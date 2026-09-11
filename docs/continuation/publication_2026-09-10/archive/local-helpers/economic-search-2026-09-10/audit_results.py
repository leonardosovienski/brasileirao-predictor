"""Independent Decimal reconciliation of frozen ledgers and price envelopes."""
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 40
ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run-01'
D = lambda x: Decimal(str(x))
manifest = json.loads((RUN / 'manifest.json').read_text())
for name, sha in manifest['outputs'].items():
    assert hashlib.sha256((RUN / name).read_bytes()).hexdigest() == sha
raw_path = Path('C:/BRASILEIRAO/work/data-completion-2026-09-09/public_sources/football_data_bra_origin_csv.csv')
raw = raw_path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == manifest['source_sha256']
rows = {}
for row in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
    if row['Season'] not in {str(y) for y in range(2012, 2025)}:
        continue
    key = '|'.join(row[x].strip() for x in ['Season', 'Home', 'Away'])
    assert key not in rows
    rows[key] = row
envelopes = json.loads((RUN / 'envelopes.json').read_text())
selected = []
for event in envelopes:
    if event.get('reason'):
        continue
    prices = [D(rows[event['key']]['MaxC' + side]) for side in 'HDA']
    adjusted = [1 + (o-1) * D('.99') for o in prices]
    inv = sum(1/o for o in adjusted)
    net = 1/inv - 1 - D('.02')
    assert abs(net - D(event['net'])) < D('1e-12')
    assert event['candidate'] == (net >= D('.005'))
    for i in range(3):
        assert abs(D(event['stakes'][i])*adjusted[i] - 1/inv) < D('1e-12')
    if event['candidate']:
        selected.append(event)
summary = json.loads((RUN / 'summary.json').read_text())
net = sum(D(x['net']) for x in selected)
worst = sum(D(min(c['worst_net'] for c in x['partial_fill_cases'])) for x in selected)
checks = {}
ledgers = json.loads((RUN / 'ledgers.json').read_text())
predictions = {r['key']:r for r in json.loads((RUN / 'predictions.json').read_text())}
for strategy, events in ledgers.items():
    stake = cost = receipts = D(0)
    bankrupt_date = None
    for event in events:
        original = rows[event['key']]
        pred = predictions[event['key']]['prediction']
        if pred:
            target_date = date.fromisoformat(event['date'])
            assert (target_date - date.fromisoformat(pred['latest_training_day'])).days >= 7
            assert (target_date - date.fromisoformat(pred['earliest_training_day'])).days <= 730
            assert abs(sum(pred[strategy])-1) < 1e-12
        if event['reason'] == 'insufficient_unreserved_bankroll' and bankrupt_date is None:
            bankrupt_date = event['date']
        if not event['stake']:
            continue
        gh, ga = int(original['HG']), int(original['AG'])
        won = event['choice'] == ('H' if gh>ga else 'A' if gh<ga else 'D')
        price = D(original['PSC' + event['choice']])
        ret = price if won else D(0)
        assert abs(ret-D(event['return'])) < D('1e-10')
        assert abs(ret-1-D('.02')-D(event['net'])) < D('1e-10')
        stake += 1; cost += D('.02'); receipts += ret
    ending = 100-stake-cost+receipts
    assert abs(ending-D(events[-1]['cash_after_day'])) < D('1e-8')
    checks[strategy] = {'stake':str(stake), 'cost':str(cost),'return':str(receipts),
                        'net':str(receipts-stake-cost),'final_cash':str(ending),
                        'first_capital_abstention_date':bankrupt_date}
result = {'verified_at':datetime.now(timezone.utc).isoformat(), 'all_checks_passed':True,
          'decimal_precision':40, 'events':len(rows), 'arbitrage_candidates':len(selected),
          'arbitrage_net':str(net),'ledger_checks':checks,
          'arbitrage_top_five_event_net':sum(x['net'] for x in sorted(selected,key=lambda x:x['net'],reverse=True)[:5]),
          'arbitrage_dates':len({x['date'] for x in selected}),
          'break_even_uniform_partial_fill_failure_probability_worst_case':float(net/(net-worst)),
          'failure_probability_interpretation':'Scenario: each basket independently suffers its worst incomplete subset with uniform probability; not measured refusal frequency.',
          'no_failure_cumulative_cost_budget_units':float(net),
          'forecast_bootstrap_limitation':'Resampling realized fills conditions on capital exhaustion; it is not a policy rerun or a future-income confidence interval.',
          'sensitivities_limitation':'Frozen fills; higher costs can exceed initial bank and are arithmetic stresses, not feasible alternative bankroll paths.'}
with (ROOT/'independent-audit.json').open('x',encoding='utf-8') as f:
    json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
