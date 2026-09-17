from copy import deepcopy

import numpy as np
import pytest
from predictor_core.measurement.metrics import brier, log_loss, rps

from brasileirao_scripts import prospective_protocol_v2 as p


def history():
    return [{'event_id': i + 1, 'home_goals': 2, 'away_goals': 1,
             'final_at': '2027-01-01T20:00:00Z', 'available_at': '2027-01-01T21:00:00Z'}
            for i in range(200)]


def prediction():
    return {'p_home': .5, 'p_draw': .3, 'p_away': .2, 'p_over_2_5': .6}


def record(event_id=1):
    state = {'model_state': {'params': [1, 2, 3, 4]}, 'model_source': 'synthetic fixture',
             'configuration': {'fixture': True}, 'training_cutoff': '2027-01-01T22:00:00Z',
             'state_at': '2027-01-01T23:00:00Z'}
    return p.forecast_record(event_id=event_id, trial=p.FAMILY[1],
                             kickoff_at='2027-01-04T18:00:00Z', predicted_at='2027-01-04T00:00:00Z',
                             arms={arm: prediction() for arm in ('control', 'treatment')},
                             escrow={arm: deepcopy(state) for arm in ('control', 'treatment')})


def test_baseline_reference_values_and_permutation():
    baseline = p.climatology_snapshot(history(), kickoff_at='2027-01-04T18:00:00Z')
    assert baseline['p_home'] == 201 / 203
    assert baseline['p_over_2_5'] == 201 / 202
    assert baseline['cutoff'] == '2027-01-03T00:00:00+00:00'
    assert baseline == p.climatology_snapshot(history()[::-1], kickoff_at='2027-01-04T23:00:00Z')


@pytest.mark.parametrize('field', ['final_at', 'available_at'])
def test_cutoff_excludes_same_instant_and_future(field):
    late = dict(history()[0], event_id=201, home_goals=0, away_goals=0)
    late[field] = '2027-01-03T00:00:00Z'
    if field == 'final_at':
        late['available_at'] = late[field]
    assert p.climatology_snapshot(history() + [late], kickoff_at='2027-01-04T18:00:00Z')['n_prior'] == 200


def test_duplicate_history_and_insufficient_history_fail():
    for rows in (history() + [history()[0]], history()[:199]):
        with pytest.raises(ValueError):
            p.climatology_snapshot(rows, kickoff_at='2027-01-04T18:00:00Z')


def test_equivalent_timezone_selects_same_block():
    assert p.climatology_snapshot(history(), kickoff_at='2027-01-04T23:30:00-03:00') == (
        p.climatology_snapshot(history(), kickoff_at='2027-01-05T02:30:00Z'))


@pytest.mark.parametrize('value', [None, True, float('nan'), float('inf'), -0.01, 1.01, '0.5'])
def test_invalid_ou_probability_rejected(value):
    row = prediction()
    row['p_over_2_5'] = value
    with pytest.raises(ValueError):
        p.losses(row, 1, 0)


@pytest.mark.parametrize('scores', [(0, 0), (1, 0), (0, 1), (2, 2), (5, 1)])
def test_scoring_agrees_with_independent_core(scores):
    row = prediction()
    actual = 2 if scores[0] > scores[1] else 1 if scores[0] == scores[1] else 0
    values = [row['p_away'], row['p_draw'], row['p_home']]
    losses = p.losses(row, *scores)
    assert losses['rps'] == pytest.approx(rps([values], [actual]))
    assert losses['log_loss'] == pytest.approx(log_loss([values], [actual]))
    assert losses['brier_1x2'] == pytest.approx(brier([values], [actual]))
    assert losses['brier_ou25'] == pytest.approx(2 * (.6 - int(sum(scores) >= 3)) ** 2)


@pytest.mark.parametrize('scores', [(None, 0), (0, None), (-1, 0), (True, 0), (1.5, 1)])
def test_partial_or_invalid_scores_rejected(scores):
    with pytest.raises(ValueError):
        p.losses(prediction(), *scores)


