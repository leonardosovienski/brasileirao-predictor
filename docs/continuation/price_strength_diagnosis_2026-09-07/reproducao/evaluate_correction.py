"""One frozen quality/reliability experiment; no operational I/O or optimization search."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from brasileirao_predictor.data.xg_quality import classify_xg_pair
from brasileirao_predictor.research.price_strength.dynamic_xg import DynamicXGConfig
from brasileirao_predictor.research.price_strength_reliability import blend, fit_weight

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = ROOT / 'work/price_strength_evaluation'
sys.path.insert(0, str(PREVIOUS))
from conditional_model import forecast_conditional  # noqa: E402
from evaluate import MARKETS, accounting, flatten, losses  # noqa: E402
from frozen_economics import evaluate_candidates, select_candidate, settle_candidate  # noqa: E402

OUT = ROOT / 'outputs/DIAGNOSTICO_XG/CORRECAO'
OLD = ROOT / 'outputs/TESTE_XG_REAL'
PLAN_SHA = '2c9a6615f77c2568ecc70868ce8283f6bb6a5796c622df898bc3858927e11a92'
START = datetime(2024, 1, 1, tzinfo=UTC)
END = datetime(2025, 1, 1, tzinfo=UTC)
NEW = ('quality_raw_market_blend', 'quality_raw', 'quality_rate_calibrated')
CONTROLS = ('xg_calibrated_primary', 'xg_raw_diagnostic', 'old_raw_frozen_2024', 'market_proportional_devig')
ARMS = (*NEW, *CONTROLS)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (OUT / name).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def clock(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('naive kickoff')
    return result.astimezone(UTC)


def feature_history(history):
    """Quarantine only feature rows; targets and labels remain independent."""
    retained, excluded, counts = [], [], {}
    if len({str(r['event_id']) for r in history}) != len(history):
        raise ValueError('duplicate event IDs')
    for row in history:
        result = row.get('result') or {}
        category = classify_xg_pair(result.get('home_xg'), result.get('away_xg'))
        year = str(clock(row['kickoff']).year)
        counts.setdefault(year, Counter())[category] += 1
        if category == 'INVALID_PAIR':
            raise ValueError('invalid numeric xG pair')
        if category == 'NUMERIC_PAIR':
            retained.append(row)
        else:
            excluded.append({'event_id': str(row['event_id']), 'category': category})
    return retained, {'by_year': counts, 'excluded_features': excluded,
                      'policy': 'ZERO_PAIR_QUARANTINE_ASSUMPTION_NOT_MISSINGNESS_FACT'}


def market_vector(odds, market):
    inverse = [1 / value for value in odds[market]]
    return dict(zip(MARKETS[market], [p / math.fsum(inverse) for p in inverse]))


def outcome_indices(result):
    h, a = result['home_goals'], result['away_goals']
    if type(h) is not int or type(a) is not int or min(h, a) < 0:
        raise ValueError('invalid final scores')
    return {'1x2': 0 if h > a else 1 if h == a else 2,
            'ou25': 0 if h + a >= 3 else 1, 'btts': 0 if h > 0 and a > 0 else 1}


def fit_stage(history, config):
    features, quality = feature_history(history)
    calibration_rows, predicted_h, predicted_a, goals_h, goals_a = [], [], [], [], []
    used_ids, targets = set(), []
    for row in sorted(history, key=lambda r: (clock(r['kickoff']), str(r['event_id']))):
        kickoff = clock(row['kickoff'])
        if kickoff < START or kickoff + timedelta(hours=48) >= END:
            continue
        # Forecast receives feature history and identity, never the target label.
        raw = forecast_conditional(features, row, config)
        if not raw['eligible']:
            continue
        result = row.get('result') or {}
        if result.get('home_goals') is None and result.get('away_goals') is None:
            continue
        outcome = outcome_indices(result)
        predicted_h.append(raw['lambda_home'])
        predicted_a.append(raw['lambda_away'])
        goals_h.append(result['home_goals'])
        goals_a.append(result['away_goals'])
        targets.append(str(row['event_id']))
        used_ids.update([*raw['history_ids'], str(row['event_id'])])
        valid = evaluate_candidates(flatten(raw['probabilities']), row['odds'])['valid_markets']
        calibration_rows.append({
            'event_id': str(row['event_id']), 'kickoff': row['kickoff'],
            'decision_at': raw['decision_at'], 'history_ids': raw['history_ids'],
            'probabilities': raw['probabilities'],
            'market': {market: market_vector(row['odds'], market) for market in valid},
            'odds': row['odds'], 'outcome': {key: result[key] for key in ('home_goals', 'away_goals')},
            'outcome_indices': outcome, 'availability_policy': 'ASSUMED_48H_NOT_OBSERVED',
        })
    weights = {}
    for market, sides in MARKETS.items():
        panel = [row for row in calibration_rows if market in row['market']]
        if len(panel) < config.min_calibration_matches:
            raise ValueError('insufficient independent calibration observations')
        fitted = fit_weight(
            [tuple(row['probabilities'][market][s] for s in sides) for row in panel],
            [tuple(row['market'][market][s] for s in sides) for row in panel],
            [row['outcome_indices'][market] for row in panel],
        )
        weights[market] = {**asdict(fitted), 'event_ids': [row['event_id'] for row in panel]}
    prior = config.calibration_prior_exposure
    calibration = {
        'n_matches': len(targets), 'eligible': len(targets) >= config.min_calibration_matches,
        'reason': 'ELIGIBLE' if len(targets) >= config.min_calibration_matches else 'INSUFFICIENT_CALIBRATION',
        'home_scale': (math.fsum(goals_h) + prior) / (math.fsum(predicted_h) + prior),
        'away_scale': (math.fsum(goals_a) + prior) / (math.fsum(predicted_a) + prior),
        'used_match_ids': sorted(used_ids), 'target_match_ids': targets,
        'config_fingerprint': config.fingerprint, 'training_end': START.isoformat(),
        'calibration_end': END.isoformat(), 'availability_policy': 'ASSUMED_48H_NOT_OBSERVED',
        'assumed_lag_hours': 48, 'status': 'CONDITIONAL_DIAGNOSTIC_NOT_PIT_ATTESTED',
    }
    return features, quality, calibration_rows, weights, calibration


def compare_scores(rows):
    return {arm: {market: {metric: math.fsum(row['scores'][arm][market][metric] for row in rows) / len(rows)
                           for metric in ('brier', 'log_loss')} for market in MARKETS} for arm in ARMS}


def bootstrap(rows, replicates=2000, seed=20260908):
    weeks = [tuple(clock(row['kickoff']).isocalendar()[:2]) for row in rows]
    groups = [[i for i, week in enumerate(weeks) if week == key] for key in sorted(set(weeks))]
    if not groups:
        raise ValueError('empty comparison panel')
    draws = np.random.default_rng(seed).integers(0, len(groups), size=(replicates, len(groups)))
    denominators = np.array([len(group) for group in groups])[draws].sum(axis=1)

    def interval(values):
        totals = np.array([math.fsum(values[i] for i in group) for group in groups])
        ci = np.quantile(totals[draws].sum(axis=1) / denominators, [0.025, 0.975])
        return {'delta_mean': math.fsum(values) / len(values), 'ci95_descriptive': [float(v) for v in ci]}

    result = {'weeks': len(groups), 'replicates': replicates, 'seed': seed, 'comparisons': {}}
    for control in CONTROLS:
        result['comparisons'][control] = {
            'probabilistic': {market: {metric: interval([
                row['scores'][NEW[0]][market][metric] - row['scores'][control][market][metric] for row in rows
            ]) for metric in ('brier', 'log_loss')} for market in MARKETS},
            'net_per_fixture': interval([
                (row['bets'][NEW[0]]['settlement']['net_profit_units'] if row['bets'][NEW[0]] else 0)
                - (row['bets'][control]['settlement']['net_profit_units'] if row['bets'][control] else 0)
                for row in rows]),
        }
    return result


def main():
    if sha(OUT / 'PLANO.json') != PLAN_SHA:
        raise ValueError('plan changed')
    plan = json.loads((OUT / 'PLANO.json').read_text())
    for name, expected in plan['inputs'].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f'frozen input changed: {name}')
    import brasileirao_predictor.research.price_strength_reliability as reliability
    import brasileirao_predictor.data.xg_quality as quality_module
    import brasileirao_predictor.research.price_strength.dynamic_xg as dynamic
    write('EXECUTION_LOCK.json', {'plan_sha256': PLAN_SHA, 'new_scores_computed': False,
          'source_sha256': {str(path): sha(path) for path in [Path(__file__), Path(reliability.__file__),
          Path(quality_module.__file__), Path(dynamic.__file__)]}})
    history = json.loads((PREVIOUS / 'inputs/history.json').read_text())
    config = DynamicXGConfig(**plan['candidate_config'])
    features, quality, calibration_rows, weights, rate_calibration = fit_stage(history, config)
    previous_result = json.loads((OLD / 'results.json').read_text())
    assert rate_calibration == previous_result['calibration'], 'quality must not change 2024 rate calibration'
    write('quality.json', quality)
    write('calibration_rows.json', calibration_rows)
    write('FIT.json', {'weights': weights, 'rate_calibration_diagnostic': rate_calibration,
                     'fitted_only_2024': True, 'candidate_config': asdict(config),
                     'availability_policy': 'ASSUMED_48H_NOT_OBSERVED'})
    write('FIT_LOCK.json', {'fit_sha256': sha(OUT / 'FIT.json'), 'calibration_rows_sha256': sha(OUT / 'calibration_rows.json'),
                           'evaluation_forecasts_computed': False})
    previous_predictions = {row['event_id']: row for row in json.loads((OLD / 'forecasts.json').read_text())}
    old_panel = {row['event_id'] for row in json.loads((OLD / 'panel.json').read_text()) if row['included']}
    targets = sorted([r for r in history if clock(r['kickoff']).year == 2025], key=lambda r: (clock(r['kickoff']), str(r['event_id'])))
    assert [str(r['event_id']) for r in targets] == [r['event_id'] for r in plan['evaluation_fixtures']]
    forecasts, panel, changed_ids = [], [], []
    for target in targets:
        event_id = str(target['event_id'])
        raw = forecast_conditional(features, target, config)
        calibrated = forecast_conditional(features, target, config, calibration=rate_calibration)
        old_raw = previous_predictions[event_id]['raw']
        changed = raw['eligible'] != old_raw['eligible'] or raw['probabilities'] != old_raw['probabilities']
        if changed:
            changed_ids.append(event_id)
        if event_id not in plan['potentially_affected_2025_ids']:
            assert not changed, 'quarantine affected an unrelated fixture'
        valid = evaluate_candidates(flatten(raw['probabilities']), target['odds'])['valid_markets'] if raw['eligible'] else []
        q = {market: market_vector(target['odds'], market) for market in valid}
        primary = {}
        if raw['eligible'] and len(q) == 3:
            primary = {market: dict(zip(sides, blend(tuple(raw['probabilities'][market][s] for s in sides),
                        tuple(q[market][s] for s in sides), weights[market]['weight']))) for market, sides in MARKETS.items()}
        common = event_id in old_panel and bool(primary) and calibrated['eligible']
        panel.append({'event_id': event_id, 'original_common': event_id in old_panel, 'common': common,
                      'quality_raw_eligible': raw['eligible'], 'complete_quotes': len(q) == 3,
                      'quarantine_changed_raw': changed})
        forecasts.append({'event_id': event_id, 'kickoff': target['kickoff'], 'raw': raw,
                          'calibrated': calibrated, 'primary_probabilities': primary, 'market': q})
    write('forecasts.json', forecasts)
    write('panel.json', panel)
    write('FORECAST_LOCK.json', {'forecasts_sha256': sha(OUT / 'forecasts.json'), 'panel_sha256': sha(OUT / 'panel.json'),
                                'new_evaluation_scores_computed': False})
    previous_rows = json.loads((OLD / 'event_results.json').read_text())
    lookup = {row['event_id']: row for row in forecasts}
    common_ids = {r['event_id'] for r in panel if r['common']}
    rows, full_original = [], []
    for previous in previous_rows:
        event_id = previous['event_id']
        prediction = lookup[event_id]
        probabilities = {**previous['probabilities'], NEW[0]: prediction['primary_probabilities'],
                         NEW[1]: prediction['raw']['probabilities'], NEW[2]: prediction['calibrated']['probabilities']}
        choices = {arm: select_candidate(flatten(probabilities[arm]), previous['odds']) if probabilities[arm] else None for arm in NEW}
        bets = {**previous['bets'], **{arm: {'candidate': choice, 'settlement': settle_candidate(choice, **previous['outcome'])}
                                     if choice else None for arm, choice in choices.items()}}
        record = {**previous, 'probabilities': probabilities, 'bets': bets, 'common': event_id in common_ids}
        record['scores'] = {**previous['scores'], **{arm: losses(probabilities[arm], previous['outcome']) if probabilities[arm] else None for arm in NEW}}
        full_original.append(record)
        if record['common']:
            rows.append(record)
    if not rows:
        raise ValueError('no common comparison fixtures')
    result = {
        'status': 'EXPLORATORY_AFTER_DIAGNOSIS_NOT_NEW_HOLDOUT', 'plan_sha256': PLAN_SHA,
        'coverage': {'universe': len(targets), 'original_common': len(previous_rows), 'new_common': len(rows),
                     'additional_excluded_ids': sorted(old_panel - common_ids), 'changed_raw_ids': changed_ids},
        'weights': {market: {k: value for k, value in fitted.items() if k != 'event_ids'} for market, fitted in weights.items()},
        'probabilistic_common': compare_scores(rows),
        'economics_common': {arm: accounting(rows, arm) for arm in ARMS},
        'economics_original_panel_with_explicit_abstentions': {arm: accounting(full_original, arm) for arm in ARMS},
        'bootstrap_common': bootstrap(rows, **{k: plan['bootstrap'][k] for k in ('replicates', 'seed')}),
        'rate_calibration_2024_unchanged': True,
        'availability_policy': 'ASSUMED_48H_NOT_OBSERVED', 'execution_attested': False,
        'joint_score_distribution_attested': False, 'promoted': False, 'real_capital_enabled': False,
    }
    write('event_results.json', rows)
    write('original_panel_results.json', full_original)
    write('results.json', result)
    write('MANIFEST.json', {'files': {p.name: sha(p) for p in sorted(OUT.glob('*.json')) if p.name != 'MANIFEST.json'}})
    print(json.dumps({key: result[key] for key in ('coverage','weights','probabilistic_common','economics_common')}, indent=2))


if __name__ == '__main__':
    main()
