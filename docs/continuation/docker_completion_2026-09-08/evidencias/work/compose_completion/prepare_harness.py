"""Prepare a new synthetic Compose harness without starting a daemon or container."""
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

import yaml

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent
LIVE = Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
ISOLATED = ROOT.parent / 'integration-repo'
OLD = ROOT.parent / 'pending_closure/compose_isolated'
STATE = WORKSPACE / 'outputs/PENDENCIAS_CORRIGIDAS/estado.json'
DEST = ROOT / 'harness'
ALLOW = {'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'COMSPEC', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA',
         'LOCALAPPDATA', 'PROGRAMDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432',
         'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS', 'OS', 'HOMEDRIVE', 'HOMEPATH'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    state = json.loads(STATE.read_text(encoding='utf-8'))
    compared = {}
    for name, expected in state['source_sha256'].items():
        live = sha(LIVE / name)
        isolated_path = ISOLATED / name
        isolated = sha(isolated_path) if isolated_path.is_file() else None
        documentation = name in state['documentation_only']
        if live != expected or (not documentation and isolated != expected):
            raise RuntimeError('source differs from final recorded state: ' + name)
        compared[name] = {'expected': expected, 'live': live, 'isolated': isolated, 'documentation_only': documentation}
    for name in ('pyproject.toml', 'uv.lock'):
        assert sha(LIVE / name) == sha(ISOLATED / name) == state['protected_sha256'][name]
    DEST.mkdir(exist_ok=False)
    fixtures = DEST / 'fixtures'
    fixtures.mkdir()
    for name in ('config.yaml', 'titularidade.json'):
        (fixtures / name).write_bytes((OLD / 'fixtures' / name).read_bytes())
    old_vorp = json.loads((OLD / 'fixtures/vorp.json').read_text(encoding='utf-8'))
    assert 'replacement_levels' not in old_vorp and 'replacement' in old_vorp
    corrected_vorp = {'beta_players': old_vorp['beta_players'], 'replacement_levels': old_vorp['replacement']}
    (fixtures / 'vorp.json').write_text(json.dumps(corrected_vorp, separators=(',', ':')) + '\n', encoding='utf-8')
    (DEST / 'empty.env').write_bytes(b'')
    docker_config = DEST / 'docker_config'
    docker_config.mkdir()
    (docker_config / 'config.json').write_text('{"auths":{}}\n', encoding='utf-8')
    compose = yaml.safe_load((OLD / 'compose.yaml').read_text(encoding='utf-8'))
    project = 'brasileirao-compose-final-' + uuid4().hex[:10]
    compose['name'] = project
    # One-off health probes must target the same heartbeat identity as the real Worker.
    compose['services']['worker']['hostname'] = project + '-worker'
    for service in compose['services'].values():
        if 'build' in service:
            service['build']['context'] = ISOLATED.as_posix()
        for mount in service.get('volumes', []):
            if not isinstance(mount, dict) or mount['type'] != 'bind':
                continue
            old_path = Path(mount['source'])
            assert old_path.resolve().is_relative_to((OLD / 'fixtures').resolve())
            mount['source'] = (fixtures / old_path.relative_to(OLD / 'fixtures')).as_posix()
            mount['bind'] = {'create_host_path': False}
    (DEST / 'compose.yaml').write_text(yaml.safe_dump(compose, sort_keys=False), encoding='utf-8')
    env = {key: value for key, value in os.environ.items() if key.upper() in ALLOW}
    cmd = ['docker.exe', '--config', str(docker_config), 'compose', '--project-name', project,
           '--project-directory', str(DEST), '--env-file', str(DEST / 'empty.env'), '--file', str(DEST / 'compose.yaml')]
    output = subprocess.run(cmd + ['config', '--format', 'json'], cwd=DEST, env=env,
                            capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    (DEST / 'config.stdout.json').write_bytes(output.stdout)
    (DEST / 'config.stderr.log').write_bytes(output.stderr)
    if output.returncode:
        raise RuntimeError('Compose parser rejected new harness')
    rendered = json.loads(output.stdout)
    assert rendered['name'] == project and rendered['networks']['default']['internal']
    for service in rendered['services'].values():
        assert not service.get('ports') and not service.get('privileged') and not service.get('network_mode')
        for mount in service.get('volumes', []):
            if mount['type'] == 'bind':
                assert Path(mount['source']).resolve().is_relative_to(fixtures.resolve())
                assert mount['read_only'] and mount.get('bind', {}).get('create_host_path', False) is False
    assert corrected_vorp.keys() == {'beta_players', 'replacement_levels'}
    hashes = {path.relative_to(DEST).as_posix(): sha(path) for path in DEST.rglob('*') if path.is_file()}
    result = {'at_utc': datetime.now(UTC).isoformat(), 'project_name': project, 'command_prefix': cmd,
              'state_path': str(STATE), 'state_sha256': sha(STATE), 'live_repo': str(LIVE), 'isolated_repo': str(ISOLATED),
              'source_comparison': compared, 'declared_source_count': len(compared),
              'runtime_and_test_sources_equal': True, 'configuration_parser_exit_code': output.returncode,
              'synthetic_vorp_fix': 'replacement -> replacement_levels required by VorpStateService.StartAsync',
              'old_harness_preserved': True, 'daemon_or_container_started': False,
              'hashes': hashes, 'handoff_sha256': sha(LIVE / 'HANDOFF.md')}
    (DEST / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('project_name', 'declared_source_count', 'runtime_and_test_sources_equal',
                                                 'configuration_parser_exit_code', 'synthetic_vorp_fix',
                                                 'old_harness_preserved', 'daemon_or_container_started')}, indent=2))


if __name__ == '__main__':
    main()
