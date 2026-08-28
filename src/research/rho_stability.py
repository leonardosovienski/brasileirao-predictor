"""Out-of-sample diagnostic for the Dixon-Coles low-score correction."""

import math
from typing import Any

from predictor_core.measurement.metrics import log_loss, rps

from src import model


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
    metrics = {
        "rps_delta": rps(probs_rho, outcomes) - rps(probs_neutral, outcomes),
        "log_loss_delta": log_loss(probs_rho, outcomes) - log_loss(probs_neutral, outcomes),
    }
    finite = all(math.isfinite(value) for value in metrics.values())
    return {
        "status": "PASS_STABLE" if finite else "FAIL_NUMERIC",
        "n": len(test),
        "rho": params[3],
        "near_boundary": abs(params[3]) >= 0.399,
        "metrics": metrics,
        "serving_changed": False,
    }
