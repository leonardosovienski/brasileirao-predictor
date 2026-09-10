"""Synthetic input-contract regressions; no frozen report or settlement is loaded."""

from copy import deepcopy
from typing import Any

import pytest

from brasileirao_predictor.research.calibration_gate import assess_a10
from brasileirao_predictor.research.residual_gate import evaluate_economic_gate


def calibration_report() -> dict[str, Any]:
    return {
        "metrics": {
            name: {"delta_treatment_minus_control": -0.01}
            for name in ("rps", "brier", "log_loss", "brier_draw", "log_loss_home_win")
        }
    }


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), True, "-0.01", None])
@pytest.mark.parametrize("metric", ["rps", "log_loss_home_win"])
def test_calibration_rejects_invalid_numeric_evidence(bad: Any, metric: str) -> None:
    report = calibration_report()
    report["metrics"][metric]["delta_treatment_minus_control"] = bad
    with pytest.raises(ValueError, match="finite number"):
        assess_a10(report)


@pytest.mark.parametrize("bad", [None, [], {"metrics": []}, {"metrics": {"rps": None}}])
def test_calibration_rejects_malformed_report(bad: Any) -> None:
    with pytest.raises(ValueError):
        assess_a10(bad)


def test_calibration_marks_report_only_and_does_not_mutate() -> None:
    report = calibration_report()
    original = deepcopy(report)
    result = assess_a10(report)
    assert result["verdict"] == "GO_CANDIDATE_FOR_NEW_PROSPECTIVE_PROTOCOL"
    assert result["schema_version"] == "a10-promotion-gate/v2"
    assert result["economic_evidence"] is False
    assert result["provenance_verified"] is False
    assert result["capital_enabled"] is False
    assert report == original


def test_calibration_missing_home_guardrail_still_abstains() -> None:
    report = calibration_report()
    del report["metrics"]["log_loss_home_win"]
    assert assess_a10(report)["verdict"] == "NO_GO_ARCHIVE_A10"


def rows() -> list[dict[str, Any]]:
    return [{"event_id": str(i), "pnl": 0.2 if i % 2 else 0.1, "clv": 0.03} for i in range(8)]


@pytest.mark.parametrize("field", ["pnl", "clv"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), True, "0.2"])
def test_residual_rejects_invalid_values_before_any_statistics(field: str, bad: Any) -> None:
    sample = rows()
    sample[0][field] = bad
    with pytest.raises(ValueError, match="finite number"):
        evaluate_economic_gate(sample, dsr=0.99, minimum_sample=2, n_boot=20)


@pytest.mark.parametrize("bad", [True, " ", [], {}])
def test_residual_requires_an_event_identity(bad: Any) -> None:
    sample = rows()
    sample[0]["event_id"] = bad
    with pytest.raises(ValueError, match="event_id"):
        evaluate_economic_gate(sample, dsr=0.99, minimum_sample=2, n_boot=20)


@pytest.mark.parametrize(
    "argument,bad",
    [
        ("dsr", float("inf")),
        ("dsr", True),
        ("dsr", 1.01),
        ("minimum_psr", -0.01),
        ("minimum_dsr", float("nan")),
        ("minimum_sample", 0),
        ("minimum_sample", True),
        ("minimum_sample", 2.5),
        ("n_boot", 0),
        ("n_boot", True),
        ("n_boot", 2.5),
    ],
)
def test_residual_validates_configuration_even_below_sample_floor(argument: str, bad: Any) -> None:
    options: dict[str, Any] = {"dsr": 0.99, "minimum_sample": 2, "n_boot": 20}
    options[argument] = bad
    with pytest.raises(ValueError):
        evaluate_economic_gate([], **options)


def test_residual_does_not_promote_a_selected_complete_subset() -> None:
    sample = rows() + [{"event_id": "missing", "pnl": None, "clv": 0.03}]
    result = evaluate_economic_gate(sample, dsr=0.99, minimum_sample=2, n_boot=20)
    assert result["verdict"] == "PENDING_DATA"
    assert result["n_input"] == 9
    assert result["n"] == 8
    assert result["n_incomplete"] == 1
    assert result["capital_enabled"] is False


def test_residual_labels_unit_assumption_and_declared_dsr() -> None:
    sample = rows()
    original = deepcopy(sample)
    result = evaluate_economic_gate(sample, dsr=0.99, minimum_sample=2, n_boot=20)
    assert result["roi"] == pytest.approx(0.15)
    assert result["roi_scope"] == "mean_pnl_assuming_one_unit_staked_per_row"
    assert result["dsr_source"] == "caller_declared_unverified"
    assert result["economic_evidence"] is False
    assert result["capital_enabled"] is False
    assert sample == original


def test_residual_cannot_call_variable_stake_pnl_roi() -> None:
    sample = rows()
    sample[0]["stake"] = 2.0
    with pytest.raises(ValueError, match="unit stake"):
        evaluate_economic_gate(sample, dsr=0.99, minimum_sample=2, n_boot=20)
