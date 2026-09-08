"""Freeze one new correction study before its weights, forecasts and scores."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/DIAGNOSTICO_XG/CORRECAO'
OUT.mkdir(parents=True, exist_ok=False)
OLD = ROOT / 'outputs/TESTE_XG_REAL'
WORK = ROOT / 'work/price_strength_evaluation'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


old_plan = json.loads((OLD / 'PLANO.json').read_text())
plan = {
    'study_id': 'xg-quality-and-market-reliability-20260908-v1',
    'created_at_utc': datetime.now(UTC).isoformat(),
    'status': 'EXPLORATORY_AFTER_DIAGNOSIS_NOT_NEW_HOLDOUT',
    'question': 'Can a 2024-learned reliance on raw xG versus market reduce forecast error and false edges in explored 2025?',
    'mechanisms': [
        'Flag reported numeric coverage separately from provenance; quarantine all ambiguous zero pairs as feature history.',
        'Keep raw xG defaults; learn one convex Brier weight per market from temporal raw predictions in 2024.',
        'Use raw forecasts for fitting, avoiding goal-rate calibration learned from the same 2024 labels.',
    ],
    'candidate_config': old_plan['candidate_config'],
    'quality_policy': 'Exclude both-xG-zero, missing or partial pairs from feature history, never by goals or target own xG; reject malformed pairs. Keep original bytes and target labels.',
    'calibration': {
        'start': '2024-01-01T00:00:00+00:00', 'end': '2025-01-01T00:00:00+00:00',
        'label_policy': 'kickoff+48h strictly before end, ASSUMED_NOT_OBSERVED',
        'weight': 'clip(sum((p-q)*(y-q))/sum((p-q)^2),0,1); zero denominator -> 0',
        'markets': 'one weight for all three 1X2 classes; one weight and complement in each binary market',
        'scores': 'multiclass sum and binary positive-class Brier, separately per market',
        'minimum_per_market': 20,
        'quote_gates': 'same frozen complete-vector bounds and overround gates; individual market fit panels',
        'no_calibrated_2024_meta_inputs': True,
    },
    'primary_arm': 'quality_raw_market_blend',
    'fixed_diagnostic_arms': ['quality_raw', 'quality_rate_calibrated'],
    'controls': ['xg_calibrated_primary', 'xg_raw_diagnostic', 'old_raw_frozen_2024', 'market_proportional_devig'],
    'diagnostic_constraints': [
        '2024 rate calibration must equal previous study exactly because no zero-2021 rows enter its histories.',
        'Only the 10 identified fixtures may change raw eligibility/probabilities due to quarantine.',
        'Do not select among arms or adjust thresholds after scores.',
    ],
    'potentially_affected_2025_ids': ['13473341','13473357','13473359','13473377','13473380','13473397','13473398','13473417','13473426','13473438'],
    'evaluation_fixtures': old_plan['evaluation_fixtures'],
    'comparison_panel': 'intersection of original 368 common IDs and new raw/calibrated/primary eligibility, fixed before scoring',
    'coverage_policy': 'report full 380 and original 368, new exclusions; never claim loss reduction from dropping fixtures alone',
    'economics': 'Unchanged frozen_economics.py: 1u, max1/event, 0.02u cost every bet, edge(0.02,0.15], positive netEV, original odds/overround bounds and tie order.',
    'fit_objective': 'Brier only, no PnL/ROI tuning or search',
    'primary_claim_criteria': 'Report each market separately vs old calibrated and market; no general improvement unless Brier lower in all three. Profit requires positive net; fewer bets/zero stake is abstention, not a profitable system.',
    'bootstrap': {'replicates': 2000, 'seed': 20260908, 'unit': 'paired ISO calendar weeks including no-bet fixtures', 'scope': 'descriptive only; no multiplicity or fit uncertainty adjustment'},
    'availability_policy': 'ASSUMED_48H_NOT_OBSERVED; aggregate retrospective quotes, no bookmaker/receipt/execution attestation',
    'joint_distribution': 'Blended market marginals are not asserted to share a joint score distribution; no correct-score matrix use.',
    'stopping_rule': 'One frozen fit and evaluation, publish all arms including negative/zero-bet, no retune, no promotion, no 2026/cohorts.',
    'inputs': {str(p.relative_to(ROOT)): sha(p) for p in [
        WORK / 'inputs/history.json', WORK / 'conditional_model.py', WORK / 'frozen_economics.py',
        OLD / 'PLANO.json', OLD / 'panel.json', OLD / 'forecasts.json', OLD / 'event_results.json', OLD / 'results.json',
    ]},
}
with (OUT / 'PLANO.json').open('x', encoding='utf-8') as file:
    json.dump(plan, file, ensure_ascii=False, indent=2, allow_nan=False)
    file.write('\n')
print(json.dumps({'plan_sha256': sha(OUT / 'PLANO.json'), 'evaluation_not_executed': True}))
