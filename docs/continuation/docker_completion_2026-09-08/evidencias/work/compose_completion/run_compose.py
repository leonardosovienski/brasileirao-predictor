"""Opt-in lifecycle test of a new, synthetic Compose project; no daemon startup."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'harness'
ALLOW = {'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'COMSPEC', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA',
         'LOCALAPPDATA', 'PROGRAMDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432',
         'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS', 'OS', 'HOMEDRIVE', 'HOMEPATH'}
ENGINES = ('npipe:////./pipe/docker_engine', 'npipe:////./pipe/dockerDesktopLinuxEngine')


def verify_sources(manifest):
    for name, expected in manifest['source_comparison'].items():
        for root in (manifest['live_repo'], manifest['isolated_repo']):
            if expected['documentation_only'] and root == manifest['isolated_repo']:
                continue
            digest = hashlib.sha256((Path(root) / name).read_bytes()).hexdigest()
            if digest != expected['expected']:
                raise RuntimeError('source changed since final validation: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'run'))
    parser.add_argument('--engine', choices=ENGINES, default=ENGINES[0])
    args = parser.parse_args()
    manifest = json.loads((ASSETS / 'manifest.json').read_text(encoding='utf-8'))
    verify_sources(manifest)
    for name, expected in manifest['hashes'].items():
        if hashlib.sha256((ASSETS / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('harness input changed: ' + name)
    suffix = uuid4().hex[:8]
    project = manifest['project_name'] + '-' + suffix
    docker = ['docker.exe', '--host', args.engine, '--config', str(ASSETS / 'docker_config')]
    compose = docker + ['compose', '--project-name', project, '--project-directory', str(ASSETS),
                        '--env-file', str(ASSETS / 'empty.env'), '--file', str(ASSETS / 'compose.yaml')]
    smoke = ['run', '--rm', '--no-deps', '--entrypoint', 'python', 'kernel', '-m',
             'brasileirao_scripts.hotpath_smoke', '--synthetic-lineup', '--n']
    sequence = [compose + ['config', '--quiet'], compose + ['build', '--pull'],
                compose + ['up', '--detach', '--wait', '--wait-timeout', '180'], compose + smoke + ['3'],
                compose + ['stop', 'redis'], compose + ['start', 'redis'], compose + smoke + ['1'],
                compose + ['restart', '--timeout', '20', 'worker', 'kernel'], compose + smoke + ['1']]
    for service in ('worker', 'kernel'):
        sequence += [compose + ['run', '--rm', '--no-deps', service, '--healthcheck'],
                     compose + ['kill', '--signal', 'SIGKILL', service],
                     compose + ['run', '--rm', '--no-deps', service, '--healthcheck'],
                     compose + ['start', service]]
    sequence += [compose + smoke + ['1'], compose + ['stop', '--timeout', '20', 'worker', 'kernel'],
                 compose + ['logs', '--no-color'], compose + ['down', '--volumes', '--remove-orphans']]
    if args.action == 'plan':
        print(json.dumps({'status': 'PLAN_ONLY', 'commands': sequence, 'container_runtime_executed': False,
                          'additional_checks': 'Unique project inventory; daemon Server; health polling; stopped services exit0; scoped cleanup inventory; hashes.'}, indent=2))
        return 0
    receipts = ROOT / 'runs' / (datetime.now(UTC).strftime('%Y%m%dT%H%M%S') + '_' + suffix)
    receipts.mkdir(parents=True, exist_ok=False)
    env = {key: value for key, value in os.environ.items() if key.upper() in ALLOW}
    state = {'started_at_utc': datetime.now(UTC).isoformat(), 'project': project, 'engine': args.engine,
             'status': 'RUNNING', 'synthetic_only': True, 'existing_resources_modified': False,
             'container_runtime_attempted': False, 'container_runtime_executed': False,
             'cleanup_complete': False, 'commands': []}
    owned = False

    def run(command, *, allowed=(0,), timeout=90):
        index = len(state['commands'])
        log_path = receipts / f'{index:03d}.log'
        entry = {'command': command, 'started_at_utc': datetime.now(UTC).isoformat()}
        state['commands'].append(entry)
        print(json.dumps({'step': index, 'command': command}), flush=True)
        with log_path.open('xb') as stream:
            process = subprocess.Popen(command, cwd=ASSETS, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            entry['owned_process_id'] = process.pid
            try:
                entry['exit_code'] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                entry['exit_code'] = 124
                entry['timed_out'] = True
                # The PID comes only from this Popen. Never select a process by
                # name or kill Docker/Desktop globally. Poll before acting so
                # a process that has already exited cannot become a stale PID.
                if process.poll() is None:
                    kill_command = ['taskkill.exe', '/PID', str(process.pid), '/T', '/F']
                    entry['owned_tree_stop_command'] = kill_command
                    try:
                        stopped = subprocess.run(kill_command, env=env, capture_output=True, timeout=15,
                                                 creationflags=subprocess.CREATE_NO_WINDOW)
                        entry['owned_tree_stop_exit_code'] = stopped.returncode
                        entry['owned_tree_stop_output'] = (stopped.stdout + stopped.stderr).decode('utf-8', errors='replace')
                    except subprocess.TimeoutExpired:
                        entry['owned_tree_stop_exit_code'] = 124
                    try:
                        entry['owned_process_final_exit_code'] = process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        entry['owned_process_still_running'] = True
                else:
                    entry['owned_process_final_exit_code'] = process.returncode
        text = log_path.read_text(encoding='utf-8', errors='replace')
        (receipts / f'{index:03d}.json').write_text(json.dumps(entry, indent=2), encoding='utf-8')
        if entry['exit_code'] not in allowed:
            raise RuntimeError(f'step {index} failed with {entry["exit_code"]}; see {log_path}')
        return entry['exit_code'], text.strip()

    def inventory():
        label = 'label=com.docker.compose.project=' + project
        return [run(docker + kind + ['--quiet', '--filter', label])[1]
                for kind in (['ps', '--all'], ['volume', 'ls'], ['network', 'ls'])]

    def ids(service):
        result = run(compose + ['ps', '--all', '--quiet', service])[1]
        if not result or '\n' in result:
            raise RuntimeError('expected one owned service container: ' + service)
        return result

    def inspect(service):
        return json.loads(run(docker + ['inspect', ids(service)])[1])[0]

    def health(service, expected=0, one_off=False, deadline_seconds=75):
        deadline = time.monotonic() + deadline_seconds
        command = compose + (['run', '--rm', '--no-deps', service, '--healthcheck'] if one_off else
                             ['exec', '-T', service] + (['dotnet', 'LineupWorker.dll'] if service == 'worker' else ['brasileirao-kernel']) + ['--healthcheck'])
        while True:
            code, _ = run(command, allowed=(0, 1), timeout=20)
            if code == expected:
                return
            if time.monotonic() >= deadline:
                raise RuntimeError('health deadline exceeded: ' + service)
            time.sleep(1)

    try:
        server = json.loads(run(docker + ['version', '--format', 'json'], timeout=25)[1])
        if not server.get('Server'):
            raise RuntimeError('Docker Server unavailable; no resources created')
        if server['Server'].get('Os', '').lower() != 'linux':
            raise RuntimeError('Docker Server must report Os=linux; no resources created')
        if any(inventory()):
            raise RuntimeError('random project name already has resources; refusing reuse')
        run(compose + ['config', '--quiet'])
        owned = True
        run(compose + ['build', '--pull'], timeout=1200)
        state['container_runtime_attempted'] = True
        run(compose + ['up', '--detach', '--wait', '--wait-timeout', '180'], timeout=210)
        state['container_runtime_executed'] = True
        run(compose + smoke + ['3'])
        run(compose + ['stop', 'redis'])
        for service in ('worker', 'kernel'):
            if inspect(service)['State']['Status'] != 'running':
                raise RuntimeError('consumer exited when Redis stopped: ' + service)
            health(service, expected=1, deadline_seconds=15)
        run(compose + ['start', 'redis'])
        for service in ('worker', 'kernel'):
            health(service)
        run(compose + smoke + ['1'])
        run(compose + ['restart', '--timeout', '20', 'worker', 'kernel'])
        for service in ('worker', 'kernel'):
            health(service)
        run(compose + smoke + ['1'])
        for service in ('worker', 'kernel'):
            # Positive control prevents a mismatched one-off hostname from faking a negative result.
            health(service, one_off=True)
            run(compose + ['kill', '--signal', 'SIGKILL', service])
            health(service, expected=1, one_off=True, deadline_seconds=20)
            run(compose + ['start', service])
            health(service)
        run(compose + smoke + ['1'])
        run(compose + ['stop', '--timeout', '20', 'worker', 'kernel'])
        for service in ('worker', 'kernel'):
            if inspect(service)['State']['ExitCode'] != 0:
                raise RuntimeError('nonzero graceful shutdown: ' + service)
        verify_sources(manifest)
        state['status'] = 'PASS_PENDING_CLEANUP'
    except Exception as exc:
        state['status'], state['error'] = 'FAILED', str(exc)
    finally:
        if owned:
            try:
                run(compose + ['logs', '--no-color'])
            except Exception as exc:
                state['logs_error'] = str(exc)
            try:
                run(compose + ['down', '--volumes', '--remove-orphans'])
                state['cleanup_complete'] = not any(inventory())
            except Exception as exc:
                state['cleanup_error'] = str(exc)
        if state['status'] == 'PASS_PENDING_CLEANUP':
            state['status'] = 'PASS' if state['cleanup_complete'] else 'FAILED_CLEANUP'
        state['finished_at_utc'] = datetime.now(UTC).isoformat()
        with (receipts / 'result.json').open('x', encoding='utf-8') as stream:
            json.dump(state, stream, indent=2)
        print(json.dumps({'status': state['status'], 'receipt': str(receipts / 'result.json')}, indent=2))
    return 0 if state['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
