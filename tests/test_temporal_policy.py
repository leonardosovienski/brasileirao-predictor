import pytest

from brasileirao_predictor.temporal_policy import TemporalPolicy, assert_unique_teams


def test_groups_equal_utc_kickoffs_and_fingerprints_policy():
    rows = [
        {"kickoff_at": "2026-01-01T15:00:00-03:00", "home_team": "A", "away_team": "B"},
        {"kickoff_at": "2026-01-01T18:00:00Z", "home_team": "C", "away_team": "D"},
    ]
    policy = TemporalPolicy()
    groups = policy.group(rows)
    assert len(groups) == 1
    assert groups[0].precision == "kickoff"
    assert policy.fingerprint == TemporalPolicy().fingerprint
    assert policy.fingerprint != TemporalPolicy(fallback="reject").fingerprint


def test_date_fallback_is_conservative_and_reject_is_available():
    rows = [
        {"date": "2026-01-01", "home_team": "A", "away_team": "B"},
        {"date": "2026-01-01", "home_team": "C", "away_team": "D"},
    ]
    group = TemporalPolicy().group(rows)[0]
    assert group.precision == "date" and len(group.rows) == 2
    with pytest.raises(ValueError, match="kickoff_at missing"):
        TemporalPolicy(fallback="reject").group(rows)


def test_duplicate_team_in_same_group_fails_closed():
    rows = [
        {"date": "2026-01-01", "home_team": "A", "away_team": "B"},
        {"date": "2026-01-01", "home_team": "A", "away_team": "C"},
    ]
    with pytest.raises(ValueError, match="more than once"):
        assert_unique_teams(TemporalPolicy().group(rows)[0])


def test_missing_kickoff_collapses_known_kickoffs_on_the_same_utc_day():
    rows = [
        {"date": "2030-01-01", "home_team": "A", "away_team": "B"},
        {"kickoff_at": "2030-01-01T21:00:00Z", "home_team": "C", "away_team": "D"},
    ]
    groups = TemporalPolicy().group(rows)
    assert len(groups) == 1
    assert groups[0].precision == "date"
    assert len(groups[0].rows) == 2


def test_missing_kickoff_is_grouped_after_timezone_normalization():
    rows = [
        {"date": "2030-01-02", "home_team": "A", "away_team": "B"},
        {"kickoff_at": "2030-01-01T22:00:00-03:00", "home_team": "C", "away_team": "D"},
    ]
    assert len(TemporalPolicy().group(rows)) == 1
