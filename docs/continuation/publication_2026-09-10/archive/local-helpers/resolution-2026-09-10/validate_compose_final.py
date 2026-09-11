"""Offline validation of public Compose and example variables only."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
out=root/'compose-final';out.mkdir(exist_ok=False)
binary=root/'compose-check/docker-compose-windows-x86_64.exe'
assert hashlib.sha256(binary.read_bytes()).hexdigest()=='51e1e61195f3616896265487ed64551095f3bd27ac7fbd5758d3538c3bfa1b19'
shutil.copyfile(repo/'compose.yaml',out/'compose.yaml')
(out/'empty.env').write_text('',encoding='utf-8')
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT'}}
env.update(TEMP=str(out),TMP=str(out),USERPROFILE=str(out),DOCKER_CONFIG=str(out/'docker-config'),COMPOSE_DISABLE_ENV_FILE='1')
command=[str(binary),'--env-file',str(out/'empty.env'),'-f',str(out/'compose.yaml'),'config','--no-env-resolution','--format','json']
result=subprocess.run(command,cwd=out,env=env,capture_output=True,timeout=60)
(out/'model.json').write_bytes(result.stdout)
(out/'stderr.log').write_bytes(result.stderr)
assert result.returncode==0
model=json.loads(result.stdout)
worker=model['services']['worker']['environment']
assert worker['LINEUP_Exchange__WebSocketUrl']==''
assert worker['LINEUP_Worker__AllowSyntheticInputs']=='false'
assert set(model['services'])=={'redis','init-data','kernel','worker'}
receipt=dict(command=command,exit_code=0,compose_sha256=hashlib.sha256((repo/'compose.yaml').read_bytes()).hexdigest(),
    model_sha256=hashlib.sha256(result.stdout).hexdigest(),services=sorted(model['services']),
    feed_disabled_by_default=True,synthetic_inputs_disabled_by_default=True,daemon_started=False,containers_executed=False)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
