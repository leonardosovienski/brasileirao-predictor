"""Persist this repository's CI evidence; credentials stay in process memory."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests

repo = 'leonardosovienski/brasileirao-predictor'
root = Path('C:/BRASILEIRAO/work/publication-2026-09-10')
run_id = int(sys.argv[1])
api = f'https://api.github.com/repos/{repo}'
session = requests.Session()
session.headers.update(Accept='application/vnd.github+json', **{'X-GitHub-Api-Version':'2022-11-28'})
response = session.get(f'{api}/actions/runs/{run_id}', timeout=30)
response.raise_for_status()
run = response.json()
if run['status'] != 'completed':
    print(json.dumps({k:run[k] for k in ['id','status','conclusion','html_url']}))
    raise SystemExit(0)
out = root / f'ci-{run_id}'
out.mkdir(exist_ok=False)
# Reuse the credential already authorized for this GitHub origin. Never log it.
env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')
credential = subprocess.run(['git','-c','credential.interactive=never','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,env=env,check=True)
fields = dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
session.headers['Authorization'] = 'Bearer ' + fields['password']
del fields, credential
items = []
def save(name, raw):
    path = out / name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(raw)
    items.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
def get(path):
    result = session.get(api + path, timeout=(15,120))
    result.raise_for_status()
    return result
save('run.json',json.dumps(run,indent=2).encode())
jobs = get(f'/actions/runs/{run_id}/jobs?per_page=100').json()
save('jobs.json',json.dumps(jobs,indent=2).encode())
for job in jobs['jobs']:
    if job['status']=='completed':
        save(f'jobs/{job["id"]}.log',get(f'/actions/jobs/{job["id"]}/logs').content)
artifacts = get(f'/actions/runs/{run_id}/artifacts?per_page=100').json()
save('artifacts.json',json.dumps(artifacts,indent=2).encode())
for item in artifacts['artifacts']:
    if item['size_in_bytes'] <= 1000000:
        save(f'artifacts/{item["id"]}.zip',get(f'/actions/artifacts/{item["id"]}/zip').content)
receipt = {'at':datetime.now(UTC).isoformat(),'run':run_id,'head':run['head_sha'],'conclusion':run['conclusion'],'url':run['html_url'],'files':items,'large_artifacts':'download separately through GitHub connector, then archive_ci verifies official digests'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'run':run_id,'head':run['head_sha'],'conclusion':run['conclusion'],'jobs':[{k:j[k] for k in ['id','name','conclusion']} for j in jobs['jobs']],'artifacts':len(artifacts['artifacts']),'bytes':sum(x['bytes'] for x in items)}))
