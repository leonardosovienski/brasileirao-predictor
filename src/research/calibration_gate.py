"""Deterministic promotion gate for frozen probability-calibration reports."""

from typing import Any


def assess_a10(report: dict[str, Any]) -> dict[str, Any]:
    required = ("rps", "brier", "log_loss", "brier_draw")
    metrics = report.get("metrics")
    if not isinstance(metrics, dict) or any(name not in metrics for name in required):
        raise ValueError("A10 report is missing required metrics")
    deltas = {name: float(metrics[name]["delta_treatment_minus_control"]) for name in required}
    primary_improved = deltas["brier_draw"] < 0
    guardrails_not_worse = all(deltas[name] <= 0 for name in ("rps", "brier", "log_loss"))
    promoted = primary_improved and guardrails_not_worse
    return {
        "schema_version": "a10-promotion-gate/v1",
        "verdict": "GO_CANDIDATE_FOR_NEW_PROSPECTIVE_PROTOCOL" if promoted else "NO_GO_ARCHIVE_A10",
        "primary_improved": primary_improved,
        "guardrails_not_worse": guardrails_not_worse,
        "deltas": deltas,
        "serving_changed": False,
        "holdouts_reopened": False,
    }
