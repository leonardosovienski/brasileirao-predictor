"""Generate a fingerprinted temporal manifest without changing legacy runners."""

import argparse
import json
from pathlib import Path
from typing import Any

from brasileirao_predictor.research.temporal_replay import build_temporal_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="JSON array of historical match rows")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fallback", choices=("group_by_date", "reject"), default="group_by_date")
    args = parser.parse_args()
    rows: Any = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("input must be a JSON array of objects")
    manifest = build_temporal_manifest(rows, fallback=args.fallback)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
