"""Emit the point-in-time xG coverage audit without mutating the database."""

import json

from brasileirao_predictor import db
from brasileirao_predictor.data.missingness_audit import xg_coverage
from brasileirao_predictor.ingest import ROOT, load_config


def main() -> int:
    cfg = load_config()
    conn = db.connect(str(ROOT / cfg["database"]), read_only=True)
    try:
        print(json.dumps(xg_coverage(conn), ensure_ascii=False, indent=2))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
