"""Closed factorial replay over refit cadence and temporal block size."""

from __future__ import annotations

import json

from scripts.research_ou25_nested_replay import ROOT, grid, load_rows
from src.research.ou25_nested_replay import file_sha256, nested_walk_forward


def main() -> None:
    output = ROOT / "data" / "research" / "ou25_factorial"
    output.mkdir(parents=True, exist_ok=True)
    cells = []
    combinations = grid()
    backfill = ROOT / "data" / "research" / "ou25_backfill.sqlite"
    for retrain_every in (10, 20, 100):
        rows = load_rows("serving", retrain_every, backfill)
        for block_size in (38, 95, 190):
            result = nested_walk_forward(
                rows,
                combinations,
                minimum_train=560,
                block_size=block_size,
                seed=20260827,
            )
            path = output / f"r{retrain_every}_b{block_size}.json"
            path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            cells.append(
                {
                    "retrain_every": retrain_every,
                    "block_size": block_size,
                    "combination_count_per_fold": len(combinations),
                    "folds": len(result["outer_folds"]),
                    "total_recorded_trials": len(result["tested_combinations"]),
                    "metrics": result["metrics"],
                    "baselines": result["baselines"],
                    "artifact": path.name,
                    "sha256": file_sha256(path),
                }
            )
    summary = {
        "schema_version": "ou25-factorial/2",
        "selection": "none; closed factorial reported in full",
        "contaminated_retrospective": True,
        "prospective_a1_eligible": False,
        "capital_enabled": False,
        "maximum_indication_score": 40,
        "cells": cells,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
