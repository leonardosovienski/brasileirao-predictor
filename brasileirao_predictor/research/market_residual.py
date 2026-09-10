"""Market-anchored residual model for binary football markets.

The market no-vig probability is an offset, not an ordinary feature. The
model can only move that baseline when pre-event covariates justify it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


def _logit(probability: float) -> float:
    if not 0 < probability < 1:
        raise ValueError("probability must be strictly between zero and one")
    return math.log(probability / (1.0 - probability))


def _sigmoid(value):
    return expit(np.asarray(value, dtype=float))


def _nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")


def _feature_names(names, count):
    if (
        not isinstance(names, (list, tuple))
        or len(names) != count
        or any(not isinstance(name, str) or not name.strip() for name in names)
        or len(set(names)) != count
    ):
        raise ValueError("feature_names must be unique nonblank names matching feature count")
    return tuple(names)


def _validate_arrays(coefficients, means, scales, *, multinomial=False):
    if coefficients is None or means is None or scales is None:
        raise RuntimeError("residual model is not fitted")
    if means.ndim != 1 or scales.shape != means.shape:
        raise ValueError("residual model artifact has incompatible shapes")
    expected = (2, len(means) + 1) if multinomial else (len(means) + 1,)
    if coefficients.shape != expected or any(not np.isfinite(a).all() for a in (coefficients, means, scales)):
        raise ValueError("residual model artifact has invalid coefficients or preprocessing")
    if np.any(scales <= 0):
        raise ValueError("residual model scales must be positive")


def _optimization_coefficients(result, shape):
    beta = np.asarray(result.x, dtype=float)
    if not result.success or not np.isfinite(result.fun) or beta.shape != shape or not np.isfinite(beta).all():
        raise RuntimeError("residual optimization failed")
    return beta


@dataclass(frozen=True)
class ResidualPrediction:
    probability: float
    lower_probability: float
    upper_probability: float
    market_probability: float
    residual_log_odds: float


@dataclass
class MarketResidualModel:
    l2: float = 5.0
    feature_names: tuple[str, ...] = ()
    coefficients: np.ndarray | None = None
    means: np.ndarray | None = None
    scales: np.ndarray | None = None
    covariance: np.ndarray | None = None

    def _validate_state(self):
        _nonnegative(self.l2, "l2")
        _validate_arrays(self.coefficients, self.means, self.scales)
        assert self.means is not None
        _feature_names(self.feature_names, len(self.means))
        covariance = self.covariance
        if covariance is None:
            raise RuntimeError("residual model is not fitted")
        if covariance.shape != (len(self.means) + 1, len(self.means) + 1) or not np.isfinite(covariance).all():
            raise ValueError("residual covariance has invalid shape or values")
        tolerance = 1e-12 * max(1.0, float(np.abs(covariance).max()))
        if not np.allclose(covariance, covariance.T, rtol=0, atol=tolerance):
            raise ValueError("residual covariance must be symmetric")
        if float(np.linalg.eigvalsh(covariance).min()) < -tolerance:
            raise ValueError("residual covariance must be positive semidefinite")

    def fit(
        self,
        features: np.ndarray,
        outcomes: np.ndarray,
        market_probabilities: np.ndarray,
        *,
        feature_names: tuple[str, ...] | None = None,
    ) -> MarketResidualModel:
        _nonnegative(self.l2, "l2")
        x = np.asarray(features, dtype=float)
        y = np.asarray(outcomes, dtype=float)
        market = np.asarray(market_probabilities, dtype=float)
        if x.ndim != 2 or y.shape != (len(x),) or market.shape != (len(x),):
            raise ValueError("incompatible residual training shapes")
        if len(x) < max(20, x.shape[1] * 5) or not set(np.unique(y)).issubset({0.0, 1.0}):
            raise ValueError("insufficient or invalid residual training sample")
        if np.any((market <= 0) | (market >= 1)) or not np.isfinite(market).all() or not np.isfinite(x).all():
            raise ValueError("training data contains invalid values")
        names = _feature_names(
            feature_names if feature_names is not None else tuple(f"x{i}" for i in range(x.shape[1])), x.shape[1]
        )
        means = x.mean(axis=0)
        scales = x.std(axis=0)
        scales[scales < 1e-12] = 1.0
        z = (x - means) / scales
        design = np.column_stack([np.ones(len(z)), z])
        offset = np.array([_logit(float(p)) for p in market])

        def objective(beta):
            eta = offset + design @ beta
            loss = np.logaddexp(0.0, eta).sum() - y @ eta
            penalty = 0.5 * self.l2 * float(beta[1:] @ beta[1:])
            return float(loss + penalty)

        def gradient(beta):
            grad = design.T @ (_sigmoid(offset + design @ beta) - y)
            grad[1:] += self.l2 * beta[1:]
            return grad

        result = minimize(objective, np.zeros(design.shape[1]), jac=gradient, method="BFGS")
        beta = _optimization_coefficients(result, (design.shape[1],))
        fitted = _sigmoid(offset + design @ beta)
        weights = fitted * (1.0 - fitted)
        hessian = design.T @ (design * weights[:, None])
        hessian[1:, 1:] += self.l2 * np.eye(design.shape[1] - 1)
        candidate = MarketResidualModel(self.l2, names, beta, means, scales, np.linalg.pinv(hessian))
        candidate._validate_state()
        self.coefficients, self.means, self.scales = beta, means, scales
        self.covariance, self.feature_names = candidate.covariance, names
        return self

    def predict(self, features: np.ndarray, market_probability: float, *, z_score: float = 1.96) -> ResidualPrediction:
        self._validate_state()
        _nonnegative(z_score, "z_score")
        if self.coefficients is None or self.means is None or self.scales is None or self.covariance is None:
            raise RuntimeError("residual model is not fitted")
        row = np.asarray(features, dtype=float)
        if row.shape != self.means.shape or not np.isfinite(row).all():
            raise ValueError("invalid residual feature row")
        design = np.r_[1.0, (row - self.means) / self.scales]
        residual = float(design @ self.coefficients)
        variance = float(design @ self.covariance @ design)
        if not math.isfinite(residual) or not math.isfinite(variance):
            raise ValueError("residual prediction overflow")
        standard_error = math.sqrt(max(0.0, variance))
        anchor = _logit(market_probability)
        probability = float(_sigmoid(anchor + residual))
        lower = float(_sigmoid(anchor + residual - z_score * standard_error))
        upper = float(_sigmoid(anchor + residual + z_score * standard_error))
        return ResidualPrediction(probability, lower, upper, market_probability, residual)

    def to_dict(self) -> dict:
        self._validate_state()
        if self.coefficients is None or self.means is None or self.scales is None or self.covariance is None:
            raise RuntimeError("residual model is not fitted")
        return {
            "schema_version": "market-residual/1",
            "l2": self.l2,
            "feature_names": list(self.feature_names),
            "coefficients": self.coefficients.tolist(),
            "means": self.means.tolist(),
            "scales": self.scales.tolist(),
            "covariance": self.covariance.tolist(),
            "capital_enabled": False,
            "reader_contract_version": "residual-numerics/2",
            "evidence_scope": "MODEL_CONTRACT_ONLY",
            "provenance_verified": False,
            "economic_evidence_eligible": False,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> MarketResidualModel:
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != "market-residual/1"
            or payload.get("capital_enabled") is not False
        ):
            raise ValueError("invalid or unsafe residual model artifact")
        try:
            _nonnegative(payload["l2"], "l2")
            model = cls(l2=float(payload["l2"]), feature_names=tuple(payload["feature_names"]))
            model.coefficients = np.array(payload["coefficients"], dtype=float, copy=True)
            model.means = np.array(payload["means"], dtype=float, copy=True)
            model.scales = np.array(payload["scales"], dtype=float, copy=True)
            model.covariance = np.array(payload["covariance"], dtype=float, copy=True)
            _feature_names(payload["feature_names"], len(model.means))
            model._validate_state()
        except (KeyError, TypeError) as exc:
            raise ValueError("residual model artifact is incomplete or invalid") from exc
        return model


@dataclass
class MultinomialMarketResidualModel:
    """Correção 1X2 regularizada com o mercado de-vig como offset.

    A identificação usa a terceira classe como referência: os parâmetros
    movem apenas as classes 0/2 e 1/2; o softmax normaliza as três
    probabilidades. No painel 1X2, a ordem é away/draw/home.
    """

    l2: float = 5.0
    coefficients: np.ndarray | None = None
    means: np.ndarray | None = None
    scales: np.ndarray | None = None

    def fit(
        self, features: np.ndarray, outcomes: np.ndarray, market_probabilities: np.ndarray
    ) -> MultinomialMarketResidualModel:
        _nonnegative(self.l2, "l2")
        x = np.asarray(features, dtype=float)
        y = np.asarray(outcomes)
        market = np.asarray(market_probabilities, dtype=float)
        if x.ndim != 2 or y.shape != (len(x),) or market.shape != (len(x), 3):
            raise ValueError("incompatible multinomial residual training shapes")
        if len(x) < max(50, x.shape[1] * 10) or not set(np.unique(y)).issubset({0, 1, 2}):
            raise ValueError("insufficient or invalid multinomial residual sample")
        y = y.astype(int)
        if (
            np.any((market <= 0) | (market >= 1))
            or not np.isfinite(market).all()
            or not np.allclose(market.sum(axis=1), 1.0, atol=1e-8)
            or not np.isfinite(x).all()
        ):
            raise ValueError("training data contains invalid values")
        means = x.mean(axis=0)
        scales = x.std(axis=0)
        scales[scales < 1e-12] = 1.0
        design = np.column_stack([np.ones(len(x)), (x - means) / scales])
        offsets = np.log(market)
        width = design.shape[1]

        def objective(flat):
            beta = np.asarray(flat).reshape(2, width)
            logits = offsets.copy()
            logits[:, 0] += design @ beta[0]
            logits[:, 1] += design @ beta[1]
            logits -= logits.max(axis=1, keepdims=True)
            log_norm = np.log(np.exp(logits).sum(axis=1))
            loss = -(logits[np.arange(len(y)), y] - log_norm).sum()
            return float(loss + 0.5 * self.l2 * (beta[:, 1:] ** 2).sum())

        def gradient(flat):
            beta = np.asarray(flat).reshape(2, width)
            logits = offsets.copy()
            logits[:, :2] += design @ beta.T
            logits -= logits.max(axis=1, keepdims=True)
            probabilities = np.exp(logits)
            probabilities /= probabilities.sum(axis=1, keepdims=True)
            errors = probabilities - np.eye(3)[y]
            grad = errors[:, :2].T @ design
            grad[:, 1:] += self.l2 * beta[:, 1:]
            return grad.ravel()

        result = minimize(objective, np.zeros(2 * width), jac=gradient, method="BFGS")
        beta = _optimization_coefficients(result, (2 * width,)).reshape(2, width)
        _validate_arrays(beta, means, scales, multinomial=True)
        self.coefficients, self.means, self.scales = beta, means, scales
        return self

    def predict_proba(self, features: np.ndarray, market_probabilities: np.ndarray) -> np.ndarray:
        _nonnegative(self.l2, "l2")
        _validate_arrays(self.coefficients, self.means, self.scales, multinomial=True)
        if self.coefficients is None or self.means is None or self.scales is None:
            raise RuntimeError("multinomial residual model is not fitted")
        x = np.asarray(features, dtype=float)
        market = np.asarray(market_probabilities, dtype=float)
        one = x.ndim == 1
        if one:
            x, market = x[None, :], market[None, :]
        if x.ndim != 2 or x.shape[1:] != self.means.shape or market.shape != (len(x), 3):
            raise ValueError("invalid multinomial residual prediction shapes")
        if (
            not np.isfinite(x).all()
            or not np.isfinite(market).all()
            or np.any((market <= 0) | (market >= 1))
            or not np.allclose(market.sum(axis=1), 1.0, atol=1e-8)
        ):
            raise ValueError("invalid multinomial residual prediction values")
        design = np.column_stack([np.ones(len(x)), (x - self.means) / self.scales])
        logits = np.log(market)
        logits[:, 0] += design @ self.coefficients[0]
        logits[:, 1] += design @ self.coefficients[1]
        if not np.isfinite(logits).all():
            raise ValueError("multinomial residual prediction overflow")
        logits -= logits.max(axis=1, keepdims=True)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        return probabilities[0] if one else probabilities
