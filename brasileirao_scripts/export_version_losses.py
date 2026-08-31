"""Export per-game predictions and losses for a benchmark engine/configuration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from predictor_core.measurement.metrics import brier, log_loss, rps

from brasileirao_predictor.ingest import load_config
from brasileirao_scripts.benchmark_predictor import MIN_HISTORY, RETRAIN_EVERY, _load_observations, _run_walkforward


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--engine",
        choices=("serving", "dynamic_strength", "h9_frozen", "dixon_coles"),
        default="serving",
    )
    parser.add_argument("--retrain-every", type=int, default=RETRAIN_EVERY)
    parser.add_argument("--half-life", type=float, default=120.0)
    parser.add_argument(
        "--ensemble-xg",
        choices=("configured", "on", "off"),
        default="configured",
        help="Override ensemble_xg.enabled without changing config.yaml.",
    )
    args = parser.parse_args()
    start, end = args.period.split(",", 1)
    cfg = load_config()
    if args.ensemble_xg != "configured":
        cfg["ensemble_xg"] = dict(cfg.get("ensemble_xg") or {})
        cfg["ensemble_xg"]["enabled"] = args.ensemble_xg == "on"
    observations = _load_observations(end)
    rows, _ev = _run_walkforward(
        observations,
        half_life=args.half_life,
        retrain_every=args.retrain_every,
        engine=args.engine,
        cfg=cfg,
    )
    selected = [row for row in rows if (not start or row["date"] >= start) and (not end or row["date"] <= end)]
    exported = []
    for row in selected:
        probabilities = [row["p_loss"], row["p_draw"], row["p_win"]]
        outcome = row["actual_1x2"]
        exported.append(
            {
                "event_id": row["event_id"],
                "date": row["date"],
                "home": row["home"],
                "away": row["away"],
                "outcome": outcome,
                "probabilities": probabilities,
                "rps": rps([probabilities], [outcome]),
                "brier": brier([probabilities], [outcome]),
                "log_loss": log_loss([probabilities], [outcome]),
            }
        )
    if len(observations) < MIN_HISTORY:
        raise RuntimeError("insufficient history")
    Path(args.output).write_text(json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
