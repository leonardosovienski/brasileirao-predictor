"""Synthetic mathematical regressions; no real forecasts, prices or outcomes."""

import math
from dataclasses import FrozenInstanceError, asdict

import pytest

from brasileirao_predictor.research.price_strength_reliability import blend, fit_weight


def test_binary_interior_solution_uses_positive_class_brier_once() -> None:
    fitted = fit_weight([(0.8, 0.2)] * 2, [(0.2, 0.8)] * 2, [0, 1])
    assert fitted.weight == pytest.approx(0.5)
    assert fitted.n == 2
    assert fitted.dimension == 2
    assert fitted.numerator == pytest.approx(0.36)
    assert fitted.denominator == pytest.approx(0.72)
    assert fitted.model_loss == pytest.approx(0.34)
    assert fitted.market_loss == pytest.approx(0.34)
    assert fitted.blended_loss == pytest.approx(0.25)
    assert blend((0.8, 0.2), (0.2, 0.8), fitted.weight) == pytest.approx((0.5, 0.5))


def test_three_class_interior_solution_sums_all_classes() -> None:
    fitted = fit_weight([(0.8, 0.1, 0.1)] * 4, [(0.2, 0.4, 0.4)] * 4, [0, 0, 1, 2])
    assert fitted.weight == pytest.approx(0.5)
    assert fitted.n == 4
    assert fitted.dimension == 3
    assert fitted.numerator == pytest.approx(1.08)
    assert fitted.denominator == pytest.approx(2.16)
    assert fitted.model_loss == pytest.approx(0.76)
    assert fitted.market_loss == pytest.approx(0.76)
    assert fitted.blended_loss == pytest.approx(0.625)


@pytest.mark.parametrize("outcome, expected", [(0, 1.0), (1, 0.0)])
def test_unconstrained_solution_is_clipped_to_convex_endpoints(outcome, expected) -> None:
    fitted = fit_weight([(0.8, 0.2)], [(0.2, 0.8)], [outcome])
    assert fitted.weight == expected
    assert fitted.blended_loss == pytest.approx(min(fitted.model_loss, fitted.market_loss))


@pytest.mark.parametrize("vector, labels", [((0.5, 0.5), [0, 1]), ((0.2, 0.3, 0.5), [2, 1])])
def test_identical_model_and_market_choose_market_for_zero_denominator(vector, labels) -> None:
    fitted = fit_weight([vector] * 2, [vector] * 2, labels)
    assert fitted.weight == 0
    assert fitted.numerator == fitted.denominator == 0
    assert fitted.model_loss == fitted.market_loss == fitted.blended_loss


def test_repeated_vectors_are_not_mistaken_for_duplicate_event_ids() -> None:
    fitted = fit_weight([(0.8, 0.2)] * 3, [(0.2, 0.8)] * 3, [0, 0, 1])
    assert fitted.n == 3
    assert fitted.weight == pytest.approx(7 / 9)
    assert fitted.blended_loss == pytest.approx(2 / 9)


def test_input_order_does_not_change_fit_and_inputs_are_not_modified() -> None:
    models = [[0.7, 0.2, 0.1], [0.3, 0.2, 0.5], [0.1, 0.6, 0.3]]
    markets = [[0.4, 0.3, 0.3], [0.2, 0.3, 0.5], [0.3, 0.3, 0.4]]
    labels = [0, 1, 2]
    original = [row[:] for row in models], [row[:] for row in markets], labels[:]
    fitted = fit_weight(models, markets, labels)
    reversed_fit = fit_weight(reversed(models), reversed(markets), reversed(labels))
    assert asdict(reversed_fit) == pytest.approx(asdict(fitted))
    assert (models, markets, labels) == original
    with pytest.raises(FrozenInstanceError):
        fitted.weight = 0.5


def test_joint_class_permutation_preserves_multiclass_fit() -> None:
    models = [(0.8, 0.1, 0.1), (0.3, 0.4, 0.3)]
    markets = [(0.2, 0.3, 0.5), (0.4, 0.3, 0.3)]
    fitted = fit_weight(models, markets, [0, 1])
    permuted = fit_weight([row[::-1] for row in models], [row[::-1] for row in markets], [2, 1])
    assert asdict(permuted) == pytest.approx(asdict(fitted))


def test_fit_accepts_ordered_generators_without_consuming_them_twice() -> None:
    fitted = fit_weight(((x for x in (0.8, 0.2)) for _ in range(2)), iter([(0.2, 0.8)] * 2), iter([0, 1]))
    assert fitted.weight == pytest.approx(0.5)
    assert fitted.n == 2


