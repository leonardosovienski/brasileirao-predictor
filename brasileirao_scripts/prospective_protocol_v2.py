"""Explicit successor protocol components; no IO, activation or legacy evaluation.

This version resolves previously unspecified choices without retroactively
changing the August 2026 trials. Pure functions accept supplied data only.
"""
from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np

from brasileirao_scripts.prospective_metrics import brier_ou25, holm_family

FAMILY = ('h14-successor-v2', 'h15-successor-v2')
METRICS = ('rps', 'log_loss', 'brier_1x2', 'brier_ou25')
PROTOCOL = {
    'id': 'br-prospective-repair-v2-20260915',
    'family': list(FAMILY),
    'status': 'SPECIFIED_NOT_ACTIVATED',
    'legacy_cohorts_eligible': False,
    'reconstructions_eligible': False,
    'capital_enabled': False,
    'minimum_sample_per_member': 900,
    'intermediate_evaluations': False,
    'evaluation_order': ['kickoff_at_utc', 'event_id'],
    'cohort': 'same first 900 eligible event IDs in both members; freeze enrollment before outcome access',
    'prediction_window_hours': 24,
    'model': {'algorithm': 'nbdc-normalized-elo-horizon-v2', 'ensemble_xg_enabled': False,
              'h14_retrain_games': 100, 'elo_policy': 'frozen with each refit state',
              'configuration': 'freeze exact relevant configuration at separate activation',
              'fit_inputs': 'finalized and received before training cutoff; no future timestamps'},
    'h14_baseline': {
        'one_x_two': 'Dirichlet(1,1,1)',
        'over_2_5': 'Beta(1,1); (over_count + 1)/(n + 2)',
        'minimum_history': 200,
        'date_block': 'UTC fixture date',
        'cutoff': '00:00 UTC on the preceding calendar date',
        'eligibility': 'final_at and available_at strictly before cutoff',
        'late_arrivals': 'not included retrospectively; same frozen snapshot per block',
    },
    'h15_refit_games': {'control': 100, 'treatment': 10},
    'metrics': list(METRICS),
    'one_x_two_order': ['away', 'draw', 'home'],
    'rps': 'sum of two squared cumulative errors / 2',
    'log_loss': 'natural log; observed-class probability floor 1e-12',
    'brier_1x2': 'sum over three classes',
    'brier_ou25': '2 * (p_over - I(total_goals >= 3))**2',
    'gain': 'control_loss minus treatment_loss',
    'bootstrap': {
        'scheme': 'moving non-circular overlapping blocks',
        'block_length': 21, 'n_boot': 10000, 'seed': 42,
        'rng': 'NumPy PCG64',
        'sampling': 'ceil(n/21) independent block starts; concatenate then truncate to n',
        'ci': 'percentile 2.5/97.5; NumPy linear quantile',
        'p_null': 'one-sided H0 mean_gain <= 0; centered resampled means',
        'p_formula': '(1 + count(bootstrap_mean - observed_mean >= observed_mean))/(10000 + 1)',
        'ties': 'included in upper tail',
        'degenerate': 'constant gains produce inconclusive p=1, never approval',
        'validity': 'approximate; requires suitable weak dependence and stationarity',
    },
    'decision': {
        'primary': 'RPS lower CI > 0 and Holm-adjusted one-sided p <= 0.05',
        'family_alpha': 0.05,
        'family_complete': True,
        'guardrails': 'each lower CI >= 0; uncertain interval is inconclusive',
        'noninferiority_margin': 0.0,
        'interpretation': 'engineering decision only until prospective provenance is admitted',
    },
    'required_escrow': ['full_model_state', 'model_source', 'relevant_configuration',
                        'full_precision_1x2_and_ou25', 'training_cutoff', 'prediction_receipt'],
    'activation': 'separate immutable registration and new empty ledgers required; no scheduler installed',
}


def specification() -> dict:
    return deepcopy(PROTOCOL)


def content_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def _time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError('Timestamp must be text with timezone')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Timezone required')
    return parsed.astimezone(UTC)


def _identifier(value: Any) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError('Positive integer event ID required')
    return value


