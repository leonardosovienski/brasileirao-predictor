"""Chronological residual-model diagnostics and a cash-constrained shadow replay."""

from __future__ import annotations

import math
import statistics as st
from numbers import Integral
from typing import Any

import numpy as np

from brasileirao_predictor.research.economic_decision import choose_shadow_side, decide_shadow
from brasileirao_predictor.research.market_residual import MarketResidualModel
from brasileirao_predictor.research.residual_features import FEATURE_NAMES
from brasileirao_predictor.research.shadow_portfolio import binary_outcome, finite, replay_shadow_portfolio, utc


def _validate(row):
    if not isinstance(row, dict):
        raise ValueError("walk-forward rows must be objects")
    event = row.get("event_id")
    if isinstance(event, bool) or not isinstance(event, (str, int)) or not str(event).strip():
        raise ValueError("event_id must be a nonblank string or integer")
    prediction, kickoff = utc(row["predicted_at"]), utc(row["kickoff_at"])
    outcome = binary_outcome(row.get("outcome"))
    settled = utc(row["settled_at"]) if row.get("settled_at") is not None else None
    if (
        prediction >= kickoff
        or (settled is not None and settled <= kickoff)
        or ((settled is None) != (outcome is None))
    ):
        raise ValueError("invalid prediction/kickoff/settlement chronology")
    label_available = utc(row["label_available_at"]) if row.get("label_available_at") is not None else settled
    if label_available is not None and (settled is None or label_available < settled):
        raise ValueError("invalid label availability chronology")
    if row.get("data_status") == "ABSTAIN_DATA":
        if not isinstance(row.get("abstention_reason"), str) or not row["abstention_reason"].strip():
            raise ValueError("data abstention requires a reason")
        if any(
            row.get(field) is not None
            for field in ("features", "market_probability", "best_odds", "best_odds_by_selection")
        ):
            raise ValueError("data abstention cannot carry admitted model or price inputs")
        return {**row, "event_id": str(event), "_prediction": prediction, "_label_available": None}
    probability = finite(row["market_probability"], "market_probability")
    if not 0 < probability < 1:
        raise ValueError("market_probability must be strictly between 0 and 1")
    features = row["features"]
    if not isinstance(features, (list, tuple)) or len(features) != len(FEATURE_NAMES):
        raise ValueError("features must match FEATURE_NAMES")
    features = [finite(value, "features") for value in features]
    for field in ("features_available_at", "quote_available_at", "quote_received_at", "quote_observed_at"):
        if row.get(field) is not None and utc(row[field]) > prediction:
            raise ValueError(f"{field} is not available by prediction")
    quotes = row.get("best_odds_by_selection")
    if quotes is not None:
        if not isinstance(quotes, dict) or set(quotes) != {"over", "under"}:
            raise ValueError("quotes must contain exactly over and under")
        quotes = {side: finite(price, "odds") for side, price in quotes.items()}
        if any(price <= 1 for price in quotes.values()):
            raise ValueError("odds must exceed 1")
    single = finite(row["best_odds"], "odds") if row.get("best_odds") is not None else None
    if single is not None and single <= 1:
        raise ValueError("odds must exceed 1")
    return {
        **row,
        "event_id": str(event),
        "outcome": outcome,
        "features": features,
        "market_probability": probability,
        "best_odds_by_selection": quotes,
        "best_odds": single,
        "_prediction": prediction,
        "_label_available": label_available,
    }


