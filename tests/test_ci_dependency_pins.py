"""CI installs the shared wheels named by the registry, the lock and the hash manifest (never a release URL)."""

import json
import re
import tomllib
from pathlib import Path


def test_ci_shared_downloads_match_locked_sources():
    root = Path(__file__).resolve().parents[1]
    # R01 (2026-10-07): the producers are private; wheels come from STACK_WHEELS.json through
    # tools/stack_wheels.py, into the flat index the lock points to. No URL may remain in CI.
    registry = json.loads((root / "STACK_WHEELS.json").read_text(encoding="utf-8"))
    registered = {entry["package"]: entry for entry in registry["wheels"]}
    assert set(registered) == {"predictor-core", "predictor-ops"}
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    flat = [i for i in project["tool"]["uv"]["index"] if i.get("format") == "flat"]
    assert [i["url"] for i in flat] == [registry["index_dir"]]
    assert "predictor-core" not in project["tool"]["uv"].get("sources", {})
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    packages = {item["name"]: item for item in lock["package"]}
    for name, entry in registered.items():
        assert packages[name]["version"] == entry["version"]
        assert packages[name]["source"] == {"registry": registry["index_dir"]}
        assert [w["path"] for w in packages[name]["wheels"]] == [entry["asset"]]
    for relative in (
        ".github/workflows/ci.yml",
        ".github/workflows/publication-validation.yml",
        ".github/workflows/release.yml",
        "Dockerfile.cli",
        "Dockerfile.kernel",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert not re.findall(r"https://github.com/leonardosovienski/[^\s\"\\]+\.whl", text), relative
        assert "stack_wheels.py" in text, relative
    checksums = (root / "constraints/shared-wheels.sha256").read_text(encoding="utf-8")
    for entry in registered.values():
        assert f"{entry['sha256']}  {entry['asset']}" in checksums
