"""Out-of-sample diagnostic for the Dixon-Coles low-score correction."""

import math
from typing import Any

import numpy as np
from predictor_core.measurement.metrics import log_loss, rps

from src import model


def _moving_block_ci(values: list[float], *, seed: int = 42, n_boot: int = 2000) -> list[float]:
    array = np.asarray(values, dtype=float)
    block = min(max(2, round(len(array) ** 0.5)), len(array))
    starts = np.arange(len(array) - block + 1)
    blocks_needed = math.ceil(len(array) / block)
    rng = np.random.default_rng(seed)
    samples = np.empty(n_boot)
    for index in range(n_boot):
        chosen = rng.choice(starts, size=blocks_needed, replace=True)
        sample = np.concatenate([array[start : start + block] for start in chosen])[: len(array)]
        samples[index] = sample.mean()
    return [float(value) for value in np.quantile(samples, [0.025, 0.975])]


def evaluate_rho(history: list[tuple[float, int, int]], *, minimum_matches: int = 100) -> dict[str, Any]:
    if len(history) < minimum_matches:
        return {"status": "BLOCKED_DATA", "n": len(history), "serving_changed": False}
    split = max(1, int(len(history) * 0.8))
    train, test = history[:split], history[split:]
    params = model.fit_goal_model(train)
    neutral = (*params[:3], 0.0)
    probs_rho: list[list[float]] = []
    probs_neutral: list[list[float]] = []
    outcomes: list[int] = []
    for diff, home_goals, away_goals in test:
        fitted = model.predict_match(diff, 0.0, params)
        control = model.predict_match(diff, 0.0, neutral)
        probs_rho.append([fitted["p_loss"], fitted["p_draw"], fitted["p_win"]])
        probs_neutral.append([control["p_loss"], control["p_draw"], control["p_win"]])
        outcomes.append(2 if home_goals > away_goals else 1 if home_goals == away_goals else 0)
    rps_deltas = [rps([treated], [outcome]) - rps([control], [outcome]) for treated, control, outcome in zip(
        probs_rho, probs_neutral, outcomes, strict=True
    )]
    log_deltas = [
        log_loss([treated], [outcome]) - log_loss([control], [outcome])
        for treated, control, outcome in zip(probs_rho, probs_neutral, outcomes, strict=True)
    ]
    metrics = {
        "rps_delta": float(np.mean(rps_deltas)),
        "rps_delta_ci95": _moving_block_ci(rps_deltas),
        "log_loss_delta": float(np.mean(log_deltas)),
        "log_loss_delta_ci95": _moving_block_ci(log_deltas),
    }
    finite = all(
        math.isfinite(item)
        for value in metrics.values()
        for item in (value if isinstance(value, list) else [value])
    )
    return {
        "status": "PASS_STABLE" if finite else "FAIL_NUMERIC",
        "verdict": "GO_CANDIDATE" if finite and metrics["rps_delta_ci95"][1] < 0 else "NO_GO",
        "n": len(test),
        "rho": params[3],
        "near_boundary": abs(params[3]) >= 0.399,
        "metrics": metrics,
        "serving_changed": False,
    }
