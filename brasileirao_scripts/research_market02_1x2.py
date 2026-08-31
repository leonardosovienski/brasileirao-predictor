"""MARKET-02: avaliação pareada do residual multinomial 1X2."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.measurement.metrics import brier, log_loss, rps  # noqa: E402

from brasileirao_predictor.ingest import load_config  # noqa: E402
from brasileirao_predictor.math_utils import shin_probabilities  # noqa: E402
from brasileirao_predictor.research.market_residual import MultinomialMarketResidualModel  # noqa: E402
from brasileirao_scripts import benchmark_predictor as bp  # noqa: E402


def _devig(odds) -> np.ndarray | None:
    if not odds or any(not isinstance(o, (int, float)) or o <= 1 for o in odds):
        return None
    probabilities, _z, _margin = shin_probabilities(odds)
    return np.asarray([probabilities[2], probabilities[1], probabilities[0]], dtype=float)


def _serving(row) -> np.ndarray:
    return np.asarray([row["p_loss"], row["p_draw"], row["p_win"]], dtype=float)


def _features(serving: np.ndarray, opening: np.ndarray) -> np.ndarray:
    eps = 1e-12
    serving, opening = np.clip(serving, eps, 1), np.clip(opening, eps, 1)
    return np.asarray(
        [
            math.log(serving[0] / serving[2]) - math.log(opening[0] / opening[2]),
            math.log(serving[1] / serving[2]) - math.log(opening[1] / opening[2]),
        ]
    )


def _records(rows, start, end):
    records = []
    for row in rows:
        if not start <= row["date"] <= end:
            continue
        opening = _devig(row.get("market_open_odds_1x2"))
        closing = _devig(row.get("market_odds_1x2"))
        if opening is None:
            continue
        serving = _serving(row)
        records.append(
            {
                "key": (row["date"], row["home"], row["away"]),
                "date": row["date"],
                "y": row["actual_1x2"],
                "opening": opening,
                "closing": closing,
                "serving": serving,
                "features": _features(serving, opening),
            }
        )
    return records


def _loss(metric, probabilities, outcomes):
    return [metric([p.tolist()], [int(y)]) for p, y in zip(probabilities, outcomes)]


def _metrics(probabilities, outcomes):
    probabilities = np.asarray(probabilities)
    outcomes = np.asarray(outcomes)
    return {
        "rps": rps(probabilities.tolist(), outcomes.tolist()),
        "brier_1x2": brier(probabilities.tolist(), outcomes.tolist()),
        "log_loss": log_loss(probabilities.tolist(), outcomes.tolist()),
        "accuracy_1x2_diagnostic_only": float(np.mean(np.argmax(probabilities, axis=1) == outcomes)),
    }


def _paired(candidate, control, outcomes):
    result = {}
    for name, metric in (("rps", rps), ("brier_1x2", brier), ("log_loss", log_loss)):
        treatment_loss = _loss(metric, candidate, outcomes)
        control_loss = _loss(metric, control, outcomes)
        deltas = [t - c for t, c in zip(treatment_loss, control_loss)]
        result[name] = {
            "delta_treatment_minus_control": float(np.mean(deltas)),
            "delta_ci95": bp._bootstrap_mean_ci(deltas),
        }
    return result


def _evaluate(records, probabilities, *, requested_n: int):
    outcomes = np.asarray([r["y"] for r in records])
    opening = np.asarray([r["opening"] for r in records])
    serving = np.asarray([r["serving"] for r in records])
    closing_records = [(p, r["y"]) for r in records if (p := r["closing"]) is not None]
    return {
        "n": len(records),
        "requested_n": requested_n,
        "coverage": len(records) / requested_n if requested_n else 0.0,
        "treatment": _metrics(probabilities, outcomes),
        "opening_control": _metrics(opening, outcomes),
        "serving_reference": _metrics(serving, outcomes),
        "closing_reference": (
            {"n": len(closing_records), **_metrics([p for p, _ in closing_records], [y for _, y in closing_records])}
            if closing_records
            else None
        ),
        "paired_vs_opening": _paired(probabilities, opening, outcomes),
    }


def run() -> dict:
    cfg = load_config()
    observations = bp._load_observations("2024-12-31")
    rows, _ev = bp._run_walkforward(observations, 120.0, bp.RETRAIN_EVERY, engine="serving", cfg=cfg)
    development = _records(rows, "2021-01-01", "2023-12-31")
    validation = _records(rows, "2024-01-01", "2024-12-31")

    dev_predictions, dev_test = [], []
    minimum_train, block_size = 300, 100
    for start in range(minimum_train, len(development), block_size):
        train, test = development[:start], development[start : start + block_size]
        fitted = MultinomialMarketResidualModel(l2=5.0).fit(
            np.asarray([r["features"] for r in train]),
            np.asarray([r["y"] for r in train]),
            np.asarray([r["opening"] for r in train]),
        )
        dev_predictions.extend(
            fitted.predict_proba(np.asarray([r["features"] for r in test]), np.asarray([r["opening"] for r in test]))
        )
        dev_test.extend(test)

    frozen = MultinomialMarketResidualModel(l2=5.0).fit(
        np.asarray([r["features"] for r in development]),
        np.asarray([r["y"] for r in development]),
        np.asarray([r["opening"] for r in development]),
    )
    validation_predictions = frozen.predict_proba(
        np.asarray([r["features"] for r in validation]), np.asarray([r["opening"] for r in validation])
    )
    return {
        "protocol": "MARKET_02_1X2_PROTOCOL.md",
        "capital_enabled": False,
        "accuracy_policy": "DIAGNOSTIC_ONLY",
        "development_walkforward": _evaluate(
            dev_test,
            np.asarray(dev_predictions),
            requested_n=len(dev_test),
        ),
        "validation_2024": _evaluate(
            validation,
            validation_predictions,
            requested_n=sum("2024-01-01" <= row["date"] <= "2024-12-31" for row in rows),
        ),
        "holdout_2025_touched": False,
        "diagnostic_2026_touched": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
