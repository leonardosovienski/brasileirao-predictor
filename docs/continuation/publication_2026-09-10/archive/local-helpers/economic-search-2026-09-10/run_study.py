"""Run only the frozen BE source/code, without credentials or external IO."""
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('C:/BRASILEIRAO/brasileirao-predictor')
SOURCE = Path('C:/BRASILEIRAO/work/data-completion-2026-09-09/public_sources/football_data_bra_origin_csv.csv').resolve()
PROTOCOL = (REPO / 'docs/continuation/economic_search_2026-09-10/PROTOCOL.md').resolve()
CODE = (REPO / 'brasileirao_predictor/research/price_strength/economic_search.py').resolve()
run_name = sys.argv[1]
out = (ROOT / run_name).resolve()
if not out.is_relative_to(ROOT) or out == ROOT or out.exists():
    raise ValueError('new isolated output required')
for key in list(os.environ):
    if key.upper() not in {'SYSTEMROOT', 'WINDIR', 'PATH', 'COMSPEC', 'PATHEXT'}:
        del os.environ[key]
os.environ.update(TEMP=str(ROOT), TMP=str(ROOT))
sys.dont_write_bytecode = True
os.chdir(ROOT)
libraries = [Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()]
blocked = []

def guard(event, args):
    if event.startswith(('socket.', 'subprocess.', 'os.system', 'os.exec', 'os.spawn', 'sqlite3.connect')):
        blocked.append(event)
        raise PermissionError('offline study: network/process/database forbidden')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        p = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1] or '', args[2] or 0
        writing = any(c in mode for c in 'wax+') or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)
        if writing:
            allowed = p.is_relative_to(out) or p == ROOT / (run_name + '-isolation.json')
        else:
            allowed = p in {SOURCE, PROTOCOL, CODE} or p.is_relative_to(out) or any(p.is_relative_to(x) for x in libraries)
        if not allowed:
            blocked.append(event)
            raise PermissionError('path outside explicit study scope')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename', 'os.chmod'}:
        for value in args[:2] if event == 'os.rename' else args[:1]:
            if not Path(os.fsdecode(value)).resolve().is_relative_to(out):
                blocked.append(event)
                raise PermissionError('mutation outside study output')

sys.addaudithook(guard)
spec = importlib.util.spec_from_file_location('be_study', CODE)
module = importlib.util.module_from_spec(spec)
sys.modules['be_study'] = module
spec.loader.exec_module(module)
sys.argv = [str(CODE), '--source', str(SOURCE), '--protocol', str(PROTOCOL), '--output-dir', str(out)]
try:
    module.main()
finally:
    with (ROOT / (run_name + '-isolation.json')).open('x', encoding='utf-8') as f:
        json.dump({'blocked_attempts': blocked, 'source': str(SOURCE), 'output': str(out),
                   'credentials_removed': True, 'protected_content_read': False}, f, indent=2)