def test_one_x_two_does_not_identify_over_probability():
    # Two valid point-mass score grids: 1-0 versus 3-0. Same 1X2, opposite OU.
    a = {'p_home': 1., 'p_draw': 0., 'p_away': 0., 'p_over_2_5': 0.}
    b = dict(a, p_over_2_5=1.)
    assert p.losses(a, 1, 0)['rps'] == p.losses(b, 1, 0)['rps'] == 0
    assert p.losses(a, 1, 0)['brier_ou25'] != p.losses(b, 1, 0)['brier_ou25']


def test_escrow_is_copied_and_hash_covers_state():
    row = record()
    before = row['record_sha256']
    row['escrow']['control']['model_state']['params'][0] += 1
    assert p.content_hash({k: v for k, v in row.items() if k != 'record_sha256'}) != before


def test_legacy_and_postkickoff_rejected():
    row = record()
    kwargs = {k: row[k] for k in ('event_id', 'trial', 'kickoff_at', 'predicted_at', 'arms', 'escrow')}
    for change in ({'trial': 'h15-refit10-vs-100-serving-v2-prospectivo'},
                   {'predicted_at': row['kickoff_at']}, {'predicted_at': '2027-01-02T00:00:00Z'}):
        with pytest.raises(ValueError):
            p.forecast_record(**(kwargs | change))
    kwargs['escrow']['control']['state_at'] = '2027-01-04T00:01:00Z'
    with pytest.raises(ValueError):
        p.forecast_record(**kwargs)


def test_h14_baseline_escrow_replays_and_rejects_tampering():
    row = record()
    baseline = p.climatology_snapshot(history(), kickoff_at=row['kickoff_at'])
    kwargs = {k: row[k] for k in ('event_id', 'trial', 'kickoff_at', 'predicted_at', 'arms', 'escrow')}
    kwargs['trial'] = p.FAMILY[0]
    kwargs['arms']['control'] = baseline
    kwargs['escrow']['control']['model_state'] = {'history': history(), 'history_sha256': baseline['history_sha256']}
    assert p.forecast_record(**kwargs)['trial'] == p.FAMILY[0]
    kwargs['arms']['control']['p_over_2_5'] = .1
    with pytest.raises(ValueError, match='mismatch'):
        p.forecast_record(**kwargs)


@pytest.fixture
def sample():
    rows = [record(i + 1) for i in range(900)]
    for row in rows:
        row['receipt'] = {'record_sha256': row['record_sha256'], 'received_at': row['predicted_at']}
    actual = [{'event_id': i + 1, 'home_goals': 1, 'away_goals': 0,
               'final_at': '2027-01-04T20:00:00Z', 'available_at': '2027-01-04T21:00:00Z'}
              for i in range(900)]
    return rows, actual


def test_paired_sample_sorted_no_silent_drop(sample):
    rows, actual = sample
    result = p.paired_sample(rows[::-1], actual[::-1], trial=p.FAMILY[1])
    assert result['event_ids'] == list(range(1, 901))
    assert all(values == [0.] * 900 for values in result['gains'].values())
    with pytest.raises(ValueError, match='No silent'):
        p.paired_sample(rows, actual[:-1], trial=p.FAMILY[1])


@pytest.mark.parametrize('fault', ['forecast_duplicate', 'outcome_duplicate', 'late_receipt', 'hash', 'legacy',
                                  'early_final', 'early_available'])
def test_bad_sample_never_reaches_losses(sample, fault, monkeypatch):
    rows, actual = sample
    if fault == 'forecast_duplicate':
        rows[-1] = rows[0]
    elif fault == 'outcome_duplicate':
        actual[-1] = actual[0]
    elif fault == 'late_receipt':
        rows[0]['receipt']['received_at'] = rows[0]['kickoff_at']
    elif fault == 'hash':
        rows[0]['arms']['control']['p_over_2_5'] = .1
    elif fault == 'early_final':
        actual[-1]['final_at'] = rows[0]['kickoff_at']
    elif fault == 'early_available':
        actual[-1]['available_at'] = rows[0]['kickoff_at']
    else:
        rows[0]['schema'] = 'old'
    def forbidden(*args):
        pytest.fail('Invalid sample must be rejected before scoring')
    monkeypatch.setattr(p, 'losses', forbidden)
    with pytest.raises(ValueError):
        p.paired_sample(rows, actual, trial=p.FAMILY[1])


