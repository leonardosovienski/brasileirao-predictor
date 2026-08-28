import json
from pathlib import Path

from src.research.calibration_gate import assess_a10

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
