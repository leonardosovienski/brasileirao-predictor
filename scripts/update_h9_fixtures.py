"""Refresh the fixture/result inputs required by the H9 shadow pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STEPS = (
    ("sofascore", (sys.executable, "-X", "utf8", "-m", "src.ingest_sofascore")),
    (
        "match_mirror",
        (sys.executable, "-X", "utf8", str(ROOT / "scripts" / "sync_matches_from_sofascore.py")),
    ),
    ("elo_cache", (sys.executable, "-X", "utf8", "-m", "src.cron_update_models")),
)


def main() -> int:
    for name, command in STEPS:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            print(f"H9_INPUT_REFRESH_FAILED step={name} exit={result.returncode}", file=sys.stderr)
            return result.returncode
        print(f"H9_INPUT_REFRESH_OK step={name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