@pytest.mark.parametrize('value', [None, True, float('nan'), float('inf'), '1', 1e308, -1e308])
def test_bootstrap_invalid_values(value):
    with pytest.raises(ValueError):
        p.paired_inference([value] + [0.] * 899)


def test_degenerate_and_small_sample_do_not_approve():
    with pytest.raises(ValueError):
        p.paired_inference([1.] * 899)
    for value in (-1., 0., 1.):
        assert p.paired_inference([value] * 900)['p_one_sided'] == 1


def test_randomized_scores_agree_with_core():
    rng = np.random.default_rng(119)
    for _ in range(200):
        values = rng.dirichlet([1, 1, 1]).tolist()
        row = dict(zip(('p_away', 'p_draw', 'p_home'), values, strict=True))
        row['p_over_2_5'] = float(rng.random())
        home, away = (int(v) for v in rng.integers(0, 8, size=2))
        actual = 2 if home > away else 1 if home == away else 0
        result = p.losses(row, home, away)
        assert result['rps'] == pytest.approx(rps([values], [actual]))
        assert result['brier_1x2'] == pytest.approx(brier([values], [actual]))
        assert result['log_loss'] == pytest.approx(log_loss([values], [actual]))


def test_direction_reproducibility_and_seed_is_local():
    x = (np.random.default_rng(19).normal(size=900) + .5).tolist()
    np.random.seed(123)
    before = np.random.get_state()
    result = p.paired_inference(x)
    after = np.random.get_state()
    assert np.array_equal(before[1], after[1])
    assert result == p.paired_inference(x)
    assert result['p_one_sided'] <= .025
    assert result['ci95'][0] > 0
    assert p.paired_inference([-v for v in x])['p_one_sided'] > .95


def test_family_preflight_before_any_inference(monkeypatch):
    def forbidden(*args):
        pytest.fail('Incomplete family must not be measured')
    monkeypatch.setattr(p, 'paired_inference', forbidden)
    for data in ({}, {p.FAMILY[0]: {}}, {trial: {m: [0.] * 899 for m in p.METRICS} for trial in p.FAMILY}):
        with pytest.raises(ValueError):
            p.family_decision(data)


def test_family_conjunction_does_not_approve_uncertain_guardrail(monkeypatch):
    def inference(values):
        uncertain = values[0] < 0
        return {'n': 900, 'mean_gain': .1, 'ci95': [-.1 if uncertain else .01, .2],
                'p_one_sided': .01, 'degenerate': False}
    monkeypatch.setattr(p, 'paired_inference', inference)
    data = {trial: {m: [.1] * 900 for m in p.METRICS} for trial in p.FAMILY}
    result = p.family_decision(data)
    assert set(result['decisions'].values()) == {'CRITERIA_MET'}
    assert result['scientific_claim_authorized'] is False
    data[p.FAMILY[0]]['brier_ou25'][0] = -.1
    assert p.family_decision(data)['decisions'][p.FAMILY[0]] == 'INCONCLUSIVE_OR_FAILED'


def test_joint_enrollment_gate_precedes_any_scoring(sample, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Incomplete enrollment reached scoring')
    monkeypatch.setattr(p, 'paired_sample', forbidden)
    rows, actual = sample
    data = {member: {'records': deepcopy(rows), 'outcomes': deepcopy(actual)} for member in p.FAMILY}
    data[p.FAMILY[0]]['records'][0]['event_id'] = 9001
    with pytest.raises(ValueError, match='identical frozen'):
        p.measure_supplied_family(data)
    data[p.FAMILY[0]]['records'].pop()
    with pytest.raises(ValueError, match='Exactly 900'):
        p.measure_supplied_family(data)
