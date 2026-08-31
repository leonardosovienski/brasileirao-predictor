from datetime import UTC, datetime, timedelta

import pytest

from brasileirao_predictor.research.contextual_ensemble import evaluate_contextual_ensemble


def _rows(count: int) -> list[dict]:
    start = datetime(2020, 1, 1, 18, tzinfo=UTC)
    return [
        {
            "event_id": str(index),
            "kickoff_at": (start + timedelta(days=index // 5)).isoformat(),
            "context_available_at": (start + timedelta(days=index // 5, hours=-24)).isoformat(),
            "baseline_probs": [0.3, 0.3, 0.4],
            "outcome": index % 3,
            "context": {"rest_days_delta": float(index % 4 - 2), "away_travel_km": float(index * 10)},
        }
        for index in range(count)
    ]


def test_contextual_trial_is_expanding_and_never_changes_serving() -> None:
    report = evaluate_contextual_ensemble(_rows(80), minimum_train=30, minimum_test=20)
    assert report["status"] == "PASS"
    assert report["validation"] == "expanding_window_by_kickoff_date"
    assert report["serving_changed"] is False


def test_contextual_trial_blocks_insufficient_data() -> None:
    report = evaluate_contextual_ensemble(_rows(10), minimum_train=30, minimum_test=20)
    assert report["status"] == "BLOCKED_DATA"


def test_contextual_trial_rejects_post_kickoff_evidence() -> None:
    rows = _rows(80)
    rows[0]["context_available_at"] = rows[0]["kickoff_at"]
    with pytest.raises(ValueError, match="strictly before"):
        evaluate_contextual_ensemble(rows, minimum_train=30, minimum_test=20)
