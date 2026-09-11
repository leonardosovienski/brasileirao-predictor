"""Validate the built package without an operational DB, Redis or HTTP client."""

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
wheel = root/'dist-final/brasileirao_predictor-0.1.0-py3-none-any.whl'
out = root/'package-smoke'
out.mkdir(exist_ok=False)
sys.dont_write_bytecode = True
for key in list(os.environ):
    if key.upper() not in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT'}:
        del os.environ[key]
os.environ.update(TEMP=str(out),TMP=str(out))
changed = ['brasileirao_predictor/kernel_daemon.py','brasileirao_predictor/kernel_message.py','brasileirao_scripts/hotpath_smoke.py','brasileirao_predictor/research/price_strength/capture_decision.py']
with zipfile.ZipFile(wheel) as archive:
    names=archive.namelist()
    assert archive.testzip() is None
    assert not [n for n in names if Path(n).name == '.env' or Path(n).suffix in {'.db','.sqlite','.sqlite3'}]
    for name in changed:
        assert archive.read(name) == (repo/name).read_bytes(), name
    for name in names:
        assert (out/name).resolve().is_relative_to(out)
    archive.extractall(out)
sys.path.insert(0,str(out))
os.chdir(out)


def guard(event,args):
    if event.startswith(('socket.connect','socket.getaddrinfo','sqlite3.','subprocess.','os.system')):
        raise PermissionError('package_no_network_or_database')
    if event == 'open' and isinstance(args[0], (str,bytes,os.PathLike)):
        p=Path(os.fsdecode(args[0])).resolve()
        mode,flags=args[1] or '',args[2] or 0
        if (any(c in mode for c in 'wax+') or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT)) and not p.is_relative_to(out):
            raise PermissionError('package_write_outside_output')
        if p.name == '.env' or p.is_relative_to(repo/'data') or p.is_relative_to(Path('C:/BRASILEIRAO/DADOS_PRESERVADOS')):
            raise PermissionError('package_private_data')


sys.addaudithook(guard)
from brasileirao_predictor.research.price_strength import capture_decision
from brasileirao_scripts import hotpath_smoke
from brasileirao_predictor import kernel_message

for module in [capture_decision,hotpath_smoke,kernel_message]:
    assert Path(module.__file__).is_relative_to(out)
for command in [capture_decision.main,hotpath_smoke.main]:
    try:
        command(['--help'])
    except SystemExit as exc:
        assert exc.code == 0
assert not {'numpy','numba','scipy','brasileirao_predictor.kernel_daemon'} & sys.modules.keys()
(out/'receipt.json').write_text(json.dumps({'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'members':len(names),'changed_modules_exact':changed,'cli_help_passed':2,'numeric_runtime_imported':False,'network_and_operational_data_forbidden':True},indent=2),encoding='utf-8')
print('PACKAGE_SMOKE_PASS')
