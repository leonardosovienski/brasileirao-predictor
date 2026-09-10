import pytest

from brasileirao_predictor.event_models import fit_event_model, predict_event


def history():
    return [dict(home_elo=1500, away_elo=1450, home_event=3, away_event=2)] * 8


@pytest.mark.parametrize("value", [-1, 2.5, float("inf"), True])
def test_count_target_requires_finite_nonnegative_integer(value):
    with pytest.raises(ValueError):
        fit_event_model([{**history()[0], "home_event": value}], "synthetic")


def test_empty_training_set_is_not_a_fitted_model():
    with pytest.raises(ValueError):
        fit_event_model([], "synthetic")


def test_missing_training_feature_is_not_observed_zero():
    with pytest.raises(ValueError):
        fit_event_model(history(), "synthetic", features=["unobserved"])


def test_missing_prediction_feature_is_not_observed_zero():
    with pytest.raises(ValueError):
        predict_event(1500, 1500, {"a": 1, "b": 0.1, "distribution": "poisson", "theta_feature": {"unobserved": 0.3}})


def test_poisson_override_has_correct_distribution_contract():
    params = fit_event_model(history(), "synthetic", distribution="nbinom", overdispersion=False)
    assert params["distribution"] == "poisson"
    assert predict_event(1500, 1450, params)[2]["under_0.5"] >= 0


def test_unknown_distribution_is_rejected():
    with pytest.raises(ValueError):
        fit_event_model(history(), "synthetic", distribution="typo")
