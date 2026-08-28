"""Run the promoted-team prior experiment only with explicit PIT ratings."""

import json
from pathlib import Path

from src.data.promotions import load_promotions
from src.ingest import ROOT
from src.research.promoted_cold_start import build_entries, evaluate_empirical_prior


def main() -> int:
    ratings_path = ROOT / "data" / "promoted_entry_ratings.json"
    output = ROOT / "reports" / "promoted_cold_start.json"
    if not ratings_path.exists():
        report = {
            "status": "BLOCKED_DATA",
            "reason": "data/promoted_entry_ratings.json is absent",
            "serving_changed": False,
        }
    else:
        raw = json.loads(ratings_path.read_text(encoding="utf-8"))
        ratings = {(int(item["season"]), str(item["team_id"])): float(item["rating"]) for item in raw}
        promotions = load_promotions(ROOT / "data" / "promotions_brasileirao_2018_2026.json")
        entries = build_entries(promotions, ratings, as_of_season=2026)
        report = evaluate_empirical_prior(entries)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
