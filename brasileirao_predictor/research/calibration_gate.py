"""Validate declared calibration deltas without authenticating a study or promoting serving."""

import math
from numbers import Real
from typing import Any


def _delta(metric: Any, name: str) -> float:
    if not isinstance(metric, dict) or "delta_treatment_minus_control" not in metric:
        raise ValueError(f"A10 metric {name} is missing its delta")
    value = metric["delta_treatment_minus_control"]
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"A10 metric {name} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"A10 metric {name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"A10 metric {name} must be a finite number")
    return result


def assess_a10(report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise ValueError("A10 report must be an object")
    required = ("rps", "brier", "log_loss", "brier_draw")
    metrics = report.get("metrics")
    if not isinstance(metrics, dict) or any(name not in metrics for name in required):
        raise ValueError("A10 report is missing required metrics")
    deltas = {name: _delta(metrics[name], name) for name in required}
    home_delta = _delta(metrics["log_loss_home_win"], "log_loss_home_win") if "log_loss_home_win" in metrics else None
    minimum_rps_gain = 0.002
    primary_improved = deltas["brier_draw"] < 0
    material_rps_gain = deltas["rps"] <= -minimum_rps_gain
    aggregate_guardrails_not_worse = all(deltas[name] <= 0 for name in ("brier", "log_loss"))
    home_win_guardrail_not_worse = home_delta is not None and home_delta <= 0
    guardrails_not_worse = aggregate_guardrails_not_worse and home_win_guardrail_not_worse
    promoted = primary_improved and material_rps_gain and guardrails_not_worse
    return {
        "schema_version": "a10-promotion-gate/v2",
        "verdict": "GO_CANDIDATE_FOR_NEW_PROSPECTIVE_PROTOCOL" if promoted else "NO_GO_ARCHIVE_A10",
        "primary_improved": primary_improved,
        "material_rps_gain": material_rps_gain,
        "minimum_rps_gain": minimum_rps_gain,
        "guardrails_not_worse": guardrails_not_worse,
        "home_win_guardrail_not_worse": home_win_guardrail_not_worse,
        "deltas": {**deltas, "log_loss_home_win": home_delta},
        "serving_changed": False,
        "holdouts_reopened": False,
        "provenance_verified": False,
        "economic_evidence": False,
        "capital_enabled": False,
    }
