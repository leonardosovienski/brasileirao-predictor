"""Finish offline validation of the new harness; never starts Docker services."""
from datetime import UTC, datetime
import hashlib
import json
import math
import os
import re
import subprocess

import yaml

from prepare_harness import ALLOW, DEST, ISOLATED, LIVE, ROOT, STATE, sha


def main():
    state = json.loads(STATE.read_text(encoding='utf-8'))
    source_comparison = {}
    for name, expected in state['source_sha256'].items():
        live = sha(LIVE / name)
        isolated_path = ISOLATED / name
        isolated = sha(isolated_path) if isolated_path.is_file() else None
        document = name in state['documentation_only']
        assert live == expected and (document or isolated == expected), name
        source_comparison[name] = {'expected': expected, 'live': live, 'isolated': isolated, 'documentation_only': document}
    for name in ('pyproject.toml', 'uv.lock'):
        assert sha(LIVE / name) == sha(ISOLATED / name) == state['protected_sha256'][name]
    compose_path = DEST / 'compose.yaml'
    compose = yaml.safe_load(compose_path.read_text(encoding='utf-8'))
    project = compose['name']
    env = {key: value for key, value in os.environ.items() if key.upper() in ALLOW}
    cmd = ['docker.exe', '--config', str(DEST / 'docker_config'), 'compose', '--project-name', project,
           '--project-directory', str(DEST), '--env-file', str(DEST / 'empty.env'), '--file', str(compose_path)]
    output = subprocess.run(cmd + ['config', '--format', 'json'], cwd=DEST, env=env, capture_output=True,
                            timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    with (DEST / 'config_final.stdout.json').open('xb') as stream:
        stream.write(output.stdout)
    with (DEST / 'config_final.stderr.log').open('xb') as stream:
        stream.write(output.stderr)
    assert output.returncode == 0
    rendered = json.loads(output.stdout)
    assert rendered['name'] == project and rendered['networks']['default']['internal']
    for name, service in rendered['services'].items():
        assert not service.get('ports') and not service.get('privileged') and not service.get('network_mode')
        if 'build' in service:
            assert service['build']['context'].replace('\\', '/') == ISOLATED.as_posix()
        for mount in service.get('volumes', []):
            if mount['type'] == 'bind':
                assert __import__('pathlib').Path(mount['source']).resolve().is_relative_to((DEST / 'fixtures').resolve())
                assert mount['read_only'] and mount.get('bind', {}).get('create_host_path', False) is False
    for volume in rendered['volumes'].values():
        assert not volume.get('external') and volume['name'].startswith(project + '_')
    vorp_source = (ISOLATED / 'dotnet/LineupWorker/Services/VorpStateService.cs').read_text(encoding='utf-8')
    required_fields = re.findall(r'root.GetProperty\("([^\"]+)"\)', vorp_source)
    vorp = json.loads((DEST / 'fixtures/vorp.json').read_text(encoding='utf-8'))
    assert set(required_fields) <= vorp.keys()
    for field in required_fields:
        assert isinstance(vorp[field], dict)
        assert all(type(value) in (int, float) and math.isfinite(value) for value in vorp[field].values())
    scratch = DEST / 'synthetic_db_check'
    scratch.mkdir(exist_ok=False)
    guarded_env = dict(env)
    guarded_env.update({'PYTHONPATH': str(ROOT.parent / 'guard') + os.pathsep + str(ISOLATED),
                        'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                        'SPORTS_DB_PATH': str(scratch / 'sports.db'), 'MARKET_DB_PATH': str(scratch / 'market.db'),
                        'BRASILEIRAO_CONFIG_PATH': str(DEST / 'fixtures/config.yaml'),
                        'KERNEL_VORP_THETA': '0.0', 'KERNEL_MAX_GOALS': '12',
                        'NUMBA_CACHE_DIR': str(scratch / 'numba_cache')})
    code = '''import json, os
from brasileirao_scripts.init_compose_data import main
assert main() == 0
from brasileirao_predictor.kernel_daemon import _load_params
from brasileirao_predictor import db
params = _load_params(os.environ["SPORTS_DB_PATH"])
assert params == (0.2, 1.0, 0.1, 0.0, 0.0, 12), params
for path in (os.environ["SPORTS_DB_PATH"], os.environ["MARKET_DB_PATH"]):
    con = db.connect(path, read_only=True)
    assert con.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 0
    con.close()
print(json.dumps({"status":"PASS","synthetic_params":params,"real_match_rows":0,"fit_or_backtest":False}))
'''
    args = [str(LIVE / '.venv/Scripts/python.exe'), '-X', 'utf8', '-c', code]
    result = subprocess.run(args, cwd=ISOLATED, env=guarded_env, capture_output=True, timeout=30,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    with (scratch / 'check.stdout.log').open('xb') as stream:
        stream.write(result.stdout)
    with (scratch / 'check.stderr.log').open('xb') as stream:
        stream.write(result.stderr)
    receipt = {'at_utc': datetime.now(UTC).isoformat(), 'command': args, 'cwd': str(ISOLATED),
               'exit_code': result.returncode, 'environment_allowlist': True, 'external_network_guard': True,
               'only_new_synthetic_databases': True, 'operational_data_access': False, 'fit_or_backtest': False}
    (scratch / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    if result.returncode:
        raise RuntimeError('synthetic init/load check failed; inspect new receipt')
    hashes = {path.relative_to(DEST).as_posix(): sha(path) for path in DEST.rglob('*') if path.is_file()}
    final = {'at_utc': datetime.now(UTC).isoformat(), 'project_name': project, 'command_prefix': cmd,
             'state_path': str(STATE), 'state_sha256': sha(STATE), 'live_repo': str(LIVE), 'isolated_repo': str(ISOLATED),
             'source_comparison': source_comparison, 'declared_source_count': len(source_comparison),
             'runtime_and_test_sources_equal': True, 'configuration_parser_exit_code': output.returncode,
             'synthetic_fixture_contract_passed': True, 'synthetic_init_and_cache_read_passed': True,
             'synthetic_vorp_fix': 'replacement -> replacement_levels required by VorpStateService.StartAsync',
             'initial_harness_check': 'Parser exited 0; post-check incorrectly required explicit false in normalized bind object. Fixed default handling; prior files retained.',
             'old_harness_preserved': True, 'daemon_or_container_started': False, 'hashes': hashes,
             'handoff_sha256': sha(LIVE / 'HANDOFF.md')}
    with (DEST / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(final, stream, indent=2)
    print(json.dumps({key: final[key] for key in ('project_name', 'declared_source_count', 'runtime_and_test_sources_equal',
                                                 'configuration_parser_exit_code', 'synthetic_fixture_contract_passed',
                                                 'synthetic_init_and_cache_read_passed', 'daemon_or_container_started')}, indent=2))


if __name__ == '__main__':
    main()
