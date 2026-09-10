"""Numerical and serialization boundaries; synthetic samples only."""

import copy
from types import SimpleNamespace

import numpy as np
import pytest

from brasileirao_predictor.research import market_residual as module


def artifact():
    return dict(
        schema_version="market-residual/1",
        capital_enabled=False,
        l2=5.0,
        feature_names=["signal"],
        coefficients=[0.0, 0.1],
        means=[0.0],
        scales=[1.0],
        covariance=[[1.0, 0.0], [0.0, 1.0]],
    )


@pytest.mark.parametrize(
    "change",
    [
        {"coefficients": [0.0, float("nan")]},
        {"means": [float("inf")]},
        {"scales": [0.0]},
        {"scales": [-1.0]},
        {"scales": [float("nan")]},
        {"covariance": [[1.0, 2.0], [0.0, 1.0]]},
        {"covariance": [[1.0, 2.0], [2.0, 1.0]]},
        {"covariance": [[float("inf"), 0.0], [0.0, 1.0]]},
        {"l2": -1},
        {"l2": True},
        {"l2": float("nan")},
        {"feature_names": [" "]},
    ],
)
def test_invalid_artifact_cannot_be_loaded(change):
    with pytest.raises(ValueError):
        module.MarketResidualModel.from_dict({**artifact(), **change})


def test_duplicate_feature_names_are_rejected():
    payload = {
        **artifact(),
        "feature_names": ["x", "x"],
        "coefficients": [0, 0, 0],
        "means": [0, 0],
        "scales": [1, 1],
        "covariance": np.eye(3).tolist(),
    }
    with pytest.raises(ValueError):
        module.MarketResidualModel.from_dict(payload)


@pytest.mark.parametrize("z", [-1.0, float("nan"), float("inf"), True])
def test_interval_multiplier_must_be_finite_nonnegative(z):
    model = module.MarketResidualModel.from_dict(artifact())
    with pytest.raises(ValueError):
        model.predict(np.zeros(1), 0.5, z_score=z)


def test_sigmoid_handles_extreme_logits_without_overflow():
    with np.errstate(over="raise", invalid="raise"):
        result = module._sigmoid(np.array([-1000.0, 0.0, 1000.0]))
    assert np.array_equal(result, [0.0, 0.5, 1.0])


def test_predict_and_export_reject_mutated_invalid_state():
    model = module.MarketResidualModel.from_dict(artifact())
    model.covariance = np.array([[-1.0, 0.0], [0.0, 1.0]])
    with pytest.raises(ValueError):
        model.predict(np.zeros(1), 0.5)
    with pytest.raises(ValueError):
        model.to_dict()


def test_loading_copies_arrays_instead_of_borrowing_mutable_payload():
    coefficients = np.array([0.0, 0.1])
    payload = {**artifact(), "coefficients": coefficients}
    model = module.MarketResidualModel.from_dict(payload)
    coefficients[0] = 999.0
    assert model.coefficients is not None
    assert model.coefficients[0] == 0.0


def synthetic(kind):
    x = np.linspace(-1, 1, 60).reshape(-1, 1)
    if kind == "binary":
        return x, np.tile([0, 1], 30), np.full(60, 0.5)
    return x, np.tile([0, 1, 2], 20), np.tile([0.3, 0.3, 0.4], (60, 1))


@pytest.mark.parametrize("kind", ["binary", "multinomial"])
def test_failed_optimizer_never_publishes_model(kind, monkeypatch):
    def failed(objective, initial, **kwargs):
        return SimpleNamespace(success=False, fun=1.0, x=initial)

    monkeypatch.setattr(module, "minimize", failed)
    cls = module.MarketResidualModel if kind == "binary" else module.MultinomialMarketResidualModel
    model = cls()
    with pytest.raises(RuntimeError, match="optimization failed"):
        model.fit(*synthetic(kind))
    assert model.coefficients is None and model.means is None and model.scales is None


def test_invalid_refit_does_not_replace_existing_model():
    model = module.MarketResidualModel.from_dict(artifact())
    before = copy.deepcopy(model.to_dict())
    with pytest.raises(ValueError):
        model.fit(*synthetic("binary"), feature_names=("x", "extra"))
    assert model.to_dict() == before


def test_multinomial_outcome_cannot_be_silently_truncated():
    x, y, market = synthetic("multinomial")
    y = y.astype(float)
    y[0] = 1.9
    with pytest.raises(ValueError):
        module.MultinomialMarketResidualModel().fit(x, y, market)


@pytest.mark.parametrize("kind", ["binary", "multinomial"])
def test_analytic_gradient_agrees_with_independent_central_difference(kind, monkeypatch):
    original = module.minimize
    checked = []

    def inspect_gradient(objective, initial, *, jac, **kwargs):
        point = np.linspace(-0.3, 0.7, len(initial))
        epsilon = 1e-6
        basis = np.eye(len(initial)) * epsilon
        numeric = np.array([(objective(point + step) - objective(point - step)) / (2 * epsilon) for step in basis])
        np.testing.assert_allclose(jac(point), numeric, rtol=2e-5, atol=1e-6)
        checked.append(True)
        return original(objective, initial, jac=jac, **kwargs)

    monkeypatch.setattr(module, "minimize", inspect_gradient)
    cls = module.MarketResidualModel if kind == "binary" else module.MultinomialMarketResidualModel
    cls().fit(*synthetic(kind))
    assert checked == [True]
