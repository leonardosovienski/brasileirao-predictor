"""Evaluate a leakage-safe market-anchored OU2.5 probability and filter."""

from __future__ import annotations

import json

from brasileirao_scripts.research_ou25_nested_replay import ROOT, grid, load_rows
from brasileirao_predictor.research.ou25_nested_replay import anchor_to_market_prequential, file_sha256, nested_walk_forward


def main() -> None:
    output = ROOT / "data" / "research" / "ou25_market_anchor"
    output.mkdir(parents=True, exist_ok=True)
    backfill = ROOT / "data" / "research" / "ou25_backfill.sqlite"
    rows = load_rows("serving", 20, backfill)
    anchored, anchor_report = anchor_to_market_prequential(rows, minimum_history=190, block_size=38)
    replay = nested_walk_forward(anchored, grid(), minimum_train=560, block_size=95, seed=20260827)
    anchor_path = output / "anchor_report.json"
    replay_path = output / "nested_replay.json"
    anchor_path.write_text(
        json.dumps(anchor_report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    replay_path.write_text(json.dumps(replay, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    summary = {
        "schema_version": "ou25-market-anchor-evaluation/2",
        "anchor": anchor_report,
        "filter_metrics": replay["metrics"],
        "filter_baselines": replay["baselines"],
        "verdict": "NO_GO" if replay["metrics"]["n"] < 200 else "REVIEW_REQUIRED",
        "capital_enabled": False,
        "maximum_indication_score": 40,
        "artifacts": {
            anchor_path.name: file_sha256(anchor_path),
            replay_path.name: file_sha256(replay_path),
        },
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
