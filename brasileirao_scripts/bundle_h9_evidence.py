"""Build a deterministic, immutable manifest for H9 operational evidence.

The source ledgers remain ignored and append-only. The generated bundle is an
audit artifact, not a replacement ledger and never enables capital.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCES = (
    ROOT / "data/research/h9_shadow.jsonl",
    ROOT / "data/research/h9_emission_attempts.jsonl",
    ROOT / "data/research/market_observations.jsonl",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(paths: tuple[Path, ...], *, generated_at: datetime, commit: str) -> dict:
    files = []
    for path in paths:
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8") as handle:
            rows = sum(1 for line in handle if line.strip())
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name,
                "bytes": path.stat().st_size,
                "rows": rows,
                "sha256": _sha256(path),
            }
        )
    return {
        "schema_version": "h9-evidence-bundle/1",
        "generated_at": generated_at.astimezone(UTC).isoformat(timespec="seconds"),
        "source_commit": commit,
        "trial": "h9-ou25-prospective-replication",
        "capital_enabled": False,
        "missing_historical_windows_recoverable": False,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    manifest = build_manifest(DEFAULT_SOURCES, generated_at=datetime.now(UTC), commit=commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
