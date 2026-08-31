import json
from pathlib import Path

import numpy as np

from brasileirao_predictor.research.calibration_gate import assess_a10
from brasileirao_scripts.trial_draw_calibration_a10 import _losses, _moving_ci

ROOT = Path(__file__).resolve().parent.parent


def test_existing_a10_report_is_formally_no_go():
    report = json.loads((ROOT / "reports" / "trial_draw_calibration_a10_2024.json").read_text(encoding="utf-8"))
    gate = assess_a10(report)
    assert gate["verdict"] == "NO_GO_ARCHIVE_A10"
    assert gate["primary_improved"] is False
    assert gate["serving_changed"] is False


def test_gate_requires_primary_and_every_guardrail():
    metrics = {
        name: {"delta_treatment_minus_control": delta}
        for name, delta in {"rps": -0.1, "brier": -0.1, "log_loss": 0.01, "brier_draw": -0.1}.items()
    }
    assert assess_a10({"metrics": metrics})["verdict"] == "NO_GO_ARCHIVE_A10"


def test_gate_requires_material_rps_gain_and_home_win_guardrail():
    metrics = {
        name: {"delta_treatment_minus_control": delta}
        for name, delta in {
            "rps": -0.0021,
            "brier": -0.001,
            "log_loss": -0.001,
            "brier_draw": -0.001,
            "log_loss_home_win": 0.0,
        }.items()
    }
    gate = assess_a10({"metrics": metrics})
    assert gate["verdict"] == "GO_CANDIDATE_FOR_NEW_PROSPECTIVE_PROTOCOL"
    metrics["rps"]["delta_treatment_minus_control"] = -0.0019
    assert assess_a10({"metrics": metrics})["verdict"] == "NO_GO_ARCHIVE_A10"


def test_a10_producer_can_compute_home_win_guardrail() -> None:
    probabilities = np.array([[0.1, 0.2, 0.7], [0.6, 0.3, 0.1]])
    outcomes = np.array([2, 0])
    losses = _losses(probabilities, outcomes)
    home_losses = losses["log_loss"][outcomes == 2]
    assert len(home_losses) == 1
    assert len(_moving_ci(home_losses, n_boot=20)) == 2
