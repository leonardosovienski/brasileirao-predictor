import numpy as np
import pytest

from brasileirao_predictor.research.economic_decision import decide_shadow
from brasileirao_predictor.research.market_residual import MarketResidualModel, MultinomialMarketResidualModel, ResidualPrediction


def _sample(n=200):
    rng = np.random.default_rng(13)
    x = rng.normal(size=(n, 2))
    market = np.full(n, 0.5)
    probability = 1.0 / (1.0 + np.exp(-(1.5 * x[:, 0])))
    y = rng.binomial(1, probability)
    return x, y, market


def test_residual_model_learns_signal_around_market_offset():
    x, y, market = _sample()
    model = MarketResidualModel(l2=1.0).fit(x, y, market, feature_names=("signal", "noise"))
    high = model.predict(np.array([2.0, 0.0]), 0.5)
    low = model.predict(np.array([-2.0, 0.0]), 0.5)
    assert high.probability > 0.75
    assert low.probability < 0.25
    assert high.lower_probability < high.probability < high.upper_probability


def test_residual_model_rejects_small_sample():
    with pytest.raises(ValueError, match="insufficient"):
        MarketResidualModel().fit(np.zeros((10, 2)), np.zeros(10), np.full(10, 0.5))


def test_shadow_decision_uses_lower_confidence_bound_and_never_enables_capital():
    uncertain = ResidualPrediction(0.60, 0.48, 0.72, 0.50, 0.4)
    assert decide_shadow(uncertain, best_odds=2.0).action == "NO_BET"
    strong = ResidualPrediction(0.65, 0.58, 0.72, 0.50, 0.6)
    decision = decide_shadow(strong, best_odds=2.0)
    assert decision.action == "SHADOW_BET"
    assert 0 < decision.stake_units <= 0.25
    assert decision.capital_enabled is False


def test_residual_artifact_roundtrip_is_shadow_only():
    x, y, market = _sample()
    model = MarketResidualModel(l2=1.0).fit(x, y, market, feature_names=("signal", "noise"))
    restored = MarketResidualModel.from_dict(model.to_dict())
    before = model.predict(np.array([0.3, -0.1]), 0.52)
    after = restored.predict(np.array([0.3, -0.1]), 0.52)
    assert after.probability == pytest.approx(before.probability)
    payload = model.to_dict()
    payload["capital_enabled"] = True
    with pytest.raises(ValueError, match="unsafe"):
        MarketResidualModel.from_dict(payload)


def test_multinomial_residual_learns_sports_signal_around_market():
    rng = np.random.default_rng(17)
    x = rng.normal(size=(600, 2))
    market = np.tile([0.33, 0.30, 0.37], (len(x), 1))
    logits = np.log(market)
    logits[:, 0] += 1.2 * x[:, 0]
    logits[:, 1] -= 0.8 * x[:, 1]
    probabilities = np.exp(logits)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    y = np.array([rng.choice(3, p=p) for p in probabilities])
    fitted = MultinomialMarketResidualModel(l2=1.0).fit(x, y, market)
    high_away = fitted.predict_proba(np.array([2.0, 0.0]), market[0])
    low_away = fitted.predict_proba(np.array([-2.0, 0.0]), market[0])
    assert high_away[0] > low_away[0]
    assert high_away.sum() == pytest.approx(1.0)


def test_multinomial_residual_rejects_market_probabilities_not_normalized():
    x = np.zeros((60, 2))
    y = np.tile([0, 1, 2], 20)
    invalid_market = np.tile([0.4, 0.3, 0.4], (60, 1))

    with pytest.raises(ValueError, match="invalid values"):
        MultinomialMarketResidualModel().fit(x, y, invalid_market)


def test_multinomial_residual_rejects_invalid_prediction_market():
    rng = np.random.default_rng(19)
    x = rng.normal(size=(90, 2))
    y = np.tile([0, 1, 2], 30)
    market = np.tile([0.35, 0.30, 0.35], (90, 1))
    fitted = MultinomialMarketResidualModel().fit(x, y, market)

    with pytest.raises(ValueError, match="prediction values"):
        fitted.predict_proba(np.zeros(2), np.array([0.4, 0.3, 0.4]))
