"""Synthetic chronology and population tests for the new, separate recipe."""
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from brasileirao_predictor.research.price_strength.dynamic_xg import DynamicXGConfig
from evaluate_correction import feature_history, fit_stage, outcome_indices


def fixture(i, kickoff, *, xg=(1.5, 0.9), goals=(1, 0)):
    return {'event_id': i, 'home': 'A', 'away': 'B', 'kickoff': kickoff.isoformat(),
            'result': {'home_goals': goals[0], 'away_goals': goals[1], 'home_xg': xg[0], 'away_xg': xg[1]},
            'odds': {'1x2': [1.9, 3.5, 4], 'ou25': [1.9, 1.9], 'btts': [1.9, 1.9]}}


def history():
    start = datetime(2023, 12, 1, tzinfo=UTC)
    return [fixture(i+1, start + timedelta(days=i*7)) for i in range(12)]


CONFIG = DynamicXGConfig(min_calibration_matches=1)


def test_zero_quarantine_uses_no_score_or_team_identity_and_does_not_mutate():
    source = history()
    for row in source[:2]:
        row['result']['home_xg'] = row['result']['away_xg'] = 0
    source[0]['result']['home_goals'] = 0
    source[1]['result']['home_goals'] = 9
    before = deepcopy(source)
    kept, report = feature_history(source)
    assert source == before
    assert [r['event_id'] for r in kept] == list(range(3, 13))
    assert report['excluded_features'] == [
        {'event_id': '1', 'category': 'ZERO_PAIR_UNATTESTED'},
        {'event_id': '2', 'category': 'ZERO_PAIR_UNATTESTED'},
    ]


def test_future_goals_and_odds_do_not_enter_fit():
    source = history()
    future = fixture(99, datetime(2025, 4, 1, tzinfo=UTC))
    a = fit_stage([*source, future], CONFIG)
    future['result']['home_goals'] = 99
    future['result']['away_goals'] = 88
    future['odds'] = {'future': 'not read'}
    b = fit_stage([*source, future], CONFIG)
    assert a[2:] == b[2:]


def test_last_target_own_xg_does_not_decide_its_calibration_label_eligibility():
    source = history()
    fitted = fit_stage(source, CONFIG)
    source[-1]['result']['home_xg'] = source[-1]['result']['away_xg'] = 0
    changed = fit_stage(source, CONFIG)
    assert changed[2:] == fitted[2:]
    assert '12' in changed[4]['target_match_ids']


def test_label_buffer_boundary_is_strict():
    source = history()
    boundary = fixture(99, datetime(2024, 12, 30, tzinfo=UTC))
    a = fit_stage(source, CONFIG)
    b = fit_stage([*source, boundary], CONFIG)
    assert a[2:] == b[2:]
    assert '99' not in b[4]['target_match_ids']


def test_duplicate_ids_and_invalid_numeric_xg_fail():
    source = history()
    with pytest.raises(ValueError, match='duplicate'):
        feature_history([*source, source[0]])
    source[0]['result']['home_xg'] = -1
    with pytest.raises(ValueError, match='invalid numeric'):
        feature_history(source)


def test_label_directions_include_draw_and_binary_complements():
    assert outcome_indices({'home_goals': 1, 'away_goals': 1}) == {'1x2': 1, 'ou25': 1, 'btts': 0}
    assert outcome_indices({'home_goals': 0, 'away_goals': 3}) == {'1x2': 2, 'ou25': 0, 'btts': 1}
    with pytest.raises(ValueError):
        outcome_indices({'home_goals': True, 'away_goals': 0})
