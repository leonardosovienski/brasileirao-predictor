from types import SimpleNamespace

import pytest

from brasileirao_predictor import model
from brasileirao_predictor.model import (
    ModelIntegrityError,
    OptimizationFailedError,
    exponential_recency_weights,
    fit_goal_model,
    predict_match,
)

# AUDITORIA P1: o fixture antigo usava [elo_home, elo_away, hs, as] — formato
# ERRADO que este teste canonizou e a Fase 2 copiou (o MLE tratava o Elo do
# visitante como gols do mandante). O contrato real de fit_goal_model é
# (elo_diff, home_goals, away_goals) — ver ratings.compute_ratings.
_HISTORY = [
    (200, 2, 1),
    (100, 3, 0),
    (-100, 1, 2),
    (-200, 0, 1),
    (300, 4, 0),
]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_fit_without_xg():
    """Backward compatibility: sem delta_xg, retorna 4 parametros.
    (n=5 e' fixture-brinquedo: rho pode cravar no bound e o warning P10
    dispara legitimamente — aqui so interessa a forma do retorno.)"""
    params = fit_goal_model(_HISTORY)
    assert len(params) == 4
    a, b, alpha, rho = params
    assert alpha > 0
    assert -0.4 <= rho <= 0.4


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_fit_with_xg():
    """Com delta_xg, retorna 5 parametros e theta_xg != 0."""
    history = list(_HISTORY)
    delta_xg = [1.5, 2.0, -1.5, -2.0, 2.5]
    params = fit_goal_model(history, delta_xg=delta_xg)
    assert len(params) == 5
    a, b, alpha, rho, theta_xg = params
    assert alpha > 0
    assert theta_xg != 0.0  # deve capturar o sinal do delta_xg


def test_fit_with_unit_weights_preserves_legacy_result():
    legacy = fit_goal_model(_HISTORY)
    weighted = fit_goal_model(_HISTORY, sample_weights=[1.0] * len(_HISTORY))
    assert weighted == pytest.approx(legacy)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_recent_matches_receive_more_influence():
    history = [(0, 0, 0)] * 20 + [(0, 4, 4)] * 5
    old_heavy = fit_goal_model(history, sample_weights=[1.0] * 20 + [0.01] * 5)
    recent_heavy = fit_goal_model(history, sample_weights=[0.01] * 20 + [1.0] * 5)
    assert recent_heavy[0] > old_heavy[0]


@pytest.mark.parametrize("weights", [[1.0], [1.0, 1.0, 1.0, 1.0, 0.0], [1.0, 1.0, 1.0, 1.0, float("nan")]])
def test_invalid_sample_weights_fail_closed(weights):
    with pytest.raises(ModelIntegrityError, match="sample_weights"):
        fit_goal_model(_HISTORY, sample_weights=weights)


@pytest.mark.parametrize(
    "history,match",
    [
        ([(float("nan"), 1, 0)], "elo_diff"),
        ([(float("inf"), 1, 0)], "elo_diff"),
        ([(0, -1, 0)], "home_goals"),
        ([(0, 1.5, 0)], "home_goals"),
        ([(0, True, 0)], "home_goals"),
        ([(0, 1, float("nan"))], "away_goals"),
        ([(0, 1)], "three-item"),
        ([{"elo_diff": 0, "home_goals": 1, "away_goals": 0}], "three-item"),
    ],
)
def test_invalid_goal_history_fails_closed(history, match):
    with pytest.raises(ModelIntegrityError, match=match):
        fit_goal_model(history)


@pytest.mark.parametrize("delta_xg", [[1.0], [1.0] * 4 + [float("nan")], [1.0] * 4 + [float("inf")]])
def test_invalid_delta_xg_fails_closed(delta_xg):
    with pytest.raises(ModelIntegrityError, match="delta_xg"):
        fit_goal_model(_HISTORY, delta_xg=delta_xg)


def test_empty_history_preserves_explicit_cold_start():
    assert fit_goal_model([]) == (0.0, 0.3, 1e-4, 0.0)
    assert fit_goal_model([], delta_xg=[]) == (0.0, 0.3, 1e-4, 0.0, 0.0)


def test_optimizer_failure_is_typed_and_never_returns_fallback(monkeypatch):
    failed = SimpleNamespace(success=False, fun=10.0, x=[0.0, 0.3, -2.0, 0.0], message="synthetic failure")
    monkeypatch.setattr(model, "minimize", lambda *args, **kwargs: failed)
    with pytest.raises(OptimizationFailedError, match="did not converge"):
        fit_goal_model(_HISTORY)


def test_exponential_recency_weights_obey_half_life_exactly():
    weights = exponential_recency_weights(["2025-01-11", "2025-07-10", "2026-01-06"], "2026-01-06", 360)
    assert weights == pytest.approx([0.5, 2**-0.5, 1.0])


def test_exponential_recency_weights_support_explicit_uniform_policy():
    assert exponential_recency_weights(["2021-01-01", "2026-01-01"], "2026-01-01", None) == [1.0, 1.0]


@pytest.mark.parametrize("half_life", [0, -1, float("nan"), float("inf")])
def test_exponential_recency_weights_reject_invalid_half_life(half_life):
    with pytest.raises(ValueError, match="goal_half_life_days"):
        exponential_recency_weights([], "2026-01-01", half_life)


def test_exponential_recency_weights_reject_future_match():
    with pytest.raises(ValueError, match="after asof"):
        exponential_recency_weights(["2026-01-02"], "2026-01-01", 360)


def test_predict_with_xg():
    """predict_match com delta_xg altera as probabilidades."""
    params = (0.2, 0.8, 0.15, -0.03, 0.5)  # a, b, alpha, rho, theta
    pred_flat = predict_match(1800, 1600, params, delta_xg=0.0)
    pred_xg = predict_match(1800, 1600, params, delta_xg=2.0)
    # Com delta_xg positivo, o time da casa deve ter mais chances
    assert pred_xg["p_win"] > pred_flat["p_win"]


def test_predict_without_xg():
    """predict_match sem delta_xg mantem comportamento original."""
    params = (0.2, 0.8, 0.15, -0.03)
    pred = predict_match(1800, 1600, params)
    assert 0 < pred["p_win"] < 1
    assert abs(pred["p_win"] + pred["p_draw"] + pred["p_loss"] - 1.0) < 0.001
