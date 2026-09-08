"""Run one review command with captured logs and an isolated Python environment."""
import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import time

WORK = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('name')
parser.add_argument('--timeout', type=int, default=1200)
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
env = dict(os.environ)
for key in list(env):
    if any(word in key.upper() for word in ('API_KEY', 'API_TOKEN', 'SECRET', 'ACCESS_TOKEN')) or key in (
        'SPORTS_DB_PATH','MARKET_DB_PATH','VORP_ARTIFACT_PATH','TITULARIDADE_PATH','RUNTIME_DIR',
        'PREDICTIONS_LOG_PATH','PERIOD_LOG_PATH','BRASILEIRAO_DB_PATH','PYTHONPATH','REDIS_URL'):
        env.pop(key, None)
env['PYTHONPATH'] = str(WORK/'guard') + os.pathsep + str(WORK/'repo')
env['PYTHONUTF8'] = '1'
env['COVERAGE_FILE'] = str(WORK/'.coverage')
env['NUMBA_CACHE_DIR'] = str(WORK/'numba_cache')
env['REDIS_URL'] = 'redis://127.0.0.1:16389/15'
env['PREDICTIONS_LOG_PATH'] = str(WORK/'smoke_predictions.jsonl')
env['PERIOD_LOG_PATH'] = str(WORK/'smoke_periods.jsonl')
command = args.command[1:] if args.command[:1] == ['--'] else args.command
start = time.monotonic()
receipt = {'name':args.name,'started_at_utc':datetime.now(UTC).isoformat(),
           'command':command,'cwd':str(WORK/'repo'),'live_data_used':False,
           'external_python_network_blocked':True,'credentials_removed':True}
with (WORK/f'{args.name}.log').open('w',encoding='utf-8') as log:
    try:
        process = subprocess.run(command,cwd=WORK/'repo',env=env,stdout=log,stderr=subprocess.STDOUT,
                                 timeout=args.timeout,check=False)
        receipt['exit_code'] = process.returncode
    except subprocess.TimeoutExpired:
        receipt['exit_code'] = 124
        receipt['timeout'] = True
receipt['seconds'] = time.monotonic()-start
(WORK/f'{args.name}.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt),flush=True)
print('\n'.join((WORK/f'{args.name}.log').read_text(encoding='utf-8',errors='replace').splitlines()[-14:]),flush=True)
raise SystemExit(receipt['exit_code'])
