"""Create compact review receipts from explicit non-operational artifacts."""
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
REPO = Path('C:/BRASILEIRAO/brasileirao-predictor')
DEST = REPO / 'docs/continuation/integral_review_2026-09-09/evidence'
DEST.mkdir(parents=True, exist_ok=True)

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def save(name, obj):
    (DEST / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

rounds = ['regressions-before','regressions-after','temporal-before','temporal-after',
          'domain-before','concurrency-before','event-before','baseline-broad',
          'baseline-failure-recheck','final-corrections','isolation-boundary']
receipts = []
latest = {}
for label in rounds:
    path = ROOT / label / 'junit.xml'
    if not path.exists():
        raise FileNotFoundError(path)
    cases = []
    for case in ET.parse(path).iter('testcase'):
        status = 'failed' if case.find('failure') is not None else 'error' if case.find('error') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
        identity = case.attrib.get('classname','') + '::' + case.attrib['name']
        cases.append({'id':identity,'status':status})
        if label in {'baseline-broad','baseline-failure-recheck','final-corrections'}:
            latest[identity] = {'status':status,'round':label}
    receipts.append({'round':label,'junit':str(path),'sha256':digest(path),'counts':dict(Counter(c['status'] for c in cases))})
    save(label + '-cases.json', cases)
save('tests.json', {'rounds':receipts,'latest_case_outcomes':dict(Counter(c['status'] for c in latest.values())), 'latest_cases':latest,
                   'not_a_single_full_suite':True,'protected_evaluators_excluded':True})
source = read(ROOT / 'source_inventory.json')
save('inventory-summary.json', {'source_files':len(source),'review_methods':dict(Counter(r['review'] for r in source)),
     'baseline_selected_test_files':len(read(ROOT / 'baseline-test-selection.json')), 'inventory_sha256':digest(ROOT / 'source_inventory.json'),
     'full_inventory':str(ROOT / 'source_inventory.json'), 'not_line_by_line_certification':True})
save('data-summary.json', read(ROOT / 'data-audit-02/summary.json'))
closing = read(ROOT / 'data-audit-02/closing_reproduction.json')
events = closing.pop('events')
closing['abstention_reasons'] = dict(Counter(e.get('reason') for e in events if e['status']=='ABSTAIN'))
closing['first_bet_date'] = min(e['date'] for e in events if e['status']=='SETTLED')
closing['last_bet_date'] = max(e['date'] for e in events if e['status']=='SETTLED')
closing['monthly_bet_counts'] = dict(Counter(e['date'][:7] for e in events if e['status']=='SETTLED'))
closing['full_receipt_sha256'] = digest(ROOT / 'data-audit-02/closing_reproduction.json')
save('closing-summary.json', closing)
for src, dst in [('environment.json','environment.json'),('data-audit-02/frozen_identity_receipt.json','frozen-identity.json'),
                 ('public-sources/receipts.json','public-source-receipts.json'),('dotnet-sdk-receipt.json','dotnet-sdk.json')]:
    save(dst, read(ROOT / src))
save('artifact-locations.json', {'generated_at':datetime.now(UTC).isoformat(),
    'work':str(ROOT), 'repo':str(REPO),
    'data_inputs_unchanged':str(Path('C:/BRASILEIRAO/work/data-completion-2026-09-09')),
    'github_base_ci_run':'https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34419406215',
    'base_commit':'ac22c56c3318623e07a722f34d44dc6cd877ea37',
    'hashes':{p.relative_to(ROOT).as_posix():digest(p) for p in ROOT.glob('*.log')}})
print(json.dumps({'rounds':[(r['round'],r['counts']) for r in receipts], 'latest_case_outcomes':dict(Counter(c['status'] for c in latest.values()))},ensure_ascii=False))
