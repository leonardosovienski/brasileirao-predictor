import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from brasileirao_predictor.prediction_protocol import assess_prediction_readiness

NOW = datetime(2026, 8, 22, 20, tzinfo=UTC)


def candidate(**overrides):
    row = {
        "prediction_kind": "PRE_MATCH",
        "event_id": "123",
        "home": "A",
        "away": "B",
        "predicted_at": NOW,
        "kickoff_at": NOW + timedelta(hours=1),
        "model_name": "serving",
        "model_version": "1",
        "pipeline_fingerprint": "abc",
        "historical_data_cutoff": NOW,
        "latest_training_match_kickoff": NOW - timedelta(days=1),
        "latest_training_result_available_at": NOW - timedelta(hours=20),
        "current_season_matches_included": 225,
        "current_season_matches_available": 225,
        "lineup_captured_at": NOW - timedelta(minutes=5),
        "lineup_confirmed": False,
        "capital_enabled": False,
    }
    row.update(overrides)
    return row


def test_pre_match_ready_with_explicit_probable_lineup():
    report = assess_prediction_readiness(candidate())
    assert report.ready
    assert report.designation == "OFFICIAL_PRE_MATCH"
    assert [warning.code for warning in report.warnings] == ["MARKET_UNAVAILABLE"]


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"predicted_at": NOW + timedelta(hours=2)}, "POST_KICKOFF_PRE_MATCH"),
        ({"historical_data_cutoff": NOW + timedelta(seconds=1)}, "FUTURE_DATA_CUTOFF"),
        ({"latest_training_match_kickoff": NOW}, "TRAINING_MATCH_NOT_PRIOR"),
        ({"latest_training_result_available_at": NOW + timedelta(seconds=1)}, "RESULT_NOT_AVAILABLE"),
        ({"current_season_matches_included": 224}, "INCOMPLETE_CURRENT_HISTORY"),
        ({"lineup_captured_at": NOW + timedelta(seconds=1)}, "FUTURE_LINEUP"),
        ({"odds_captured_at": NOW + timedelta(seconds=1)}, "FUTURE_ODDS"),
        ({"lineup_confirmed": None}, "LINEUP_STATUS_UNKNOWN"),
        ({"capital_enabled": True}, "CAPITAL_BLOCKED"),
    ],
)
def test_pre_match_fails_closed(changes, code):
    report = assess_prediction_readiness(candidate(**changes))
    assert not report.ready
    assert report.designation == "BLOCKED"
    assert code in {finding.code for finding in report.blockers}


def test_live_requires_state_and_rejects_unvalidated_features():
    report = assess_prediction_readiness(
        candidate(
            prediction_kind="LIVE",
            kickoff_at=NOW - timedelta(minutes=10),
            lineup_confirmed=True,
            unvalidated_live_features_injected=True,
        )
    )
    codes = {finding.code for finding in report.blockers}
    assert {"LIVE_STATE_MISSING", "UNVALIDATED_LIVE_FEATURES"} <= codes


def test_live_ready_with_point_in_time_state():
    report = assess_prediction_readiness(
        candidate(
            prediction_kind="LIVE",
            kickoff_at=NOW - timedelta(minutes=10),
            live_observed_at=NOW - timedelta(seconds=5),
            observed_minute=9,
            current_score=(0, 0),
            lineup_confirmed=True,
        )
    )
    assert report.ready
    assert report.designation == "OFFICIAL_LIVE"


def test_retrospective_is_never_designated_official():
    report = assess_prediction_readiness(candidate(prediction_kind="RETROSPECTIVE_SIMULATION"))
    assert report.ready
    assert report.designation == "RETROSPECTIVE_ONLY"
    assert report.warnings[0].code == "NOT_PROSPECTIVE"


def test_naive_datetime_is_rejected():
    with pytest.raises(ValidationError, match="predicted_at must be timezone-aware"):
        assess_prediction_readiness(candidate(predicted_at=datetime(2026, 8, 22, 20)))


@pytest.mark.parametrize(("changes", "expected_code"), [({}, 0), ({"capital_enabled": True}, 2)])
def test_readiness_cli_exit_code(tmp_path: Path, changes, expected_code):
    input_path = tmp_path / "readiness.json"
    payload = candidate(**changes)
    input_path.write_text(json.dumps(payload, default=lambda value: value.isoformat()), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-m", "brasileirao_scripts.check_prediction_readiness", str(input_path)],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(completed.stdout)
    assert completed.returncode == expected_code
    assert report["ready"] is (expected_code == 0)
