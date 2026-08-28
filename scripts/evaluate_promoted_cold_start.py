"""Run the promoted-team prior experiment only with explicit PIT ratings."""

import json

from src.data.promotions import load_promotions
from src.ingest import ROOT
from src.research.promoted_cold_start import (
    ColdStartMatch,
    build_entries,
    evaluate_first_matches,
    evaluate_goal_priors,
)


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
        ratings = {
            (int(item["season"]), str(item["team_id"])): float(item["rating"])
            for item in raw["ratings"]
        }
        participation = {
            str(team): {int(season) for season in seasons}
            for team, seasons in raw["participation_seasons"].items()
        }
        promotions = load_promotions(ROOT / "data" / "promotions_brasileirao_2018_2026.json")
        entries = build_entries(promotions, ratings, as_of_season=2026, participation_seasons=participation)
        observations = [ColdStartMatch(**item) for item in raw["first_matches"]]
        parameters = raw["protocol_parameters"]
        report = evaluate_first_matches(
            entries,
            observations,
            first_n=int(parameters["first_n"]),
            baseline_rating=float(parameters["baseline_rating"]),
            home_advantage=float(parameters["home_advantage"]),
            draw_rate=float(parameters["training_draw_rate"]),
            base_k=float(parameters["base_k"]),
            bootstrap_seed=int(parameters["bootstrap_seed"]),
            bootstrap_iterations=int(parameters["bootstrap_iterations"]),
        )
        goal_priors = {
            int(item["season"]): (float(item["attack_multiplier"]), float(item["defense_multiplier"]))
            for item in raw.get("goal_priors", [])
        }
        report["goal_prior_arm"] = evaluate_goal_priors(
            observations,
            goal_priors,
            baseline_goals_for=float(parameters["training_goals_for"]),
            baseline_goals_against=float(parameters["training_goals_against"]),
            bootstrap_seed=int(parameters["bootstrap_seed"]),
            bootstrap_iterations=int(parameters["bootstrap_iterations"]),
        )
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
