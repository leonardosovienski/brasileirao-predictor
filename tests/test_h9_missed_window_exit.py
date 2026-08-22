from __future__ import annotations

import sys

from scripts import report_h9_missed_windows as missed


def test_missed_window_alert_is_not_reported_as_task_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        missed,
        "report",
        lambda **_: {"missed_count": 2, "at_risk_count": 1, "missed": [], "at_risk": []},
    )
    monkeypatch.setattr(sys, "argv", ["report_h9_missed_windows.py"])

    assert missed.main() == 0
    assert "H9_MISSED_WINDOW_ALERT missed=2 at_risk=1" in capsys.readouterr().err
