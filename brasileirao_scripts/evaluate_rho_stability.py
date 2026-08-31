"""Evaluate rho against rho=0 on a chronological holdout."""

import json
from pathlib import Path

from brasileirao_predictor import db, ratings
from brasileirao_predictor.ingest import ROOT, load_config
from brasileirao_predictor.research.rho_stability import evaluate_rho


def main() -> int:
    cfg = load_config()
    connection = db.connect(str(ROOT / cfg["database"]), read_only=True)
    rows = db.completed_matches_with_kickoff(connection)
    _current, history = ratings.compute_ratings(rows, cfg["elo"])
    keyed = sorted(zip(ratings.temporal_keys(rows), rows, strict=True), key=lambda item: item[0])
    report = evaluate_rho(history, group_keys=[key for key, _row in keyed])
    output = Path(ROOT) / "reports" / "rho_stability.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] != "FAIL_NUMERIC" else 2


if __name__ == "__main__":
    raise SystemExit(main())