@pytest.mark.parametrize("dimension", [2, 3])
def test_fitted_weight_minimizes_synthetic_loss_along_the_convex_segment(dimension) -> None:
    model = (0.8, 0.2) if dimension == 2 else (0.8, 0.1, 0.1)
    market = (0.2, 0.8) if dimension == 2 else (0.2, 0.4, 0.4)
    labels = [0, 1] if dimension == 2 else [0, 0, 1, 2]
    fitted = fit_weight([model] * len(labels), [market] * len(labels), labels)
    classes = range(1) if dimension == 2 else range(3)
    for weight in (0, 0.25, 0.5, 0.75, 1):
        vector = blend(model, market, weight)
        independent_loss = sum((vector[i] - (label == i)) ** 2 for label in labels for i in classes) / len(labels)
        assert fitted.blended_loss <= independent_loss + 1e-14


@pytest.mark.parametrize("weight", [0, 0.25, 0.5, 1])
def test_blend_is_normalized_convex_and_returns_an_immutable_tuple(weight) -> None:
    model, market = [0.8, 0.1, 0.1], [0.2, 0.4, 0.4]
    result = blend(model, market, weight)
    assert isinstance(result, tuple)
    assert math.fsum(result) == pytest.approx(1)
    assert all(min(p, q) <= b <= max(p, q) for p, q, b in zip(model, market, result, strict=True))
    assert model == [0.8, 0.1, 0.1]
    assert market == [0.2, 0.4, 0.4]


def test_endpoints_preserve_valid_input_without_silent_renormalization() -> None:
    model = (0.3, 0.7000000001)
    market = (0.5, 0.5)
    assert blend(model, market, 1) == model
    assert blend(model, market, 0) == market


@pytest.mark.parametrize(
    "invalid",
    [
        [],
        [1],
        [0.25] * 4,
        [0.2, 0.7],
        [-0.1, 1.1],
        [True, 0],
        [False, 1],
        [float("nan"), 1],
        [float("inf"), 0],
        [-float("inf"), 1],
        [10**400, 0],
        ["0.5", 0.5],
        None,
        "01",
        {0.5},
        {"yes": 0.5, "no": 0.5},
    ],
)
def test_invalid_probability_vectors_are_rejected_in_fit_and_blend(invalid) -> None:
    with pytest.raises(ValueError):
        fit_weight([invalid], [(0.5, 0.5)], [0])
    with pytest.raises(ValueError):
        fit_weight([(0.5, 0.5)], [invalid], [0])
    with pytest.raises(ValueError):
        blend(invalid, (0.5, 0.5), 0.5)
    with pytest.raises(ValueError):
        blend((0.5, 0.5), invalid, 0.5)


@pytest.mark.parametrize("weight", [True, False, -0.1, 1.1, float("nan"), float("inf"), "0.5", None, 10**400])
def test_invalid_blend_weights_are_rejected(weight) -> None:
    with pytest.raises(ValueError, match="weight"):
        blend((0.8, 0.2), (0.2, 0.8), weight)


@pytest.mark.parametrize("outcome", [True, False, -1, 2, 0.0, float("nan"), "0", None])
def test_binary_outcomes_require_integer_class_indices(outcome) -> None:
    with pytest.raises(ValueError, match="outcomes"):
        fit_weight([(0.5, 0.5)], [(0.5, 0.5)], [outcome])


def test_inconsistent_dimensions_are_rejected() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        fit_weight([(0.5, 0.5), (0.2, 0.3, 0.5)], [(0.5, 0.5)] * 2, [0, 1])
    with pytest.raises(ValueError, match="dimensions"):
        fit_weight([(0.2, 0.3, 0.5)], [(0.5, 0.5)], [0])
    with pytest.raises(ValueError, match="dimensions"):
        blend((0.5, 0.5), (0.2, 0.3, 0.5), 0.5)


@pytest.mark.parametrize(
    "models, markets, outcomes",
    [
        ([], [], []),
        ([(0.5, 0.5)], [], [0]),
        ([(0.5, 0.5)], [(0.5, 0.5)], []),
        ([(0.5, 0.5)], [(0.5, 0.5)], [0, 1]),
        (None, [], []),
        ([], None, []),
        ([], [], None),
        ({(0.5, 0.5)}, [(0.5, 0.5)], [0]),
        ([(0.5, 0.5)], [(0.5, 0.5)], {0}),
    ],
)
def test_empty_unordered_or_unaligned_fitting_samples_are_rejected(models, markets, outcomes) -> None:
    with pytest.raises(ValueError):
        fit_weight(models, markets, outcomes)
