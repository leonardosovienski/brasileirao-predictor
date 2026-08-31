"""Test strict past-calibrated abstention policies for OU2.5."""

from __future__ import annotations

import json

from brasileirao_scripts.research_ou25_nested_replay import ROOT, load_rows
from brasileirao_predictor.research.ou25_nested_replay import (
    anchor_to_market_prequential,
    evaluate_certainty_policies,
    file_sha256,
)


def main() -> None:
    output = ROOT / "data" / "research" / "ou25_certainty"
    output.mkdir(parents=True, exist_ok=True)
    backfill = ROOT / "data" / "research" / "ou25_backfill.sqlite"
    model_rows = load_rows("serving", 20, backfill)
    anchored_rows, anchor_report = anchor_to_market_prequential(model_rows, minimum_history=190, block_size=38)
    arms = {
        "sports_model": evaluate_certainty_policies(model_rows, evaluation_start=560),
        "market_anchored": evaluate_certainty_policies(anchored_rows, evaluation_start=560),
    }
    arm_summaries = {}
    for name, result in arms.items():
        path = output / f"{name}.json"
        path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        eligible = [
            policy
            for policy in result["policies"]
            if policy["metrics"]["n"] >= 200
            and policy["metrics"]["roi_ci95_lower"] is not None
            and policy["metrics"]["roi_ci95_lower"] > 0
            and policy["p_holm"] <= 0.05
        ]
        arm_summaries[name] = {
            "policy_count": result["policy_count"],
            "policies_with_any_pick": sum(policy["metrics"]["n"] > 0 for policy in result["policies"]),
            "maximum_n": max(policy["metrics"]["n"] for policy in result["policies"]),
            "eligible_policy_count": len(eligible),
            "artifact": path.name,
            "sha256": file_sha256(path),
        }
    summary = {
        "schema_version": "ou25-certainty-evaluation/2",
        "definition_of_certainty": "past-only Wilson lower probability bound exceeds break-even plus friction",
        "anchor_brier": anchor_report,
        "arms": arm_summaries,
        "verdict": "GO" if any(a["eligible_policy_count"] for a in arm_summaries.values()) else "NO_GO",
        "capital_enabled": False,
        "maximum_indication_score": 40,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
