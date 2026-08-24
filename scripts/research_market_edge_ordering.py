"""Fase 0: existe residual ordenável entre serving e mercado 1X2 agregado?"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry  # noqa: E402

from scripts import benchmark_predictor as bp  # noqa: E402
from src.ingest import load_config  # noqa: E402
from src.research.market_edge_ordering import evaluate, paired_records  # noqa: E402

PROTOCOL = "docs/experiments/MARKET_03_EDGE_ORDERING_PROTOCOL.md"
TRIALS = ROOT / "data" / "trials.json"
SEED = 20260824


def run(*, permutations: int = 1000) -> dict:
    cfg = load_config()
    observations = bp._load_observations("2024-12-31")
    rows, _ev = bp._run_walkforward(observations, 120.0, bp.RETRAIN_EVERY, engine="serving", cfg=cfg)
    registry = TrialRegistry(TRIALS)
    sharpes = registry.sharpes()
    requested_dev = sum("2021-01-01" <= row["date"] <= "2023-12-31" for row in rows)
    requested_val = sum("2024-01-01" <= row["date"] <= "2024-12-31" for row in rows)
    dev = paired_records(rows, "2021-01-01", "2023-12-31")
    val = paired_records(rows, "2024-01-01", "2024-12-31")
    development = evaluate(
        dev,
        requested_n=requested_dev,
        historical_trial_sharpes=sharpes,
        permutations=permutations,
        seed=SEED,
    )
    validation = evaluate(
        val,
        requested_n=requested_val,
        historical_trial_sharpes=sharpes,
        permutations=permutations,
        seed=SEED + permutations,
        power_reference=dev,
    )
    passed = bool(
        validation["draw_ordering"]["monotonic_roi"]
        and validation["power_minimums_met"]
        and validation["permutation_sanity"]["null_monotonic_rate"] < 0.05
    )
    return {
        "schema_version": "market-edge-ordering/1",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "protocol": PROTOCOL,
        "source": "SOFASCORE_AGGREGATE_UNNAMED_DIAGNOSTIC_ONLY",
        "economic_evidence_eligible": False,
        "capital_enabled": False,
        "accuracy_policy": "DIAGNOSTIC_ONLY",
        "development_2021_2023": development,
        "validation_2024": validation,
        "holdout_2025_touched": False,
        "diagnostic_2026_touched": False,
        "verdict": "SIGNAL_FOR_PROSPECTIVE_REPLICATION" if passed else "NO_GO_CURRENT_RESIDUAL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--permutations", type=int, default=1000)
    args = parser.parse_args()
    if args.permutations < 1:
        parser.error("--permutations >= 1")
    result = run(permutations=args.permutations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"MARKET_EDGE_ORDERING verdict={result['verdict']} "
        f"dev_n={result['development_2021_2023']['n']} val_n={result['validation_2024']['n']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
