from datetime import UTC, datetime, timedelta

import pytest

from brasileirao_predictor.research import residual_walkforward as wf
from brasileirao_predictor.research.economic_decision import ShadowDecision
from brasileirao_predictor.research.market_residual import ResidualPrediction


def records():
    base = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        {
            "event_id": str(i),
            "predicted_at": (base + timedelta(days=i)).isoformat(),
            "kickoff_at": (base + timedelta(days=i, hours=1)).isoformat(),
            "settled_at": (base + timedelta(days=i, hours=3)).isoformat(),
            "features": [0.0] * 7,
            "market_probability": 0.5,
            "best_odds": 2.0,
            "outcome": i % 2,
        }
        for i in range(24)
    ]


@pytest.fixture
def fixed_model(monkeypatch):
    class FixedModel:
        def __init__(self, **kwargs):
            pass

        def fit(self, *args, **kwargs):
            return self

        def predict(self, *args):
            return ResidualPrediction(0.8, 0.7, 0.9, 0.5, 0.0)

    monkeypatch.setattr(wf, "MarketResidualModel", FixedModel)
    monkeypatch.setattr(
        wf,
        "decide_shadow",
        lambda *args, **kwargs: ShadowDecision("SHADOW_BET", "over", 0.5, 0.4, 2.0, 0.1, 0.75),
    )


@pytest.mark.parametrize("invalid", [1.9, -0.1, True, "1", float("nan")])
def test_replay_rejects_invalid_label_before_training(invalid, fixed_model):
    rows = records()
    rows[-1]["outcome"] = invalid
    with pytest.raises(ValueError, match="outcome"):
        wf.evaluate_walkforward(rows, minimum_train=20)


@pytest.mark.parametrize("field", ["predicted_at", "settled_at"])
def test_replay_rejects_impossible_chronology(field, fixed_model):
    rows = records()
    rows[-1][field] = rows[-1]["kickoff_at"]
    with pytest.raises(ValueError, match="chronology"):
        wf.evaluate_walkforward(rows, minimum_train=20)


def test_replay_preserves_missing_quote_and_unsettled_games(fixed_model):
    rows = records()
    rows[-1].pop("best_odds")
    rows[20]["outcome"] = rows[21]["outcome"] = 1
    rows[-2]["outcome"] = None
    rows[-2]["settled_at"] = None
    result = wf.evaluate_walkforward(rows, minimum_train=20)
    assert len(result["universe"]) == len(rows)
    assert result["universe"][-1]["action"] == "NO_QUOTE"
    assert result["n_unsettled_predictions"] == 1
    assert result["portfolio"]["open_stakes"] > 0


def test_replay_reserves_capital_and_uses_requested_stake(fixed_model):
    rows = records()[:22]
    rows[-1].update({key: rows[-2][key] for key in ("predicted_at", "kickoff_at", "settled_at")})
    rows[-2]["outcome"] = 1
    rows[-1]["outcome"] = 0
    result = wf.evaluate_walkforward(rows, minimum_train=20, friction_rate=0.1)
    portfolio = result["portfolio"]
    # Independent cash ledger: 100 - 75 stake - 7.5 fee + 150 return = 167.5.
    assert portfolio["total_stakes"] == 75
    assert portfolio["total_costs"] == 7.5
    assert portfolio["returns_including_principal"] == 150
    assert portfolio["final_cash"] == 167.5
    assert portfolio["net_pnl"] == 67.5
    assert result["roi"] == 0.9
    assert result["selected"] == 1
    assert result["universe"][-1]["action"] == "NO_CAPITAL"


def test_replay_rejects_duplicate_events(fixed_model):
    rows = records()
    rows[-1]["event_id"] = rows[-2]["event_id"]
    with pytest.raises(ValueError, match="duplicate"):
        wf.evaluate_walkforward(rows, minimum_train=20)


def test_replay_rejects_future_feature_availability(fixed_model):
    rows = records()
    rows[-1]["features_available_at"] = rows[-1]["kickoff_at"]
    with pytest.raises(ValueError, match="available"):
        wf.evaluate_walkforward(rows, minimum_train=20)


def test_portfolio_rejects_nonfinite_output_from_finite_inputs():
    from brasileirao_predictor.research.shadow_portfolio import replay_shadow_portfolio

    order = {
        "event_id": "huge",
        "predicted_at": "2024-01-01T00:00:00Z",
        "settled_at": "2024-01-02T00:00:00Z",
        "outcome": 1,
        "stake_fraction": 0.5,
        "odds": 1e308,
        "friction_rate": 0.0,
        "selection": "over",
    }
    with pytest.raises(ValueError, match="finite"):
        replay_shadow_portfolio([order], reference_bankroll=1e308)