def _number(value: Any, *, probability: bool = False) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Finite numeric value required')
    if probability and not 0 <= value <= 1:
        raise ValueError('Probability outside [0,1]')
    return float(value)


def _score(row: dict) -> tuple[int, int]:
    values = (row['home_goals'], row['away_goals'])
    if any(type(x) is not int or x < 0 for x in values):
        raise ValueError('Two complete nonnegative integer goal counts required')
    return values


def validate_probabilities(prediction: dict) -> None:
    values = [_number(prediction[k], probability=True) for k in ('p_away', 'p_draw', 'p_home')]
    if not math.isclose(sum(values), 1.0, rel_tol=0, abs_tol=1e-9):
        raise ValueError('Full precision 1X2 probabilities must sum to one')
    _number(prediction['p_over_2_5'], probability=True)


def climatology_snapshot(history: list[dict], *, kickoff_at: str) -> dict:
    """Only finalized and received observations preceding the frozen date block."""
    kickoff = _time(kickoff_at)
    cutoff = kickoff.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    seen, admitted = set(), []
    counts, overs = [1, 1, 1], 1
    for row in history:
        event_id = _identifier(row['event_id'])
        if event_id in seen:
            raise ValueError('Duplicate history event')
        seen.add(event_id)
        final, available = _time(row['final_at']), _time(row['available_at'])
        if available < final:
            raise ValueError('Result cannot be available before finalization')
        if final >= cutoff or available >= cutoff:
            continue
        home, away = _score(row)
        counts[2 if home > away else 1 if home == away else 0] += 1
        overs += int(home + away >= 3)
        admitted.append(row)
    if len(admitted) < PROTOCOL['h14_baseline']['minimum_history']:
        raise ValueError('At least 200 eligible historical matches required')
    admitted.sort(key=lambda r: r['event_id'])
    return {'p_away': counts[0] / sum(counts), 'p_draw': counts[1] / sum(counts),
            'p_home': counts[2] / sum(counts), 'p_over_2_5': overs / (len(admitted) + 2),
            'n_prior': len(admitted), 'block_date': kickoff.date().isoformat(),
            'cutoff': cutoff.isoformat(), 'history_sha256': content_hash(admitted)}


def forecast_record(*, event_id: int, trial: str, kickoff_at: str, predicted_at: str,
                    arms: dict, escrow: dict) -> dict:
    """Build a complete future record, including enough material for replay.

    Caller must persist this and a trusted receipt before kickoff. Hashes alone
    do not prove a historical timestamp, therefore no scientific admission here.
    """
    _identifier(event_id)
    if trial not in FAMILY or set(arms) != {'control', 'treatment'} or set(escrow) != set(arms):
        raise ValueError('Successor trial and both arms required')
    kickoff, predicted = _time(kickoff_at), _time(predicted_at)
    if not kickoff - timedelta(hours=24) <= predicted < kickoff:
        raise ValueError('Prediction must be within 24 hours strictly before kickoff')
    for arm, prediction in arms.items():
        validate_probabilities(prediction)
        state = escrow[arm]
        for key in ('model_state', 'model_source', 'configuration'):
            if not state.get(key):
                raise ValueError('Replay escrow is incomplete')
        if not isinstance(state['model_source'], str):
            raise ValueError('Model source text required, not only a hash')
        if not _time(state['training_cutoff']) <= _time(state['state_at']) <= predicted:
            raise ValueError('Future or inconsistent model state')
        if trial == FAMILY[0] and arm == 'control':
            expected = kickoff.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            if _time(prediction['cutoff']) != expected or prediction['block_date'] != kickoff.date().isoformat():
                raise ValueError('Wrong climatology date block')
            if type(prediction['n_prior']) is not int or prediction['n_prior'] < 200:
                raise ValueError('Insufficient climatology history')
            history = state['model_state'].get('history')
            if not isinstance(history, list):
                raise ValueError('Baseline history must be escrowed for replay')
            replay = climatology_snapshot(history, kickoff_at=kickoff_at)
            if replay != prediction or state['model_state'].get('history_sha256') != prediction['history_sha256']:
                raise ValueError('Baseline/history escrow mismatch')
    record = {'schema': PROTOCOL['id'], 'protocol_sha256': content_hash(PROTOCOL), 'trial': trial,
              'event_id': event_id, 'kickoff_at': kickoff.isoformat(), 'predicted_at': predicted.isoformat(),
              'classification': 'FUTURE_FORECAST_PENDING_TRUSTED_RECEIPT',
              'arms': deepcopy(arms), 'escrow': deepcopy(escrow),
              'escrow_sha256': content_hash(escrow), 'scientific_claim_authorized': False}
    record['record_sha256'] = content_hash(record)
    return record


