"""Exercise denial before operations, using no operational input contents."""

import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent / 'guard-boundaries'
root.mkdir(exist_ok=False)
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
env = {k: v for k, v in os.environ.items() if k.upper() in {'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT'}}
env.update(BRASILEIRAO_LAB_REPO=str(repo), BRASILEIRAO_LAB_OUTPUT=str(root), PYTHONPATH=str(repo/'tools/runtime_lab'), PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', TEMP=str(root), TMP=str(root))
cases = {
    'foreign_redis': "import socket; socket.create_connection(('127.0.0.1',6379),timeout=1)",
    'external_network': "import socket; socket.create_connection(('192.0.2.1',80),timeout=1)",
    'protected_file': "open('C:/BRASILEIRAO/DADOS_PRESERVADOS/lab_never_read.json','rb')",
    'external_write': "open('C:/BRASILEIRAO/brasileirao-predictor/lab_never_written.txt','w')",
    'external_sqlite': "import sqlite3; sqlite3.connect('C:/BRASILEIRAO/brasileirao-predictor/lab_never_created.db')",
    'subprocess': "import subprocess; subprocess.run(['whoami'])",
}
results = []
for name, code in cases.items():
    result = subprocess.run([sys.executable, '-c', code], env=env, cwd=root, capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode != 0 and b'PermissionError: lab_' in result.stderr, (name, result.returncode, result.stderr)
    results.append({'case': name, 'exit_code': result.returncode, 'denied_before_operation': True})
bad_env = {k:v for k,v in env.items() if k != 'BRASILEIRAO_LAB_OUTPUT'}
result = subprocess.run([sys.executable, '-c', "print('MUST_NOT_RUN')"], env=bad_env, cwd=root, capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode == 70 and not result.stdout
results.append({'case': 'guard_startup_failure', 'exit_code': 70, 'denied_before_operation': True})
(root/'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print(json.dumps({'passed':len(results)}))
