"""Offline package and explicit synthetic CLI checks. Never starts operational entry points."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
ri=Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09')
python=ri/'venv/Scripts/python.exe'
uv=Path('C:/BRASILEIRAO/work/price-feasibility-2026-09-09/bootstrap/Scripts/uv.exe')
out=root/'package-smoke-final';out.mkdir(exist_ok=False)
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT'}}
env.update(TEMP=str(out),TMP=str(out),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',
           UV_CACHE_DIR='C:/BRASILEIRAO/work/implementacao-2026-09-10/uv-cache')
env['PATH']=str(python.parent)+os.pathsep+str(Path(env['SYSTEMROOT'])/'System32')
records=[]
def run(name,args,cwd=out,expected=0):
    result=subprocess.run([str(a) for a in args],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (out/(name+'.log')).write_bytes(result.stdout)
    records.append(dict(name=name,argv=[str(a) for a in args],exit_code=result.returncode,expected=expected))
    (root/'package-receipt-final.json').write_text(json.dumps(dict(commands=records),indent=2),encoding='utf-8')
    print(name,result.returncode,result.stdout.decode('utf-8',errors='replace')[-800:],flush=True)
    assert result.returncode==expected,name
    return result.stdout
run('build',[uv,'build','--offline','--no-python-downloads','--python',python,'--out-dir',out/'dist'],cwd=repo)
wheel=next((out/'dist').glob('*.whl'))
run('install',[uv,'pip','install','--python',python,'--offline','--no-deps','--target',out/'installed',wheel])
env['PYTHONPATH']=str(out/'installed')
module='brasileirao_predictor.data.odds_api_snapshot'
raw=out/'empty.json';raw.write_bytes(b'[]')
run('odds-empty',[python,'-B','-m',module,raw,'--sha256',hashlib.sha256(raw.read_bytes()).hexdigest(),
                 '--received-at','2020-01-01T12:00:00Z','--output',out/'empty-result.json'])
value=json.loads((out/'empty-result.json').read_text())
assert value['observation_status']=='VALID_EMPTY' and value['execution']=='ABSTAIN'
invalid=out/'invalid.json';invalid.write_bytes(b'[{"id":"ambiguous"}]')
run('odds-invalid',[python,'-B','-m',module,invalid,'--sha256',hashlib.sha256(invalid.read_bytes()).hexdigest(),
                 '--received-at','2020-01-01T12:00:00Z','--output',out/'invalid-result.json'],expected=2)
payload=dict(prediction_kind='PRE_MATCH',event_id='synthetic',home='A',away='B',predicted_at='2020-01-01T12:00:00Z',
             kickoff_at='2020-01-01T13:00:00Z',model_name='synthetic',model_version='1',pipeline_fingerprint='synthetic',
             historical_data_cutoff='2020-01-01T12:00:00Z',latest_training_match_kickoff='2019-12-30T12:00:00Z',
             latest_training_result_available_at='2019-12-30T15:00:00Z',current_season_matches_included=0,
             current_season_matches_available=0,lineup_confirmed=False,capital_enabled=False)
for enabled,code in [(False,0),(True,2)]:
    path=out/f'readiness-{enabled}.json';path.write_text(json.dumps({**payload,'capital_enabled':enabled}),encoding='utf-8')
    run('readiness-'+str(enabled),[python,'-B','-m','brasileirao_scripts.check_prediction_readiness',path],expected=code)
source=run('installed-path',[python,'-B','-c','import brasileirao_predictor.data.odds_api_snapshot as m; print(m.__file__)']).decode().strip()
assert Path(source).is_relative_to(out/'installed')
receipt=dict(commands=records,installed_source=source,dependency_scope='wheel installed to explicit target; dependencies supplied by existing isolated RI venv',
             files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (out/'dist').iterdir()})
(root/'package-receipt-final.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
