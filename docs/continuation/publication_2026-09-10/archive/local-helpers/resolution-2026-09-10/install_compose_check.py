"""Two public release downloads; offline Compose validation, no daemon/startup."""
import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import requests

root = Path('C:/BRASILEIRAO/work/resolution-2026-09-10/compose-check')
root.mkdir(exist_ok=False)
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
receipt = {'purpose': 'validate current Compose model without Docker daemon or private .env',
           'budget': {'public_gets': 2, 'max_download_bytes': 80 * 1024 * 1024, 'paid_api_calls': 0},
           'official_instructions': 'https://docs.docker.com/compose/install/standalone/',
           'downloads': [], 'commands': []}
(root / 'plan.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
base = 'https://github.com/docker/compose/releases/download/v5.5.0/'
asset = 'docker-compose-windows-x86_64.exe'
session = requests.Session()
session.trust_env = False
try:
    for name, maximum in [(asset + '.sha256', 4096), (asset, 80 * 1024 * 1024)]:
        item = {'url': base + name, 'started_at': datetime.now(UTC).isoformat()}
        receipt['downloads'].append(item)
        with session.get(base + name, timeout=(10, 30), stream=True) as response:
            item['status_code'] = response.status_code
            response.raise_for_status()
            total = 0
            with (root / name).open('xb') as handle:
                for chunk in response.iter_content(128 * 1024):
                    total += len(chunk)
                    if total > maximum:
                        raise ValueError('declared_download_budget_exceeded')
                    handle.write(chunk)
        item.update(bytes=total, sha256=hashlib.sha256((root / name).read_bytes()).hexdigest())
    expected = (root / (asset + '.sha256')).read_text().split()[0]
    if receipt['downloads'][-1]['sha256'] != expected:
        raise ValueError('official_checksum_mismatch')
    shutil.copyfile(repo / 'compose.yaml', root / 'compose.yaml')
    (root / 'empty.env').write_text('', encoding='utf-8')
    env = {key: value for key, value in os.environ.items() if key.upper() in {'SYSTEMROOT', 'WINDIR', 'PATH', 'COMSPEC', 'PATHEXT'}}
    env.update(TEMP=str(root), TMP=str(root), USERPROFILE=str(root), DOCKER_CONFIG=str(root / 'docker-config'),
               COMPOSE_DISABLE_ENV_FILE='1', COMPOSE_PROJECT_NAME='brasileirao-resolution-synthetic')
    for label, arguments in [('version', ['version']), ('model', ['--env-file', str(root / 'empty.env'), '-f', str(root / 'compose.yaml'), 'config', '--no-env-resolution', '--no-interpolate', '--format', 'json'])]:
        command = [str(root / asset), *arguments]
        result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=60)
        (root / (label + '.stdout')).write_bytes(result.stdout)
        (root / (label + '.stderr')).write_bytes(result.stderr)
        receipt['commands'].append({'label': label, 'argv': command, 'exit_code': result.returncode})
        if result.returncode:
            raise RuntimeError('compose_validation_failed:' + label)
    model = json.loads((root / 'model.stdout').read_bytes())
    receipt.update(services=sorted(model['services']), daemon_started=False, containers_executed=False,
                   model_sha256=hashlib.sha256((root / 'model.stdout').read_bytes()).hexdigest())
finally:
    (root / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))
