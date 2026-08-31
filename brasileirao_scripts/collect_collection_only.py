"""Run the isolated sports/results COLLECTION_ONLY archival cycle."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from brasileirao_predictor.data.collection_only_archive import collect

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    conn = sqlite3.connect(f"file:{ROOT / 'data' / 'matches.db'}?mode=ro", uri=True)
    try:
        print(json.dumps(collect(conn, root=ROOT, dry_run=args.dry_run), ensure_ascii=False, sort_keys=True))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
