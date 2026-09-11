"""Inspect and smoke-test only the built wheel in a new, offline directory."""
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
wheel = root / 'dist-final/brasileirao_predictor-0.1.0-py3-none-any.whl'
out = root / 'package-smoke-final'
out.mkdir(exist_ok=False)
sys.dont_write_bytecode = True
for key in list(os.environ):
    if key.upper() not in {'SYSTEMROOT', 'WINDIR', 'PATH', 'COMSPEC', 'PATHEXT'}:
        del os.environ[key]
os.environ.update(TEMP=str(out), TMP=str(out))
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    forbidden = [name for name in names if Path(name).suffix in {'.db', '.sqlite3'} or Path(name).name == '.env']
    assert not forbidden, forbidden
    for changed in ['backtest_event.py','simulator.py','temporal_policy.py','research/price_strength/live_capture_admission.py']:
        name='brasileirao_predictor/'+changed
        assert archive.read(name)==(Path('C:/BRASILEIRAO/brasileirao-predictor')/name).read_bytes(), name
    for name in names:
        assert (out / name).resolve().is_relative_to(out)
    archive.extractall(out)
sys.path.insert(0, str(out))
os.chdir(out)

def guard(event, args):
    if event.startswith(('socket.connect', 'socket.getaddrinfo', 'sqlite3.', 'subprocess.', 'os.system')):
        raise PermissionError('package_smoke_no_network_or_database')
    if event == 'open' and isinstance(args[0], str | bytes | os.PathLike):
        path = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1] or '', args[2] or 0
        if (any(c in mode for c in 'wax+') or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)) and not path.is_relative_to(out):
            raise PermissionError('package_smoke_write_outside_output')
        if path.name == '.env' or path.is_relative_to(Path('C:/BRASILEIRAO/DADOS_PRESERVADOS')):
            raise PermissionError('package_smoke_private_data')

sys.addaudithook(guard)
from brasileirao_predictor import predict
assert Path(predict.__file__).is_relative_to(out)
sys.argv = ['brasileirao-predict', '--help']
try:
    predict.main()
except SystemExit as exc:
    assert exc.code == 0, exc.code
(out / 'receipt.json').write_text(json.dumps({
    'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
    'members': len(names), 'operational_data_members': forbidden,
    'imported_from': predict.__file__, 'entry_point_help_exit': 0,
    'functional_predictions_not_executed': True,
}, indent=2), encoding='utf-8')
