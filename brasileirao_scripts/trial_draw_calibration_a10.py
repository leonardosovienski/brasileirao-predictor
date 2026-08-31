"""Run the frozen A10 binary draw calibration protocol."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return np.log(p / (1 - p))


def _fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    def objective(theta: np.ndarray) -> float:
        z = theta[0] + theta[1] * x
        return float(np.sum(np.logaddexp(0.0, z) - y * z))

    def gradient(theta: np.ndarray) -> np.ndarray:
        z = theta[0] + theta[1] * x
        fitted = 1 / (1 + np.exp(-z))
        residual = fitted - y
        return np.array([np.sum(residual), np.sum(residual * x)])

    result = minimize(objective, np.array([0.0, 1.0]), jac=gradient, method="L-BFGS-B")
    if not result.success:
        raise RuntimeError(str(result.message))
    return float(result.x[0]), float(result.x[1])


def _losses(p: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray]:
    onehot = np.eye(3)[y]
    cumulative = np.cumsum(p, axis=1)[:, :-1]
    cumulative_y = np.cumsum(onehot, axis=1)[:, :-1]
    return {
        "rps": np.mean((cumulative - cumulative_y) ** 2, axis=1),
        "brier": np.sum((p - onehot) ** 2, axis=1),
        "log_loss": -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1.0)),
        "brier_draw": (p[:, 1] - (y == 1)) ** 2,
    }


def _moving_ci(delta: np.ndarray, seed: int = 42, n_boot: int = 10_000, block: int = 21) -> list[float]:
    rng = np.random.default_rng(seed)
    n = len(delta)
    if n == 0:
        raise ValueError("moving-block CI requires at least one paired loss")
    block = min(block, n)
    starts = np.arange(n - block + 1)
    means = np.empty(n_boot)
    blocks_needed = int(np.ceil(n / block))
    for i in range(n_boot):
        chosen = rng.choice(starts, size=blocks_needed, replace=True)
        sample = np.concatenate([delta[start : start + block] for start in chosen])[:n]
        means[i] = np.mean(sample)
    return [float(v) for v in np.quantile(means, [0.025, 0.975])]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.input.read_text(encoding="utf-8"))
    train = [row for row in rows if row["date"] <= "2023-12-31"]
    valid = [row for row in rows if "2024-01-01" <= row["date"] <= "2024-12-31"]
    x = _logit(np.array([row["probabilities"][1] for row in train]))
    y_train = np.array([row["outcome"] == 1 for row in train], dtype=float)
    intercept, slope = _fit(x, y_train)
    p_control = np.array([row["probabilities"] for row in valid], dtype=float)
    y = np.array([row["outcome"] for row in valid], dtype=int)
    calibrated_draw = 1 / (1 + np.exp(-(intercept + slope * _logit(p_control[:, 1]))))
    p_treatment = p_control.copy()
    side_ratio = p_control[:, [0, 2]] / (1 - p_control[:, 1])[:, None]
    p_treatment[:, 1] = calibrated_draw
    p_treatment[:, [0, 2]] = side_ratio * (1 - calibrated_draw)[:, None]
    control_losses = _losses(p_control, y)
    treatment_losses = _losses(p_treatment, y)
    metrics = {}
    for name in control_losses:
        delta = treatment_losses[name] - control_losses[name]
        metrics[name] = {
            "control": float(np.mean(control_losses[name])),
            "treatment": float(np.mean(treatment_losses[name])),
            "delta_treatment_minus_control": float(np.mean(delta)),
            "delta_ci95": _moving_ci(delta),
        }
    home_mask = y == 2
    home_control = control_losses["log_loss"][home_mask]
    home_treatment = treatment_losses["log_loss"][home_mask]
    if not len(home_control):
        raise ValueError("A10 validation has no home-win observations")
    home_delta = home_treatment - home_control
    metrics["log_loss_home_win"] = {
        "control": float(np.mean(home_control)),
        "treatment": float(np.mean(home_treatment)),
        "delta_treatment_minus_control": float(np.mean(home_delta)),
        "delta_ci95": _moving_ci(home_delta),
        "n": int(len(home_delta)),
    }
    pred_control = np.argmax(p_control, axis=1)
    pred_treatment = np.argmax(p_treatment, axis=1)
    flips = pred_control != pred_treatment
    result = {
        "schema_version": "trial-draw-calibration-a10/1",
        "protocol": "docs/PROTOCOL_DRAW_CALIBRATION_A10_2026-08-26.md",
        "train_period": ["2021-01-01", "2023-12-31"],
        "validation_period": ["2024-01-01", "2024-12-31"],
        "n_train": len(train),
        "n_validation": len(valid),
        "parameters": {"intercept": intercept, "slope": slope},
        "metrics": metrics,
        "argmax": {
            "flips": int(np.sum(flips)),
            "draw_predictions_control": int(np.sum(pred_control == 1)),
            "draw_predictions_treatment": int(np.sum(pred_treatment == 1)),
            "accuracy_control": float(np.mean(pred_control == y)),
            "accuracy_treatment": float(np.mean(pred_treatment == y)),
        },
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
