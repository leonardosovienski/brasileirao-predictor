"""Verify all three research modules explicitly despite the runtime exclusion."""
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent
node = Path('C:/Users/leona/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
cli = Path('C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv/Lib/site-packages/pyright/dist/index.js')
env = {k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC','PATHEXT'}}
started = datetime.now(UTC).isoformat()
result = subprocess.run([str(node),str(cli),'--project',str(root/'pyrightconfig.json'),'--verbose','--stats'],
                        cwd=root,env=env,capture_output=True,text=True,timeout=60)
output = result.stdout+'\n'+result.stderr
log = root/'engineering-02/pyright_explicit_config.txt'
log.write_text(output,encoding='utf-8')
print(output)
assert result.returncode==0 and 'Found 3 source files' in output and 'Total files checked: 3' in output
assert '0 errors, 0 warnings' in output
path = root/'engineering_checks.json'
receipt = json.loads(path.read_text(encoding='utf-8'))
receipt['checks'].append({'name':'pyright_explicit_three_modules','returncode':0,'started_at':started,
                          'finished_at':datetime.now(UTC).isoformat(),'log':str(log),
                          'configuration':str(root/'pyrightconfig.json'),'files_checked':3})
receipt['typecheck_configuration_note'] = 'Explicit research includes and existing venv; runtime project excludes research.'
path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
