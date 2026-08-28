"""Evaluate rho against rho=0 on a chronological holdout."""

import json
from pathlib import Path

from src import db, ratings
from src.ingest import ROOT, load_config
from src.research.rho_stability import evaluate_rho


def main() -> int:
    cfg = load_config()
    connection = db.connect(str(ROOT / cfg["database"]), read_only=True)
    rows = db.completed_matches_with_kickoff(connection)
    _current, history = ratings.compute_ratings(rows, cfg["elo"])
    report = evaluate_rho(history)
    output = Path(ROOT) / "reports" / "rho_stability.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] != "FAIL_NUMERIC" else 2


if __name__ == "__main__":
    raise SystemExit(main())
