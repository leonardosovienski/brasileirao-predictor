"""Record final checks after the live status/optional-limit hardening."""
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
binpath=Path('C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv/Scripts')
logs=root/'engineering-03'
logs.mkdir(exist_ok=False)
changed=[repo/'brasileirao_predictor/research/price_strength/live_capture_admission.py',repo/'tests/test_live_capture_admission.py']
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC','PATHEXT'}}
jobs=[('pytest_final',[binpath/'python.exe','-I',root/'validate_offline.py',repo,root/'tests-05']),
      ('ruff_changed',[binpath/'ruff.exe','check','--no-cache',*changed]),
      ('format_changed',[binpath/'ruff.exe','format','--check','--no-cache',*changed]),
      ('pilot_unchanged',[binpath/'python.exe','-I',root/'verify_pilot_after_fix.py'])]
checks=[]
for name,args in jobs:
    started=datetime.now(UTC).isoformat()
    result=subprocess.run(list(map(str,args)),cwd=repo,env=env,capture_output=True,text=True,timeout=60)
    log=logs/(name+'.txt')
    log.write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    checks.append({'name':name,'returncode':result.returncode,'started_at':started,'finished_at':datetime.now(UTC).isoformat(),'log':str(log)})
    if result.returncode:
        raise RuntimeError('check_failed:'+name)
suites=list(ET.parse(root/'tests-05/junit.xml').getroot().iter('testsuite'))
counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ('tests','failures','errors','skipped')}
assert counts=={'tests':138,'failures':0,'errors':0,'skipped':0}
path=root/'engineering_checks.json'
receipt=json.loads(path.read_text(encoding='utf-8'))
receipt['checks'].extend(checks)
receipt['completed_at']=datetime.now(UTC).isoformat()
receipt['pytest']=counts
receipt['pytest_final_junit']=str(root/'tests-05/junit.xml')
receipt['regression_before_fix']={'passed':137,'failed':1,'junit':str(root/'tests-04-regression-before-fix/junit.xml')}
receipt['new_tests']=58
receipt['typecheck_initial_error']={'log':str(root/'engineering-02/pyright_explicit_config_initial_failure.txt'),
                                  'reason':'optional_limit_operand','resolved':True}
for p in changed:
    receipt['source_hashes'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','pytest':counts,'pilot_audits_unchanged':True}))
