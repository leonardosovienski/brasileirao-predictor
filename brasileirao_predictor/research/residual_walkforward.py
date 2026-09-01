"""Strict chronological evaluation for the market-residual candidate."""

from __future__ import annotations

import math
import statistics as st
from datetime import datetime
from typing import Any

import numpy as np

from brasileirao_predictor.research.economic_decision import choose_shadow_side, decide_shadow
from brasileirao_predictor.research.market_residual import MarketResidualModel
from brasileirao_predictor.research.residual_features import FEATURE_NAMES


def _brier(probabilities, outcomes):
    return st.mean((p - y) ** 2 for p, y in zip(probabilities, outcomes))


def _log_loss(probabilities, outcomes):
    eps = 1e-12
    return st.mean(
        -(y * math.log(max(eps, p)) + (1 - y) * math.log(max(eps, 1 - p))) for p, y in zip(probabilities, outcomes)
    )


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("walk-forward timestamps must be timezone-aware")
    return parsed


def evaluate_walkforward(
    records: list[dict[str, Any]],
    *,
    minimum_train: int = 100,
    block_size: int = 50,
    l2: float = 5.0,
    friction_rate: float = 0.0,
    minimum_conservative_edge: float = 0.02,
) -> dict[str, Any]:
    """Fit only on matured earlier events and evaluate each later block once."""
    if not 0 <= friction_rate < 1:
        raise ValueError("friction_rate must be between zero and one")
    ordered = sorted(records, key=lambda row: (_utc(row["kickoff_at"]), row["event_id"]))
    if minimum_train < 20 or block_size < 1 or len(ordered) <= minimum_train:
        raise ValueError("insufficient walk-forward configuration or records")
    predictions, anchors, outcomes, pnl, selected = [], [], [], [], 0
    for start in range(minimum_train, len(ordered), block_size):
        train, test = ordered[:start], ordered[start : start + block_size]
        # Strict boundary: a training result must have matured before the first
        # test prediction timestamp, not merely have an earlier kickoff.
        first_prediction = min(_utc(row["predicted_at"]) for row in test)
        train = [row for row in train if _utc(row["settled_at"]) <= first_prediction]
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
            quotes = row.get("best_odds_by_selection")
            if quotes:
                decision = choose_shadow_side(
                    prediction,
                    odds_over=float(quotes["over"]),
                    odds_under=float(quotes["under"]),
                    friction_rate=friction_rate,
                    minimum_conservative_edge=minimum_conservative_edge,
                )
            else:
                # Legacy records contain an observed Over quote only. Never
                # invent an executable Under price from the fair probability.
                decision = decide_shadow(
                    prediction,
                    best_odds=float(row["best_odds"]),
                    friction_rate=friction_rate,
                    minimum_conservative_edge=minimum_conservative_edge,
                )
            y = int(row["outcome"])
            predictions.append(prediction.probability)
            anchors.append(row["market_probability"])
            outcomes.append(y)
            if decision.action == "SHADOW_BET":
                selected += 1
                won = bool(y) if decision.selection == "over" else not bool(y)
                gross = (decision.best_odds - 1.0) if won else -1.0
                pnl.append(gross - friction_rate)
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
        "friction_rate": friction_rate,
        "minimum_conservative_edge": minimum_conservative_edge,
        "capital_enabled": False,
    }
