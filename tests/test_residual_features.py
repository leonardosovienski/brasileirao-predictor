import pytest

from src.research.residual_features import build_residual_features, lineup_state_asof


def test_lineup_state_uses_latest_vintage_available_asof():
    rows = [
        {
            "source_event_id": "1",
            "team_id": "a",
            "player_id": "old",
            "role": "starter",
            "content_hash": "v1",
            "published_at": "2026-08-10T10:00:00+00:00",
        },
        {
            "source_event_id": "1",
            "team_id": "a",
            "player_id": "new",
            "role": "starter",
            "content_hash": "v2",
            "published_at": "2026-08-10T11:00:00+00:00",
        },
    ]
    assert lineup_state_asof(rows, event_id="1", asof="2026-08-10T10:30:00+00:00") == {"a": {"old"}}
    assert lineup_state_asof(rows, event_id="1", asof="2026-08-10T11:30:00+00:00") == {"a": {"new"}}


def test_residual_features_capture_dispersion_time_and_lineup_change():
    features = build_residual_features(
        book_probabilities=[0.45, 0.50, 0.55],
        captured_at="2026-08-10T10:00:00+00:00",
        kickoff_at="2026-08-11T10:00:00+00:00",
        current_starters={"a", "b"},
        expected_starters={"a", "c"},
        xg_form_delta=0.3,
        rest_days_delta=-2,
    )
    assert len(features) == 7
    assert features[0] > 0
    assert features[3] == pytest.approx(2 / 11)
    assert features[4] == pytest.approx(2 / 22)


def test_residual_features_reject_post_kickoff_observation():
    with pytest.raises(ValueError, match="before kickoff"):
        build_residual_features(
            book_probabilities=[0.5],
            captured_at="2026-08-11T10:00:00+00:00",
            kickoff_at="2026-08-11T09:00:00+00:00",
        )
