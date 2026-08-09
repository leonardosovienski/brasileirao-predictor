"""Strict chronological evaluation for the market-residual candidate."""

from __future__ import annotations

import math
import statistics as st
from typing import Any

import numpy as np

from src.research.economic_decision import decide_shadow
from src.research.market_residual import MarketResidualModel
from src.research.residual_features import FEATURE_NAMES


def _brier(probabilities, outcomes):
    return st.mean((p - y) ** 2 for p, y in zip(probabilities, outcomes))


def _log_loss(probabilities, outcomes):
    eps = 1e-12
    return st.mean(
        -(y * math.log(max(eps, p)) + (1 - y) * math.log(max(eps, 1 - p))) for p, y in zip(probabilities, outcomes)
    )


def evaluate_walkforward(
    records: list[dict[str, Any]],
    *,
    minimum_train: int = 100,
    block_size: int = 50,
    l2: float = 5.0,
) -> dict[str, Any]:
    """Fit only on matured earlier events and evaluate each later block once."""
    ordered = sorted(records, key=lambda row: (row["kickoff_at"], row["event_id"]))
    if minimum_train < 20 or block_size < 1 or len(ordered) <= minimum_train:
        raise ValueError("insufficient walk-forward configuration or records")
    predictions, anchors, outcomes, pnl, selected = [], [], [], [], 0
    for start in range(minimum_train, len(ordered), block_size):
        train, test = ordered[:start], ordered[start : start + block_size]
        # Strict boundary: a training result must have matured before the first
        # test prediction timestamp, not merely have an earlier kickoff.
        first_prediction = min(row["predicted_at"] for row in test)
        train = [row for row in train if row["settled_at"] <= first_prediction]
        if len(train) < minimum_train:
            continue
        model = MarketResidualModel(l2=l2).fit(
            np.asarray([row["features"] for row in train]),
            np.asarray([row["outcome"] for row in train]),
            np.asarray([row["market_probability"] for row in train]),
            feature_names=FEATURE_NAMES,
        )
        for row in test:
            prediction = model.predict(np.asarray(row["features"]), row["market_probability"])
            decision = decide_shadow(prediction, best_odds=row["best_odds"])
            y = int(row["outcome"])
            predictions.append(prediction.probability)
            anchors.append(row["market_probability"])
            outcomes.append(y)
            if decision.action == "SHADOW_BET":
                selected += 1
                pnl.append((row["best_odds"] - 1.0) if y else -1.0)
    if not outcomes:
        return {"status": "PENDING_SAMPLE", "n": 0}
    model_brier, market_brier = _brier(predictions, outcomes), _brier(anchors, outcomes)
    model_logloss, market_logloss = _log_loss(predictions, outcomes), _log_loss(anchors, outcomes)
    return {
        "status": "SHADOW",
        "n": len(outcomes),
        "selected": selected,
        "model_brier": model_brier,
        "market_brier": market_brier,
        "delta_brier": model_brier - market_brier,
        "model_logloss": model_logloss,
        "market_logloss": market_logloss,
        "delta_logloss": model_logloss - market_logloss,
        "roi": st.mean(pnl) if pnl else None,
        "capital_enabled": False,
    }
