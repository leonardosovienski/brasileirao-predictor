from datetime import UTC, datetime, timedelta

import numpy as np

from brasileirao_predictor.research.residual_walkforward import evaluate_walkforward


def test_walkforward_respects_maturity_and_never_enables_capital():
    rng = np.random.default_rng(7)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    records = []
    for index in range(180):
        kickoff = base + timedelta(days=index)
        signal = float(rng.normal())
        probability = 1 / (1 + np.exp(-signal))
        records.append(
            {
                "event_id": str(index),
                "kickoff_at": kickoff.isoformat(),
                "predicted_at": (kickoff - timedelta(hours=24)).isoformat(),
                "settled_at": (kickoff + timedelta(hours=2)).isoformat(),
                "features": [signal, 1.0, 3.0, 1.0, 0.0, signal, 0.0],
                "market_probability": 0.5,
                "best_odds": 2.05,
                "best_odds_by_selection": {"over": 2.05, "under": 2.05},
                "outcome": int(rng.random() < probability),
            }
        )
    result = evaluate_walkforward(records, minimum_train=100, block_size=20)
    assert result["status"] == "SHADOW"
    assert result["n"] > 0
    assert result["capital_enabled"] is False


def test_walkforward_reports_post_friction_policy():
    rng = np.random.default_rng(11)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    records = []
    for index in range(80):
        kickoff = base + timedelta(days=index)
        signal = float(rng.normal())
        records.append(
            {
                "event_id": str(index),
                "kickoff_at": kickoff.isoformat(),
                "predicted_at": (kickoff - timedelta(hours=24)).isoformat(),
                "settled_at": (kickoff + timedelta(hours=2)).isoformat(),
                "features": [signal, 1.0, 3.0, 1.0, 0.0, signal, 0.0],
                "market_probability": 0.5,
                "best_odds": 2.0,
                "best_odds_by_selection": {"over": 2.0, "under": 2.0},
                "outcome": int(rng.random() < 1 / (1 + np.exp(-signal))),
            }
        )
    result = evaluate_walkforward(records, minimum_train=40, block_size=20, friction_rate=0.03)
    assert result["friction_rate"] == 0.03
    assert result["capital_enabled"] is False
