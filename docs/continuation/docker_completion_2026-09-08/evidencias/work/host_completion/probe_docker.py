"""Read-only probes of the two local named pipes; no global Docker context changes."""
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
docker = 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
config = ROOT.parent / 'compose_completion/harness/docker_config'
assert json.loads((config / 'config.json').read_text()) == {'auths': {}}
env = {key: value for key, value in os.environ.items() if key.upper() in {
    'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'PATHEXT', 'PROGRAMFILES',
}}
records = []
for pipe in ['docker_engine', 'dockerDesktopLinuxEngine']:
    command = [docker, '--config', str(config), '--host', 'npipe:////./pipe/' + pipe,
               'version', '--format', 'json']
    record = {'started_at_utc': datetime.now(UTC).isoformat(), 'command': command,
              'read_only': True, 'daemon_started': False, 'local_endpoint_only': True}
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = process.communicate(timeout=8)
        record['timed_out'] = False
    except subprocess.TimeoutExpired:
        process.kill()
        out, err = process.communicate(timeout=3)
        record['timed_out'] = True
        record['own_probe_process_terminated'] = True
    record['exit_code'] = process.returncode
    record['stdout'] = out.decode('utf-8', errors='replace')
    record['stderr'] = err.decode('utf-8', errors='replace')
    record['finished_at_utc'] = datetime.now(UTC).isoformat()
    records.append(record)
(ROOT / 'docker_probes.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(records, ensure_ascii=False, indent=2))
