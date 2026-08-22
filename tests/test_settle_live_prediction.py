from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from scripts.settle_live_prediction import append_settlement, build_settlement, load_prediction


def prediction():
    return {
        "prediction_id": "LIVE-2026-08-22-001",
        "prediction": {"p_home": 0.57, "p_draw": 0.25, "p_away": 0.18},
    }


def event(status="finished"):
    return {
        "id": 15235430,
        "status": {"type": status, "description": "Ended"},
        "homeScore": {"current": 0},
        "awayScore": {"current": 1},
    }


def test_settlement_is_separate_linked_append_only_and_diagnostic(tmp_path):
    row = build_settlement(prediction(), event(), datetime(2026, 8, 22, 22, tzinfo=UTC))
    assert row["prediction_id"] == "LIVE-2026-08-22-001"
    assert row["final_score"] == [0, 1]
    assert row["actual_1x2"] == "away"
    assert row["diagnostic_hit"] is False
    assert row["capital_enabled"] is False
    path = tmp_path / "settlements.jsonl"
    assert append_settlement(path, row) is True
    assert append_settlement(path, row) is False
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_settlement_refuses_unfinished_event_and_naive_clock():
    with pytest.raises(ValueError, match="not finished"):
        build_settlement(prediction(), event("inprogress"), datetime.now(UTC))
    with pytest.raises(ValueError, match="timezone-aware"):
        build_settlement(prediction(), event(), datetime(2026, 8, 22))


def test_load_prediction_requires_exactly_one_original(tmp_path):
    path = tmp_path / "live.jsonl"
    path.write_text(json.dumps(prediction()) + "\n", encoding="utf-8")
    assert load_prediction(path, "LIVE-2026-08-22-001")["prediction_id"] == "LIVE-2026-08-22-001"
    with pytest.raises(ValueError, match="found 0"):
        load_prediction(path, "missing")
