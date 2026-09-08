"""Pure Brier-optimal shrinkage of one model toward one market distribution.

Fit one weight per market on paired, temporally out-of-sample model forecasts,
market probabilities and subsequently observed labels. The caller must enforce
unique event IDs, aligned side ordering, availability cutoffs, provenance and
separation of fitting and evaluation samples. This mathematical API has no IDs,
timestamps, file, database or network access; it cannot certify those properties.
Identical vectors can belong to distinct events and are not deduplicated here.

For three classes the Brier loss sums all classes. For two classes it uses only
index 0 (the positive class: over for OU2.5, yes for BTTS). Reported losses are
means per observation; binary and three-class loss scales must not be pooled.
The convex combination minimizes fitting-sample Brier, not betting profit. A
zero model weight is valid and means reproducing the supplied market vector.
No improvement out of sample, tradable price or economic advantage is implied.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from numbers import Real

_NORMALIZATION_TOLERANCE = 1e-9


@dataclass(frozen=True)
class ReliabilityWeight:
    """Fitted model weight and descriptive, in-sample mean Brier losses."""

    weight: float
    n: int
    dimension: int
    model_loss: float
    market_loss: float
    blended_loss: float
    numerator: float
    denominator: float


def _ordered_tuple(values: Iterable, name: str) -> tuple:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError(f"{name} must be an ordered iterable")
    try:
        return tuple(values)
    except TypeError as exc:
        raise ValueError(f"{name} must be an ordered iterable") from exc


def _probability(value: float, name: str) -> float:
    # Bounds before conversion also reject arbitrarily large integers safely.
    if isinstance(value, bool) or not isinstance(value, Real) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be a finite number in [0, 1]")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number in [0, 1]")
    return result


def _vector(values: Iterable[float], name: str) -> tuple[float, ...]:
    raw = _ordered_tuple(values, name)
    if len(raw) not in (2, 3):
        raise ValueError(f"{name} must contain 2 or 3 probabilities")
    vector = tuple(_probability(value, f"{name}[{index}]") for index, value in enumerate(raw))
    if not math.isclose(math.fsum(vector), 1.0, rel_tol=0.0, abs_tol=_NORMALIZATION_TOLERANCE):
        raise ValueError(f"{name} probabilities must sum to 1")
    return vector


def _combine(model: tuple[float, ...], market: tuple[float, ...], weight: float) -> tuple[float, ...]:
    if weight == 0:
        return market
    if weight == 1:
        return model
    return tuple(weight * p + (1.0 - weight) * q for p, q in zip(model, market, strict=True))


def blend(vector: Iterable[float], market: Iterable[float], weight: float) -> tuple[float, ...]:
    """Return ``weight * vector + (1 - weight) * market`` without renormalizing.

    Inputs must have matching dimension 2 or 3, finite probabilities in [0, 1]
    and sum to 1 within absolute floating-point tolerance 1e-9. Weight must be a
    finite number in [0, 1]; booleans are not numbers accepted by this API.
    """
    model_vector = _vector(vector, "vector")
    market_vector = _vector(market, "market")
    if len(model_vector) != len(market_vector):
        raise ValueError("model and market dimensions must match")
    alpha = _probability(weight, "weight")
    return _combine(model_vector, market_vector, alpha)


def fit_weight(
    model_vectors: Iterable[Iterable[float]],
    market_vectors: Iterable[Iterable[float]],
    outcomes: Iterable[int],
) -> ReliabilityWeight:
    """Fit one convex weight from a nonempty paired sample of one market.

    Outcomes are actual zero-based class indices, not positive-class indicators.
    All observations must share dimension and side ordering. The closed form is
    ``clip(sum((p-q)*(y-q)) / sum((p-q)**2), 0, 1)`` over the scored classes.
    An exactly zero denominator returns weight 0. Invalid input raises ValueError
    and is never silently removed, filled, normalized or matched by position
    after dropping rows. Temporal eligibility and unique IDs belong to callers.
    """
    raw_models = _ordered_tuple(model_vectors, "model_vectors")
    raw_markets = _ordered_tuple(market_vectors, "market_vectors")
    labels = _ordered_tuple(outcomes, "outcomes")
    n = len(raw_models)
    if not n:
        raise ValueError("fitting sample must be nonempty")
    if len(raw_markets) != n or len(labels) != n:
        raise ValueError("model_vectors, market_vectors and outcomes lengths must match")
    models = tuple(_vector(value, f"model_vectors[{i}]") for i, value in enumerate(raw_models))
    markets = tuple(_vector(value, f"market_vectors[{i}]") for i, value in enumerate(raw_markets))
    dimension = len(models[0])
    if any(len(value) != dimension for value in (*models, *markets)):
        raise ValueError("all model and market dimensions must match")
    if any(type(value) is not int or not 0 <= value < dimension for value in labels):
        raise ValueError("outcomes must be integer class indices within the vector dimension")

    scored_classes = range(dimension) if dimension == 3 else range(1)
    terms = tuple(
        (p[index], q[index], float(outcome == index))
        for p, q, outcome in zip(models, markets, labels, strict=True)
        for index in scored_classes
    )
    numerator = math.fsum((p - q) * (y - q) for p, q, y in terms)
    denominator = math.fsum((p - q) ** 2 for p, q, _ in terms)
    weight = 0.0 if denominator == 0 else max(0.0, min(1.0, numerator / denominator))
    blended = tuple(_combine(p, q, weight) for p, q in zip(models, markets, strict=True))
    blended_loss = (
        math.fsum(
            (vector[index] - float(outcome == index)) ** 2
            for vector, outcome in zip(blended, labels, strict=True)
            for index in scored_classes
        )
        / n
    )
    return ReliabilityWeight(
        weight=weight,
        n=n,
        dimension=dimension,
        model_loss=math.fsum((p - y) ** 2 for p, _, y in terms) / n,
        market_loss=math.fsum((q - y) ** 2 for _, q, y in terms) / n,
        blended_loss=blended_loss,
        numerator=numerator,
        denominator=denominator,
    )
