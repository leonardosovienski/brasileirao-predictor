"""CI downloads must validate the artifacts named by the lock and hash manifest."""

import re
import tomllib
from pathlib import Path


def test_ci_shared_downloads_match_locked_sources():
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    expected = {v["url"] for v in project["tool"]["uv"]["sources"].values()}
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    urls = re.findall(r'https://github.com/leonardosovienski/[^\s"\\]+\.whl', workflow)
    assert urls and set(urls) == expected
    checksums = (root / "constraints/shared-wheels.sha256").read_text(encoding="utf-8")
    assert all(url.rsplit("/", 1)[1] in checksums for url in urls)
