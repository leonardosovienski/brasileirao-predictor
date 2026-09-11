import json
import os
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parent
out=root/'package-final-cli';out.mkdir(exist_ok=False)
venv=root/'installed-cross-environment/venv'
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT'}}
env.update(TEMP=str(out),TMP=str(out),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
records=[]
def run(name,args,expected=0):
    result=subprocess.run([str(a) for a in args],cwd=out,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    (out/(name+'.log')).write_bytes(result.stdout)
    records.append(dict(name=name,argv=[str(a) for a in args],exit_code=result.returncode,expected=expected))
    (out/'receipt.json').write_text(json.dumps(dict(commands=records,completed=False),indent=2),encoding='utf-8')
    print(name,result.returncode,flush=True)
    assert result.returncode==expected

run('health-missing-config',[venv/'Scripts/brasileirao-kernel.exe','--healthcheck'],2)
run('health-invalid-endpoint-no-network',[venv/'Scripts/brasileirao-kernel.exe','--healthcheck','--db',out/'unused.db','--redis','invalid://synthetic'],1)
assert not (out/'unused.db').exists()
for name in ('brasileirao_predictor.data.odds_api_snapshot','brasileirao_scripts.import_ou25_historical_backfill','brasileirao_scripts.odds_shop','brasileirao_scripts.settle_live_prediction'):
    run(name.rsplit('.',1)[-1]+'-help',[venv/'Scripts/python.exe','-I','-B','-m',name,'--help'])
(out/'receipt.json').write_text(json.dumps(dict(commands=records,completed=True,earlier_harness_error='package-final expected health=1 without required configuration; actual argparse contract=2. Original failure preserved, no product code changed.'),indent=2),encoding='utf-8')
