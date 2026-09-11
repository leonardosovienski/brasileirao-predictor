"""Union of reviewed synthetic test scopes; no discovery of operational tests."""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
prior = Path('C:/BRASILEIRAO/work/completion-2026-09-10')
tests = set()
for path in [prior/'integrated-python-03/isolation.json', prior/'storage-final/isolation.json',
             root/'after/isolation.json', root/'supplemental-after/isolation.json']:
    tests.update(json.loads(path.read_text(encoding='utf-8'))['tests'])
tests = sorted(tests)
(root/'integration-test-scope.json').write_text(json.dumps(tests,indent=2),encoding='utf-8')
python = Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe')
raise SystemExit(subprocess.call([str(python),'-I','-B',str(root/'run_isolated.py'),'integrated-final',*tests]))