def paired_sample(records: list[dict], outcomes: list[dict], *, trial: str) -> dict:
    """Validate an explicitly supplied, complete sample before calculating losses.

    Receipt consistency is checked; authenticity/registration is an external gate.
    No database, file or historical cohort is loaded by this module.
    """
    if trial not in FAMILY or len(records) < 900:
        raise ValueError('Successor trial and at least 900 records required')
    by_id = {}
    for row in records:
        event_id = _identifier(row['event_id'])
        if event_id in by_id:
            raise ValueError('Duplicate forecast event')
        if row['schema'] != PROTOCOL['id'] or row['trial'] != trial:
            raise ValueError('Legacy or mixed protocol records prohibited')
        unsigned = {key: value for key, value in row.items() if key not in ('record_sha256', 'receipt')}
        if content_hash(unsigned) != row['record_sha256']:
            raise ValueError('Forecast hash mismatch')
        rebuilt = forecast_record(event_id=event_id, trial=trial, kickoff_at=row['kickoff_at'],
                                  predicted_at=row['predicted_at'], arms=row['arms'], escrow=row['escrow'])
        if rebuilt['record_sha256'] != row['record_sha256']:
            raise ValueError('Unsupported record fields or protocol hash')
        receipt = row['receipt']
        if (receipt['record_sha256'] != row['record_sha256']
                or not _time(row['predicted_at']) <= _time(receipt['received_at']) < _time(row['kickoff_at'])):
            raise ValueError('Missing or late prediction receipt')
        by_id[event_id] = row
    result_by_id = {}
    for row in outcomes:
        event_id = _identifier(row['event_id'])
        if event_id in result_by_id:
            raise ValueError('Duplicate outcome event')
        _score(row)
        result_by_id[event_id] = row
    if set(result_by_id) != set(by_id):
        raise ValueError('No silent dropping of missing/extra outcomes')
    for event_id, actual in result_by_id.items():
        if not (_time(by_id[event_id]['kickoff_at']) < _time(actual['final_at'])
                <= _time(actual['available_at'])):
            raise ValueError('Outcome must be final after kickoff and received after finalization')
    gains = {metric: [] for metric in METRICS}
    ordered = sorted(records, key=lambda row: (_time(row['kickoff_at']), row['event_id']))
    for row in ordered:
        actual = result_by_id[row['event_id']]
        control = losses(row['arms']['control'], actual['home_goals'], actual['away_goals'])
        treatment = losses(row['arms']['treatment'], actual['home_goals'], actual['away_goals'])
        for metric in METRICS:
            gains[metric].append(control[metric] - treatment[metric])
    return {'event_ids': [row['event_id'] for row in ordered], 'gains': gains,
            'scientific_claim_authorized': False}


def losses(prediction: dict, home_goals: int, away_goals: int) -> dict:
    validate_probabilities(prediction)
    home, away = _score({'home_goals': home_goals, 'away_goals': away_goals})
    actual = 2 if home > away else 1 if home == away else 0
    p = [prediction['p_away'], prediction['p_draw'], prediction['p_home']]
    return {'rps': sum((sum(p[:i + 1]) - int(actual <= i)) ** 2 for i in range(2)) / 2,
            'log_loss': -math.log(max(p[actual], 1e-12)),
            'brier_1x2': sum((value - int(actual == i)) ** 2 for i, value in enumerate(p)),
            'brier_ou25': brier_ou25(prediction['p_over_2_5'], home, away)}


