"""Market-anchored residual model for binary football markets.

The market no-vig probability is an offset, not an ordinary feature. The
model can only move that baseline when pre-event covariates justify it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize


def _logit(probability: float) -> float:
    if not 0 < probability < 1:
        raise ValueError("probability must be strictly between zero and one")
    return math.log(probability / (1.0 - probability))


def _sigmoid(value):
    value = np.asarray(value, dtype=float)
    return np.where(value >= 0, 1.0 / (1.0 + np.exp(-value)), np.exp(value) / (1.0 + np.exp(value)))


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

    def fit(
        self,
        features: np.ndarray,
        outcomes: np.ndarray,
        market_probabilities: np.ndarray,
        *,
        feature_names: tuple[str, ...] | None = None,
    ) -> MarketResidualModel:
        x = np.asarray(features, dtype=float)
        y = np.asarray(outcomes, dtype=float)
        market = np.asarray(market_probabilities, dtype=float)
        if x.ndim != 2 or y.shape != (len(x),) or market.shape != (len(x),):
            raise ValueError("incompatible residual training shapes")
        if len(x) < max(20, x.shape[1] * 5) or not set(np.unique(y)).issubset({0.0, 1.0}):
            raise ValueError("insufficient or invalid residual training sample")
        if np.any((market <= 0) | (market >= 1)) or not np.isfinite(x).all():
            raise ValueError("training data contains invalid values")
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

        result = minimize(objective, np.zeros(design.shape[1]), method="BFGS")
        if not result.success and not np.isfinite(result.fun):
            raise RuntimeError("residual optimization failed")
        beta = np.asarray(result.x, dtype=float)
        fitted = _sigmoid(offset + design @ beta)
        weights = fitted * (1.0 - fitted)
        hessian = design.T @ (design * weights[:, None])
        hessian[1:, 1:] += self.l2 * np.eye(design.shape[1] - 1)
        self.coefficients = beta
        self.means = means
        self.scales = scales
        self.covariance = np.linalg.pinv(hessian)
        self.feature_names = feature_names or tuple(f"x{i}" for i in range(x.shape[1]))
        if len(self.feature_names) != x.shape[1]:
            raise ValueError("feature_names does not match feature count")
        return self

    def predict(self, features: np.ndarray, market_probability: float, *, z_score: float = 1.96) -> ResidualPrediction:
        if self.coefficients is None or self.means is None or self.scales is None or self.covariance is None:
            raise RuntimeError("residual model is not fitted")
        row = np.asarray(features, dtype=float)
        if row.shape != self.means.shape or not np.isfinite(row).all():
            raise ValueError("invalid residual feature row")
        design = np.r_[1.0, (row - self.means) / self.scales]
        residual = float(design @ self.coefficients)
        standard_error = math.sqrt(max(0.0, float(design @ self.covariance @ design)))
        anchor = _logit(market_probability)
        probability = float(_sigmoid(anchor + residual))
        lower = float(_sigmoid(anchor + residual - z_score * standard_error))
        upper = float(_sigmoid(anchor + residual + z_score * standard_error))
        return ResidualPrediction(probability, lower, upper, market_probability, residual)

    def to_dict(self) -> dict:
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
        }

    @classmethod
    def from_dict(cls, payload: dict) -> MarketResidualModel:
        if payload.get("schema_version") != "market-residual/1" or payload.get("capital_enabled") is not False:
            raise ValueError("invalid or unsafe residual model artifact")
        model = cls(l2=float(payload["l2"]), feature_names=tuple(payload["feature_names"]))
        model.coefficients = np.asarray(payload["coefficients"], dtype=float)
        model.means = np.asarray(payload["means"], dtype=float)
        model.scales = np.asarray(payload["scales"], dtype=float)
        model.covariance = np.asarray(payload["covariance"], dtype=float)
        expected = len(model.feature_names)
        if (
            model.coefficients.shape != (expected + 1,)
            or model.means.shape != (expected,)
            or model.scales.shape != (expected,)
            or model.covariance.shape != (expected + 1, expected + 1)
        ):
            raise ValueError("residual model artifact has incompatible shapes")
        return model
