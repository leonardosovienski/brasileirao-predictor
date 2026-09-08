"""Prepare a fresh synthetic Compose project and validate config/locked exports only."""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time

import yaml

from probe_environment import ENV

ROOT = Path(__file__).resolve().parent
REPO = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
WORKTREE = ROOT.parent / 'integration-repo'
DEST = ROOT / 'compose_isolated'
PROJECT = 'brasileirao-pending-20260908-0418'
PYTHON = REPO / '.venv/Scripts/python.exe'
UV = Path('C:/Users/Superleo13/.local/bin/uv.exe')
OWNED = ('Dockerfile.worker', 'Dockerfile.kernel', 'Dockerfile.cli', '.dockerignore', '.github/workflows/ci.yml')


def run(name, command):
    started = time.monotonic()
    result = subprocess.run(command, cwd=WORKTREE, env=ENV, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
    text = result.stdout.decode('utf-8', errors='replace')
    receipt = {'at_utc': datetime.now(UTC).isoformat(), 'command': [str(x) for x in command],
               'cwd': str(WORKTREE), 'environment_allowlist': True, 'exit_code': result.returncode,
               'seconds': time.monotonic() - started, 'operational_data_used': False,
               'docker_build_or_run': False}
    with (DEST / (name + '.log')).open('x', encoding='utf-8') as stream:
        stream.write(text)
    with (DEST / (name + '.json')).open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt), flush=True)
    if result.returncode:
        print(text[-3000:], flush=True)
        raise RuntimeError(name + ' failed')
    return text


def main():
    DEST.mkdir(exist_ok=False)
    config = {'elo': {'initial_rating': 1500, 'k': 20, 'home_advantage': 0},
              'model': {'calibration_window_years': 3, 'goal_half_life_days': 365},
              'ensemble_xg': {'enabled': False}}
    fixtures = DEST / 'fixtures'
    fixtures.mkdir()
    (fixtures / 'config.yaml').write_text(yaml.safe_dump(config), encoding='utf-8')
    (fixtures / 'vorp.json').write_text('{"beta_players":{},"replacement":{"UNKNOWN":0.0}}\n', encoding='utf-8')
    (fixtures / 'titularidade.json').write_text('{}\n', encoding='utf-8')
    (DEST / 'empty.env').write_text('', encoding='utf-8')
    compose = yaml.safe_load((REPO / 'compose.yaml').read_text(encoding='utf-8'))
    compose['name'] = PROJECT
    compose['networks'] = {'default': {'internal': True}}
    for name, service in compose['services'].items():
        if 'build' in service:
            service['build']['context'] = WORKTREE.as_posix()
        if name == 'redis':
            continue
        service['environment'] = dict(service['environment'])
        if name == 'worker':
            service['environment']['LINEUP_Exchange__WebSocketUrl'] = 'ws://127.0.0.1:9'
            service['environment']['LINEUP_Exchange__ApiKey'] = ''
        mounts = [{'type': 'volume', 'source': 'app-data', 'target': '/app/data', 'read_only': name != 'init-data'},
                  {'type': 'bind', 'source': (fixtures / 'config.yaml').as_posix(), 'target': '/app/config.yaml', 'read_only': True}]
        if name == 'worker':
            mounts.append({'type': 'bind', 'source': fixtures.as_posix(), 'target': '/app/config', 'read_only': True})
        service['volumes'] = mounts
    compose_path = DEST / 'compose.yaml'
    compose_path.write_text(yaml.safe_dump(compose, sort_keys=False), encoding='utf-8')
    hashes = {}
    for name in OWNED:
        data = (REPO / name).read_bytes()
        (WORKTREE / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    lock_before = hashlib.sha256((WORKTREE / 'uv.lock').read_bytes()).hexdigest()
    base = [str(UV), 'export', '--locked', '--offline', '--no-python-downloads', '--python', str(PYTHON),
            '--no-dev', '--no-emit-project', '--format', 'requirements.txt']
    for name, extra in [('cli', []), ('kernel', ['--extra', 'kernel'])]:
        run('uv_export_' + name, base + extra + ['--output-file', str(DEST / (name + '.requirements.lock'))])
    assert hashlib.sha256((WORKTREE / 'uv.lock').read_bytes()).hexdigest() == lock_before
    cmd = ['docker.exe', 'compose', '--project-name', PROJECT, '--project-directory', str(DEST),
           '--env-file', str(DEST / 'empty.env'), '--file', str(compose_path)]
    rendered = json.loads(run('compose_config', cmd + ['config', '--format', 'json']))
    assert rendered['name'] == PROJECT
    assert rendered['networks']['default']['internal'] is True
    for service in rendered['services'].values():
        assert not service.get('ports')
        for mount in service.get('volumes', []):
            if mount['type'] == 'bind':
                assert Path(mount['source']).resolve().is_relative_to(fixtures.resolve())
    for volume in rendered['volumes'].values():
        assert not volume.get('external') and volume['name'].startswith(PROJECT + '_')
    for path in DEST.rglob('*'):
        if path.is_file():
            hashes[str(path.relative_to(DEST))] = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {'at_utc': datetime.now(UTC).isoformat(), 'project_name': PROJECT, 'command_prefix': cmd,
               'synthetic_fixtures_only': True, 'external_runtime_network': False,
               'existing_volumes_or_services_used': False, 'config_validated': True,
               'locked_exports_validated': True, 'lock_unchanged_sha256': lock_before,
               'compose_build_run_executed': False, 'hashes': hashes}
    with (DEST / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == '__main__':
    main()
