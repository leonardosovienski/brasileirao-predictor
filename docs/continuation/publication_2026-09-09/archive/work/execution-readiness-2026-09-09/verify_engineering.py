"""Record integration checks and replay the real pilot through the repaired guard."""
import hashlib
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
scripts=repo/'docs/continuation/data_completion_2026-09-09/reproducao'
venv=Path('C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv')
node=Path('C:/Users/leona/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
logs=root/'checks'
logs.mkdir(exist_ok=False)
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC','PATHEXT'}}
changed=[scripts/'followup_capture.py',scripts/'audit_followup.py',repo/'tests/test_followup_capture_contract.py']
checks=[]


def run(name,args):
    started=datetime.now(UTC).isoformat()
    result=subprocess.run(list(map(str,args)),cwd=repo,env=env,capture_output=True,text=True,timeout=90)
    log=logs/(name+'.txt')
    output=result.stdout+'\n'+result.stderr
    log.write_text(output,encoding='utf-8')
    checks.append({'name':name,'returncode':result.returncode,'started_at':started,
                   'finished_at':datetime.now(UTC).isoformat(),'log':str(log)})
    if result.returncode:
        raise RuntimeError(name+': '+output)
    return output


run('pytest',[venv/'Scripts/python.exe','-I',root/'validate_offline.py',root/'tests-04-integrated','--full-research'])
run('ruff',[venv/'Scripts/ruff.exe','check','--no-cache',*changed])
run('format',[venv/'Scripts/ruff.exe','format','--check','--no-cache',*changed])
output=run('pyright',[node,venv/'Lib/site-packages/pyright/dist/index.js','--project',root/'pyrightconfig.json','--stats'])
assert 'Total files checked: 2' in output

# Genuine already-observed pilot, keeping original body and timestamps. No new odds.
pilot=Path('C:/BRASILEIRAO/work/data-completion-2026-09-09/prospective_pilot')
receipt=json.loads((pilot/'receipt.json').read_text(encoding='utf-8'))
record=next(r for r in receipt['requests'] if r['endpoint'].endswith('/odds'))
replay=root/'existing_pilot_guard_check'
(replay/'followup').mkdir(parents=True,exist_ok=False)
raw=(pilot/record['file']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==record['sha256']
(replay/'followup/capture.json').write_bytes(raw)
original_file=record['file']
record['file']='capture.json'
(replay/'followup/receipt.json').write_text(json.dumps({'requests':[record]},indent=2)+'\n',encoding='utf-8')
shutil.copyfile(scripts/'audit_followup.py',replay/'audit_followup.py')
run('real_pilot_guard',[venv/'Scripts/python.exe','-I',replay/'audit_followup.py'])
audited=json.loads((replay/'followup_audit/audit.json').read_text(encoding='utf-8'))
assert not audited['prospective_price_observation_admitted'] and not audited['execution_admitted']
assert not audited['frozen_decision_clock_admitted'] and audited['source_hash']==record['sha256']
run('audit_idempotent',[venv/'Scripts/python.exe','-I',replay/'audit_followup.py'])
suites=list(ET.parse(root/'tests-04-integrated/junit.xml').getroot().iter('testsuite'))
counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ('tests','failures','errors','skipped')}
assert counts=={'tests':153,'failures':0,'errors':0,'skipped':0}
state={'completed_at':datetime.now(UTC).isoformat(),'status':'PASS','checks':checks,'pytest':counts,
       'new_rehearsal_tests':15,'regressions_failed_before_fix':5,'real_api_calls':0,'real_credentials_read':False,
       'research_guard':'network_sqlite_subprocess_private_and_operational_inputs_denied',
       'synthetic_rehearsal_is_market_evidence':False,
       'existing_pilot_guard':{'source_file':original_file,'clocks_preserved':True,'body_sha256':record['sha256'],
                             'new_observation':False,'T60_admitted':False},
       'source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in changed}}
(root/'engineering_checks.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','tests':153,'new_tests':15,'source_guard_rejected_old_pilot':True}))
