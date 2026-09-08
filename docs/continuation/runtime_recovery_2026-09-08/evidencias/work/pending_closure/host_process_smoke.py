"""Exercise actual .NET host startup, stream smoke and crash liveness in owned DB13."""
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import redis

ROOT = Path(__file__).resolve().parents[2]
CHECKOUT = ROOT / 'work/integration-repo'
HERE = ROOT / 'work/pending_closure' / ('host_process_evidence_' + datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f'))
HERE.mkdir(exist_ok=False)
url = os.environ['REDIS_URL']
assert url == 'redis://127.0.0.1:26380/13'
client = redis.from_url(url, decode_responses=True)
run_id = os.environ['LINEUP_TEST_REDIS_RUN_ID']
assert client.info('server')['run_id'] == run_id
assert client.dbsize() == 0, 'DB13 must be empty before this exclusive test'
worker_dll = CHECKOUT / 'dotnet/LineupWorker/bin/Release/net10.0/LineupWorker.dll'
assert worker_dll.is_file()
assert (worker_dll.parent / 'appsettings.json').is_file()
fixture = HERE / 'vorp.json'
fixture.write_text('{"beta_players":{},"replacement_levels":{"UNKNOWN":0}}', encoding='utf-8')
tit = HERE / 'titularidade.json'
tit.write_text('{}', encoding='utf-8')
env = dict(os.environ)
env.update({'VORP_ARTIFACT_PATH': str(fixture), 'TITULARIDADE_PATH': str(tit),
            'LINEUP_Exchange__WebSocketUrl': 'ws://127.0.0.1:9', 'LINEUP_Exchange__ApiKey': '',
            'LINEUP_E2E_REDIS_URL': url, 'LINEUP_E2E_REDIS_RUN_ID': run_id})
processes = []
handles = []
results = {'started_at_utc': datetime.now(UTC).isoformat(), 'run_id': run_id,
           'synthetic_data_only': True, 'actual_dotnet_program': True,
           'kernel_parameter_loader_only_is_synthetic': True, 'checks': []}


def spawn(command, name, cwd):
    handle = (HERE / (name + '.log')).open('x', encoding='utf-8')
    handles.append(handle)
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    processes.append(process)
    return process


def check(command, name, expected, cwd):
    with (HERE / (name + '.log')).open('x', encoding='utf-8') as handle:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        processes.append(process)
        exit_code = process.wait(timeout=20)
    results['checks'].append({'name': name, 'command': command, 'exit_code': exit_code, 'expected': expected})
    assert exit_code == expected, name


def stop(process):
    if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


try:
    check(['dotnet', str(worker_dll), '--healthcheck'], 'worker_absent', 1, worker_dll.parent)
    kernel = spawn([sys.executable, str(ROOT / 'work/runtime_fix/synthetic_kernel_process.py')], 'kernel', CHECKOUT)
    worker = spawn(['dotnet', str(worker_dll)], 'worker', worker_dll.parent)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        assert worker.poll() is None and kernel.poll() is None, 'A real host stopped during startup'
        health = list(client.scan_iter('system:lineup_worker:health:*'))
        if len(health) == 2 and all(client.pttl(key) > 0 for key in health) and client.pttl('health:kernel') > 0:
            break
        time.sleep(.1)
    else: raise AssertionError('The real Worker did not report both active loops')
    check(['dotnet', str(worker_dll), '--healthcheck'], 'worker_running', 0, worker_dll.parent)
    check([sys.executable, '-m', 'brasileirao_predictor.kernel_daemon', '--healthcheck'], 'kernel_running', 0, CHECKOUT)
    check([sys.executable, '-m', 'brasileirao_scripts.hotpath_smoke', '--synthetic-lineup', '--n', '2', '--redis', url],
          'stream_smoke', 0, CHECKOUT)
    stop(worker)
    stop(kernel)
    health.append('health:kernel')
    deadline = time.monotonic() + 7
    while any(client.exists(key) for key in health) and time.monotonic() < deadline:
        time.sleep(.1)
    assert not any(client.exists(key) for key in health), 'Heartbeat remained after its bounded crash window'
    check(['dotnet', str(worker_dll), '--healthcheck'], 'worker_crashed', 1, worker_dll.parent)
    check([sys.executable, '-m', 'brasileirao_predictor.kernel_daemon', '--healthcheck'], 'kernel_crashed', 1, CHECKOUT)
    results['status'] = 'PASS'
finally:
    for process in reversed(processes): stop(process)
    for handle in handles: handle.close()
    assert client.info('server')['run_id'] == run_id, 'Cleanup refused on another Redis process'
    # This DB was empty at entry and exclusive to this fixture; no global flush.
    owned = list(client.scan_iter())
    results['owned_keys_cleaned'] = len(owned)
    if owned: client.delete(*owned)
    results['dbsize_after'] = client.dbsize()
    results['finished_at_utc'] = datetime.now(UTC).isoformat()
    (HERE / 'receipt.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    client.close()
print(json.dumps(results, indent=2))
