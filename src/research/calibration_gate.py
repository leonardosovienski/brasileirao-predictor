"""Deterministic promotion gate for frozen probability-calibration reports."""

from typing import Any


def assess_a10(report: dict[str, Any]) -> dict[str, Any]:
    required = ("rps", "brier", "log_loss", "brier_draw")
    metrics = report.get("metrics")
    if not isinstance(metrics, dict) or any(name not in metrics for name in required):
        raise ValueError("A10 report is missing required metrics")
    deltas = {name: float(metrics[name]["delta_treatment_minus_control"]) for name in required}
    home_metric = metrics.get("log_loss_home_win")
    home_delta = (
        float(home_metric["delta_treatment_minus_control"])
        if isinstance(home_metric, dict) and "delta_treatment_minus_control" in home_metric
        else None
    )
    minimum_rps_gain = 0.002
    primary_improved = deltas["brier_draw"] < 0
    material_rps_gain = deltas["rps"] <= -minimum_rps_gain
    aggregate_guardrails_not_worse = all(deltas[name] <= 0 for name in ("brier", "log_loss"))
    home_win_guardrail_not_worse = home_delta is not None and home_delta <= 0
    guardrails_not_worse = aggregate_guardrails_not_worse and home_win_guardrail_not_worse
    promoted = primary_improved and material_rps_gain and guardrails_not_worse
    return {
        "schema_version": "a10-promotion-gate/v1",
        "verdict": "GO_CANDIDATE_FOR_NEW_PROSPECTIVE_PROTOCOL" if promoted else "NO_GO_ARCHIVE_A10",
        "primary_improved": primary_improved,
        "material_rps_gain": material_rps_gain,
        "minimum_rps_gain": minimum_rps_gain,
        "guardrails_not_worse": guardrails_not_worse,
        "home_win_guardrail_not_worse": home_win_guardrail_not_worse,
        "deltas": {**deltas, "log_loss_home_win": home_delta},
        "serving_changed": False,
        "holdouts_reopened": False,
    }
