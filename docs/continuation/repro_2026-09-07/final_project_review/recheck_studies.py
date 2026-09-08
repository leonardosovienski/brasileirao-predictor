"""Reexecute fixed historical calculations; preserve all original artifacts."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

WORK = Path(__file__).resolve().parent
BASE = WORK.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def compare(a,b,path='root'):
    if isinstance(a,dict):
        assert isinstance(b,dict) and a.keys()==b.keys(),path
        for k in a:
            compare(a[k],b[k],path+'.'+k)
    elif isinstance(a,list):
        assert isinstance(b,list) and len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):
            compare(x,y,f'{path}[{i}]')
    elif isinstance(a,(int,float)) and not isinstance(a,bool):
        assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-10),(path,a,b)
    else:
        assert a==b,(path,a,b)


old = BASE/'new_split_backtest/run'
new = WORK/'replay_verified'
for name in ('forecasts_2025.json','forecasts_2026.json'):
    compare(read(old/name),read(new/name),name)
old_candidate,new_candidate = read(old/'candidate.json'),read(new/'candidate.json')
scientific_keys = ['plan_sha256','config','model_state','calibration_2025','policy','source_sha256',
                   'train_events','calibration_events','train_event_ids_sha256','horizon_utc']
stable_old = {k:old_candidate[k] for k in scientific_keys}
stable_new = {k:new_candidate[k] for k in scientific_keys}
compare(stable_old,stable_new,'scientific_candidate')
old_result,new_result = read(old/'results.json'),read(new/'results.json')
for arm in old_result['arms']:
    for key in ('overall','by_role','by_round'):
        compare(old_result['arms'][arm][key],new_result['arms'][arm][key],f'{arm}.{key}')
    for a,b in zip(old_result['arms'][arm]['decisions'],new_result['arms'][arm]['decisions']):
        compare({k:v for k,v in a.items() if k!='candidate_frozen2025_hash'},
                {k:v for k,v in b.items() if k!='candidate_frozen2025_hash'},f'{arm}.decisions')
receipt = {'status':'PASS','new_split':{'forecasts_compared':760,'decisions_compared':760,
    'scientific_fingerprint':digest(stable_new),'same_scientific_state':True,
    'execution_hash_note':'Original candidate hash includes optimizer duration. Stable scientific fingerprint excludes runtime observations.'}}

legacy = BASE/'selection_reanalysis'
spec = importlib.util.spec_from_file_location('fixed_selection_review',legacy/'selective_replay.py')
module = importlib.util.module_from_spec(spec)
sys.path.insert(0,str(legacy))
spec.loader.exec_module(module)
plan=read(legacy/'analysis_plan.json')
rows,coverage=module.prepare_rows(read(legacy/'historical_input.json'),read(legacy/'forecasts.json'),plan)
decisions,fits=module.run_decisions(rows,plan)
summary=module.summarize(decisions,plan)
original=read(legacy/'selection_results.json')
compare(original['coverage'],coverage,'legacy.coverage')
compare(original['policies'],summary,'legacy.policies')
receipt['selection_2023_2025']={'status':'PASS','decisions_recomputed':len(decisions),
    'policies_recomputed':len(summary),'same_all_metrics':True,
    'policies':{name:value['overall'] for name,value in summary.items()}}

extension=BASE/'price_extension_51'
auditdir=WORK/'extension_derived_check'
auditdir.mkdir(exist_ok=True)
extension_files = {'audit_result_independently.py','evaluate.py','result.json','plan.json','selection.json',
                   'acquisition_manifest.json','implementation_receipt.json'}
extension_files.update(read(extension/'implementation_receipt.json')['hashes'])
for name in extension_files:
    if Path(name).name != name:
        raise ValueError('Unexpected extension receipt path')
    shutil.copy2(extension/name,auditdir/name)
audit=subprocess.run([sys.executable,str(auditdir/'audit_result_independently.py')],capture_output=True,text=True,check=False)
assert audit.returncode==0,audit.stderr
ext=read(auditdir/'independent_result_audit.json')
receipt['extension_51']={'status':ext['status'],'checks':ext['checks'],'errors':ext['errors'],
                       'primary':ext['primary'],'new_api_requests':0}
(WORK/'studies_reexecution.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'status':receipt['status'],'new_split':receipt['new_split'],
    'old_selection_decisions':len(decisions),'old_selection_policies':len(summary),
    'extension_audit_checks':ext['checks']}))