def evaluate_walkforward(
    records: list[dict[str, Any]],
    *,
    minimum_train: int = 100,
    block_size: int = 50,
    l2: float = 5.0,
    friction_rate: float = 0.0,
    minimum_conservative_edge: float = 0.02,
    reference_bankroll: float = 100.0,
) -> dict[str, Any]:
    """Fit on labels available at block start; preserve every supplied event.

    Legacy records lacking verified clocks remain conditional diagnostics.
    Clock ordering does not authenticate sources. Pending labels never enter
    training or metrics. Blocks are scheduled by decision time.
    """
    for name, value, minimum in (("minimum_train", minimum_train, 20), ("block_size", block_size, 1)):
        if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}")
    if not isinstance(records, list) or len(records) <= minimum_train:
        raise ValueError("insufficient walk-forward records")
    friction_rate = finite(friction_rate, "friction_rate")
    minimum_conservative_edge = finite(minimum_conservative_edge, "minimum_conservative_edge")
    if not 0 <= friction_rate < 1 or not 0 <= minimum_conservative_edge < 1 or finite(l2, "l2") < 0:
        raise ValueError("invalid walk-forward policy")
    ordered = sorted((_validate(row) for row in records), key=lambda row: (row["_prediction"], row["event_id"]))
    if len({row["event_id"] for row in ordered}) != len(ordered):
        raise ValueError("duplicate event_id in walk-forward universe")
    universe = [
        {
            "event_id": row["event_id"],
            "predicted_at": row["predicted_at"],
            "action": "ABSTAIN_DATA" if row.get("data_status") == "ABSTAIN_DATA" else "WARMUP",
            "abstention_reason": row.get("abstention_reason"),
        }
        for row in ordered
    ]
    predictions, anchors, outcomes, orders = [], [], [], []
    unsettled_predictions = 0
    for start in range(minimum_train, len(ordered), block_size):
        test = ordered[start : start + block_size]
        cutoff = test[0]["_prediction"]
        train = [
            row for row in ordered[:start] if row["_label_available"] is not None and row["_label_available"] <= cutoff
        ]
        if len(train) < minimum_train:
            for index in range(start, start + len(test)):
                if universe[index]["action"] != "ABSTAIN_DATA":
                    universe[index]["action"] = "TRAINING_NOT_MATURE"
            continue
        model = MarketResidualModel(l2=l2).fit(
            np.asarray([row["features"] for row in train]),
            np.asarray([row["outcome"] for row in train]),
            np.asarray([row["market_probability"] for row in train]),
            feature_names=FEATURE_NAMES,
        )
        for index, row in enumerate(test, start):
            if row.get("data_status") == "ABSTAIN_DATA":
                continue
            prediction = model.predict(np.asarray(row["features"]), row["market_probability"])
            if row["outcome"] is not None:
                predictions.append(prediction.probability)
                anchors.append(row["market_probability"])
                outcomes.append(row["outcome"])
            else:
                unsettled_predictions += 1
            universe[index].update(train_n=len(train), training_cutoff=cutoff.isoformat())
            quotes = row["best_odds_by_selection"]
            if quotes is None and row["best_odds"] is None:
                universe[index]["action"] = "NO_QUOTE"
                continue
            if quotes is not None:
                decision = choose_shadow_side(
                    prediction,
                    odds_over=quotes["over"],
                    odds_under=quotes["under"],
                    friction_rate=friction_rate,
                    minimum_conservative_edge=minimum_conservative_edge,
                )
            else:
                decision = decide_shadow(
                    prediction,
                    best_odds=row["best_odds"],
                    friction_rate=friction_rate,
                    minimum_conservative_edge=minimum_conservative_edge,
                )
            universe[index]["action"] = decision.action
            if decision.action == "SHADOW_BET":
                orders.append(
                    {
                        "event_id": row["event_id"],
                        "predicted_at": row["predicted_at"],
                        "settled_at": row["_label_available"].isoformat()
                        if row["_label_available"] is not None
                        else None,
                        "outcome": row["outcome"],
                        "selection": decision.selection,
                        "stake_fraction": decision.stake_units,
                        "odds": decision.best_odds,
                        "friction_rate": decision.friction_rate,
                    }
                )
    portfolio = replay_shadow_portfolio(orders, reference_bankroll=reference_bankroll)
    actions = {r["event_id"]: r["action"] for r in portfolio["receipts"] if r["action"] != "SETTLED"}
    for row in universe:
        row["action"] = actions.get(row["event_id"], row["action"])
    result = {
        "schema_version": "residual-walkforward/v3",
        "status": "SHADOW" if outcomes else "PENDING_SAMPLE",
        "n": len(outcomes),
        "n_input": len(ordered),
        "n_unsettled_predictions": unsettled_predictions,
        "selected": sum(action == "SIMULATED_FILL" for action in actions.values()),
        "universe": universe,
        "portfolio": portfolio,
        "roi": portfolio["roi"],
        "friction_rate": friction_rate,
        "minimum_conservative_edge": minimum_conservative_edge,
        "input_scope": "caller_supplied_conditional_diagnostics",
        "n_missing_feature_clock": sum(row.get("features_available_at") is None for row in ordered),
        "n_missing_label_clock": sum(row.get("label_available_at") is None for row in ordered),
        "economic_evidence": False,
        "capital_enabled": False,
    }
    if outcomes:

        def brier(p):
            return st.mean((value - y) ** 2 for value, y in zip(p, outcomes))

        def logloss(p):
            return st.mean(
                -(y * math.log(max(1e-12, value)) + (1 - y) * math.log(max(1e-12, 1 - value)))
                for value, y in zip(p, outcomes)
            )

        result.update(
            model_brier=brier(predictions),
            market_brier=brier(anchors),
            delta_brier=brier(predictions) - brier(anchors),
            model_logloss=logloss(predictions),
            market_logloss=logloss(anchors),
            delta_logloss=logloss(predictions) - logloss(anchors),
        )
    return result
