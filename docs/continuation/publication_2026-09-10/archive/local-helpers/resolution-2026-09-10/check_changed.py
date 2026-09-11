"""Quality checks for explicit changed public Python files, no operational imports."""
import json
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
ri = Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09')
changed = subprocess.check_output(['git', 'diff', '--name-only'], cwd=repo, text=True).splitlines()
new = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=repo, text=True).splitlines()
files = sorted({p for p in changed + new if p.endswith('.py')})
assert files and all(p.startswith(('brasileirao_predictor/', 'brasileirao_scripts/', 'tests/', 'tools/runtime_lab/')) for p in files)
env = {k: v for k, v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT'}}
for k in ('TEMP', 'TMP', 'RUFF_CACHE_DIR', 'NODE_COMPILE_CACHE'):
    path = root / k.lower()
    path.mkdir(exist_ok=True)
    env[k] = str(path)
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['PYTHONUTF8'] = '1'
ruff = str(ri / 'venv/Scripts/ruff.exe')
commands = [
    ('ruff-fix', [ruff, 'check', '--fix', *files]),
    ('ruff-format', [ruff, 'format', *files]),
    ('ruff-check', [ruff, 'check', *files]),
    ('ruff-format-check', [ruff, 'format', '--check', *files]),
]
config = dict(extraPaths=['../../brasileirao-predictor','../../brasileirao-predictor/tests','../../brasileirao-predictor/tools/runtime_lab'],
              pythonVersion='3.13', typeCheckingMode='basic', include=['../../brasileirao-predictor/'+p for p in files])
(root/'pyright.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
commands.append(('pyright', [str(ri/'tools/node.exe'), str(ri/'venv/Lib/site-packages/pyright/dist/index.js'),
                 '--pythonpath', str(ri/'venv/Scripts/python.exe'), '--project', str(root/'pyright.json')]))
results=[]
for name, argv in commands:
    result=subprocess.run(argv,cwd=repo,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (root/(name+'-final.log')).write_bytes(result.stdout)
    print(name, result.returncode, result.stdout.decode('utf-8', errors='replace')[-5000:], flush=True)
    results.append(dict(name=name,argv=argv,exit_code=result.returncode))
(root/'quality-checks-final.json').write_text(json.dumps(dict(files=files,commands=results),indent=2),encoding='utf-8')
raise SystemExit(any(row['exit_code'] != 0 for row in results if row['name'] in {'ruff-check','ruff-format-check','pyright'}))
