"""Fase 0B passo zero: resolução do modelo e cobertura de odds OU2.5/BTTS."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brasileirao_scripts import benchmark_predictor as bp  # noqa: E402
from brasileirao_predictor.ingest import load_config  # noqa: E402
from brasileirao_predictor.research.market_0b_resolution import evaluate, full_market_protocol, paired_records  # noqa: E402

PROTOCOL = "docs/experiments/MARKET_04_0B_RESOLUTION_PROTOCOL.md"


def run(*, permutations: int = 1000) -> dict:
    cfg = load_config()
    observations = bp._load_observations("2023-12-31")
    rows, _evaluator = bp._run_walkforward(observations, 120.0, bp.RETRAIN_EVERY, engine="serving", cfg=cfg)
    development = [row for row in rows if "2021-01-01" <= row["date"] <= "2023-12-31"]
    precheck = evaluate(development)
    result = {
        "schema_version": "market-0b-resolution/1",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "protocol": PROTOCOL,
        "research_mode": "RETROSPECTIVE_READ_ONLY",
        "economic_evidence_eligible": False,
        "capital_enabled": False,
        "development_2021_2023": precheck,
        "validation_2024": None,
        "validation_2024_loaded": False,
        "full_protocol": None,
        "holdout_2025_touched": False,
        "diagnostic_2026_touched": False,
    }
    if precheck["verdict"] != "PROCEED_TO_FULL_0B":
        result["verdict"] = precheck["verdict"]
        return result

    observations = bp._load_observations("2024-12-31")
    all_rows, _evaluator = bp._run_walkforward(observations, 120.0, bp.RETRAIN_EVERY, engine="serving", cfg=cfg)
    validation = [row for row in all_rows if "2024-01-01" <= row["date"] <= "2024-12-31"]
    specifications = {
        "ou25": ("p_over", "market_odds_ou25", "actual_over"),
        "btts": ("p_btts", "market_odds_btts", "actual_btts"),
    }
    full = {}
    for offset, (market, keys) in enumerate(specifications.items()):
        dev_records = paired_records(development, *keys)
        val_records = paired_records(validation, *keys)
        full[market] = {
            "development": full_market_protocol(
                dev_records, power_reference=dev_records, permutations=permutations, seed=20260824 + offset
            ),
            "validation": full_market_protocol(
                val_records, power_reference=dev_records, permutations=permutations, seed=20261824 + offset
            ),
        }
    result["validation_2024"] = evaluate(validation)
    result["validation_2024_loaded"] = True
    result["full_protocol"] = full
    result["verdict"] = (
        "SIGNAL_FOR_PROSPECTIVE_REPLICATION"
        if any(item["validation"]["verdict"] == "SIGNAL_FOR_PROSPECTIVE_REPLICATION" for item in full.values())
        else "NO_GO_CURRENT_RESIDUAL"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--permutations", type=int, default=1000)
    args = parser.parse_args()
    if args.permutations < 1:
        parser.error("--permutations >= 1")
    result = run(permutations=args.permutations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"MARKET_0B verdict={result['verdict']} validation_loaded={result['validation_2024_loaded']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