def paired_inference(gains: list[float]) -> dict:
    """Fixed, one-sided centered moving-block bootstrap, future protocol only."""
    if len(gains) < 900:
        raise ValueError('Minimum sample is 900; no interim inference')
    x = np.asarray([_number(value) for value in gains], dtype=np.float64)
    if np.max(np.abs(x)) > -math.log(1e-12):
        raise ValueError('Gain exceeds the largest possible supported loss difference')
    observed = float(x.mean())
    if not math.isfinite(observed):
        raise ValueError('Numeric overflow')
    if np.ptp(x) == 0:
        return {'n': len(x), 'mean_gain': observed, 'ci95': [observed, observed],
                'p_one_sided': 1.0, 'degenerate': True}
    bootstrap = PROTOCOL['bootstrap']
    length, repetitions = bootstrap['block_length'], bootstrap['n_boot']
    rng = np.random.Generator(np.random.PCG64(bootstrap['seed']))
    means = np.empty(repetitions)
    offsets = np.arange(length)
    for index in range(repetitions):
        starts = rng.integers(0, len(x) - length + 1, size=math.ceil(len(x) / length))
        sample = x[(starts[:, None] + offsets).ravel()[:len(x)]]
        means[index] = sample.mean()
    low, high = np.quantile(means, [.025, .975], method='linear')
    p_value = (1 + np.count_nonzero(means - observed >= observed)) / (repetitions + 1)
    return {'n': len(x), 'mean_gain': observed, 'ci95': [float(low), float(high)],
            'p_one_sided': float(p_value), 'degenerate': False}


def family_decision(gains_by_trial: dict[str, dict[str, list[float]]]) -> dict:
    if set(gains_by_trial) != set(FAMILY):
        raise ValueError('Both predeclared family members required')
    for metrics in gains_by_trial.values():
        if set(metrics) != set(METRICS) or len({len(v) for v in metrics.values()}) != 1:
            raise ValueError('All four metrics on the same paired sample required')
        if any(len(v) < 900 for v in metrics.values()):
            raise ValueError('Both cohorts must reach 900 before inference')
    results = {trial: {metric: paired_inference(values) for metric, values in metrics.items()}
               for trial, metrics in gains_by_trial.items()}
    adjusted = holm_family({trial: results[trial]['rps']['p_one_sided'] for trial in FAMILY}, expected_ids=FAMILY)
    decisions = {}
    for trial in FAMILY:
        primary = results[trial]['rps']
        guards = [results[trial][m] for m in METRICS[1:]]
        passed = (not primary['degenerate'] and primary['ci95'][0] > 0
                  and adjusted['rejected'][trial]
                  and all(not g['degenerate'] and g['ci95'][0] >= 0 for g in guards))
        decisions[trial] = 'CRITERIA_MET' if passed else 'INCONCLUSIVE_OR_FAILED'
    return {'protocol': PROTOCOL['id'], 'statistics': results, 'holm': adjusted, 'decisions': decisions,
            'scientific_claim_authorized': False, 'capital_enabled': False}


def measure_supplied_family(samples: dict[str, dict]) -> dict:
    """Engineering pipeline on supplied samples, with joint preflight before losses.

    This is not the one-shot operational evaluator: it grants no registration,
    cohort access, scientific approval or retry permission.
    """
    if set(samples) != set(FAMILY):
        raise ValueError('Complete successor family required')
    identities = []
    for member in FAMILY:
        rows = samples[member]['records']
        if len(rows) != 900 or len(samples[member]['outcomes']) != 900:
            raise ValueError('Exactly 900 frozen paired observations per member required')
        identifiers = {_identifier(row['event_id']): _time(row['kickoff_at']) for row in rows}
        if len(identifiers) != 900:
            raise ValueError('Duplicate enrollment')
        identities.append(identifiers)
    if identities[0] != identities[1]:
        raise ValueError('Family members must have identical frozen enrollment and kickoff times')
    prepared = {member: paired_sample(**samples[member], trial=member) for member in FAMILY}
    return family_decision({member: prepared[member]['gains'] for member in FAMILY})
