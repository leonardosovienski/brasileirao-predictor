"""Contraste pareado TRACK A02: serving vs estados atk/def curto+longo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.measurement.metrics import brier, log_loss, rps  # noqa: E402

from brasileirao_scripts import benchmark_predictor as bp  # noqa: E402
from brasileirao_predictor.ingest import load_config  # noqa: E402

ALLOWED_PERIODS = {
    "development": ("2021-01-01", "2023-12-31"),
    "validation": ("2024-01-01", "2024-12-31"),
    "diagnostic-2026": ("2026-01-01", "2026-12-31"),
}


def _losses(rows, metric):
    probs = [[r["p_loss"], r["p_draw"], r["p_win"]] for r in rows]
    ys = [r["actual_1x2"] for r in rows]
    return [metric([p], [y]) for p, y in zip(probs, ys)]


def _summary(rows):
    probs = [[r["p_loss"], r["p_draw"], r["p_win"]] for r in rows]
    ys = [r["actual_1x2"] for r in rows]
    over_probs = [r["p_over"] for r in rows]
    over_ys = [r["actual_over"] for r in rows]
    return {
        "n": len(rows),
        "coverage": 1.0,
        "rps": rps(probs, ys),
        "brier_1x2": brier(probs, ys),
        "log_loss": log_loss(probs, ys),
        "brier_ou25": brier([[1 - p, p] for p in over_probs], over_ys),
        "accuracy_1x2_diagnostic_only": sum(p.index(max(p)) == y for p, y in zip(probs, ys)) / len(rows),
        "accuracy_ou25_diagnostic_only": sum(int(p > 0.5) == y for p, y in zip(over_probs, over_ys)) / len(rows),
    }


def run(period_name: str) -> dict:
    start, end = ALLOWED_PERIODS[period_name]
    cfg = load_config()
    observations = bp._load_observations(end)
    control, _ = bp._run_walkforward(observations, 120.0, bp.RETRAIN_EVERY, engine="serving", cfg=cfg)
    treatment, _ = bp._run_walkforward(observations, 120.0, bp.RETRAIN_EVERY, engine="dynamic_strength", cfg=cfg)
    control = [r for r in control if start <= r["date"] <= end]
    treatment = [r for r in treatment if start <= r["date"] <= end]
    keys_control = [(r["date"], r["home"], r["away"]) for r in control]
    keys_treatment = [(r["date"], r["home"], r["away"]) for r in treatment]
    if keys_control != keys_treatment:
        raise RuntimeError("controle e tratamento não estão pareados pelos mesmos jogos")

    metrics = {}
    for name, metric in (("rps", rps), ("brier_1x2", brier), ("log_loss", log_loss)):
        lc, lt = _losses(control, metric), _losses(treatment, metric)
        delta = sum(t - c for c, t in zip(lc, lt)) / len(lt)
        metrics[name] = {
            "delta_treatment_minus_control": delta,
            "delta_ci95": bp._bootstrap_mean_ci([t - c for c, t in zip(lc, lt)]),
        }

    ou_control = [brier([[1 - r["p_over"], r["p_over"]]], [r["actual_over"]]) for r in control]
    ou_treatment = [brier([[1 - r["p_over"], r["p_over"]]], [r["actual_over"]]) for r in treatment]
    ou_delta = [t - c for c, t in zip(ou_control, ou_treatment)]
    metrics["brier_ou25"] = {
        "delta_treatment_minus_control": sum(ou_delta) / len(ou_delta),
        "delta_ci95": bp._bootstrap_mean_ci(ou_delta),
    }
    return {
        "protocol": "TRACK_A02_DYNAMIC_STRENGTH_PROTOCOL.md",
        "period_name": period_name,
        "period": {"start": start, "end": end},
        "accuracy_policy": "DIAGNOSTIC_ONLY",
        "control": _summary(control),
        "treatment": _summary(treatment),
        "paired_metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True, choices=tuple(ALLOWED_PERIODS))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.period)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
