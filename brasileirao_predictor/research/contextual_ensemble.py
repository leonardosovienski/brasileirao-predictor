"""Leakage-safe experimental contextual booster over baseline 1X2 probabilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
from predictor_core.measurement.metrics import brier, log_loss, rps

CONTEXT_FEATURES = (
    "rest_days_delta",
    "away_travel_km",
    "synthetic_surface",
    "surface_familiarity_delta",
    "coach_tenure_delta",
)


def _timestamp(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("contextual timestamps must be timezone-aware")
    return parsed


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


@dataclass(frozen=True)
class _Stump:
    feature: int
    threshold: float
    left: np.ndarray
    right: np.ndarray


class ContextualBooster:
    """Small deterministic gradient-boosted stump model for research only."""

    def __init__(self, *, iterations: int = 40, learning_rate: float = 0.08) -> None:
        self.iterations = iterations
        self.learning_rate = learning_rate
        self.stumps: list[_Stump] = []

    def fit(self, x: np.ndarray, y: np.ndarray, baseline: np.ndarray) -> ContextualBooster:
        logits = np.log(np.clip(baseline, 1e-12, 1.0))
        target = np.eye(3)[y]
        self.stumps = []
        for _ in range(self.iterations):
            residual = target - _softmax(logits)
            best: tuple[float, _Stump] | None = None
            for feature in range(x.shape[1]):
                threshold = float(np.median(x[:, feature]))
                left_mask = x[:, feature] <= threshold
                if left_mask.all() or (~left_mask).all():
                    continue
                left = residual[left_mask].mean(axis=0)
                right = residual[~left_mask].mean(axis=0)
                gain = float(left_mask.sum() * np.square(left).sum() + (~left_mask).sum() * np.square(right).sum())
                stump = _Stump(feature, threshold, left, right)
                if best is None or gain > best[0]:
                    best = (gain, stump)
            if best is None:
                break
            stump = best[1]
            logits += self.learning_rate * np.where(
                (x[:, stump.feature] <= stump.threshold)[:, None], stump.left, stump.right
            )
            self.stumps.append(stump)
        return self

    def predict_proba(self, x: np.ndarray, baseline: np.ndarray) -> np.ndarray:
        logits = np.log(np.clip(baseline, 1e-12, 1.0))
        for stump in self.stumps:
            logits += self.learning_rate * np.where(
                (x[:, stump.feature] <= stump.threshold)[:, None], stump.left, stump.right
            )
        return _softmax(logits)


def _prepare(train: list[dict[str, Any]], test: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    medians = []
    for name in CONTEXT_FEATURES:
        values = [float(row["context"][name]) for row in train if row["context"].get(name) is not None]
        medians.append(float(np.median(values)) if values else 0.0)

    def matrix(rows: list[dict[str, Any]]) -> np.ndarray:
        result = []
        for row in rows:
            values, missing = [], []
            for name, median in zip(CONTEXT_FEATURES, medians, strict=True):
                raw = row["context"].get(name)
                values.append(median if raw is None else float(raw))
                missing.append(float(raw is None))
            result.append(values + missing)
        return np.asarray(result, dtype=float)

    return matrix(train), matrix(test)


def evaluate_contextual_ensemble(
    rows: list[dict[str, Any]],
    *,
    minimum_train: int = 100,
    minimum_test: int = 30,
    minimum_context_coverage: float = 0.6,
) -> dict[str, Any]:
    """Evaluate by expanding kickoff-date groups; never changes serving."""
    valid = []
    for row in rows:
        kickoff = _timestamp(row["kickoff_at"])
        available = _timestamp(row["context_available_at"])
        probabilities = [float(value) for value in row["baseline_probs"]]
        if available >= kickoff:
            raise ValueError("context must be available strictly before kickoff")
        if len(probabilities) != 3 or any(not math.isfinite(value) or value <= 0 for value in probabilities):
            raise ValueError("baseline_probs must contain three positive finite values")
        total = sum(probabilities)
        normalized = [value / total for value in probabilities]
        valid.append({**row, "baseline_probs": normalized, "_kickoff": kickoff})
    valid.sort(key=lambda row: (row["_kickoff"], str(row.get("event_id", ""))))
    coverage = (
        sum(any(row["context"].get(name) is not None for name in CONTEXT_FEATURES) for row in valid) / len(valid)
        if valid
        else 0.0
    )
    if coverage < minimum_context_coverage or len(valid) < minimum_train + minimum_test:
        return {"status": "BLOCKED_DATA", "n": len(valid), "context_coverage": coverage, "serving_changed": False}

    groups = sorted({row["_kickoff"].date() for row in valid})
    treated: list[list[float]] = []
    controls: list[list[float]] = []
    outcomes: list[int] = []
    for day in groups:
        train = [row for row in valid if row["_kickoff"].date() < day]
        test = [row for row in valid if row["_kickoff"].date() == day]
        if len(train) < minimum_train:
            continue
        x_train, x_test = _prepare(train, test)
        baseline_train = np.asarray([row["baseline_probs"] for row in train], dtype=float)
        baseline_test = np.asarray([row["baseline_probs"] for row in test], dtype=float)
        y_train = np.asarray([int(row["outcome"]) for row in train], dtype=int)
        prediction = ContextualBooster().fit(x_train, y_train, baseline_train).predict_proba(x_test, baseline_test)
        treated.extend(prediction.tolist())
        controls.extend(baseline_test.tolist())
        outcomes.extend(int(row["outcome"]) for row in test)
    if len(outcomes) < minimum_test:
        return {"status": "BLOCKED_DATA", "n": len(outcomes), "context_coverage": coverage, "serving_changed": False}
    metrics = {
        "rps_delta": rps(treated, outcomes) - rps(controls, outcomes),
        "brier_delta": brier(treated, outcomes) - brier(controls, outcomes),
        "log_loss_delta": log_loss(treated, outcomes) - log_loss(controls, outcomes),
    }
    finite = all(math.isfinite(value) for value in metrics.values())
    return {
        "status": "PASS" if finite else "FAIL_NUMERIC",
        "verdict": "GO_CANDIDATE" if finite and all(value < 0 for value in metrics.values()) else "NO_GO",
        "n": len(outcomes),
        "context_coverage": coverage,
        "metrics": metrics,
        "validation": "expanding_window_by_kickoff_date",
        "serving_changed": False,
    }
