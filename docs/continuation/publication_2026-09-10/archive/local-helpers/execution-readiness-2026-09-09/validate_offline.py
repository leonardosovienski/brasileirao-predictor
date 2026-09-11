"""Run only isolated rehearsal regressions; forbid network and private/operational IO."""
import os
import sys
from pathlib import Path

repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
out = Path(sys.argv[1]).resolve()
out.mkdir(exist_ok=False)
for name in list(os.environ):
    if name.upper() not in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC','PATHEXT'}:
        del os.environ[name]
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
os.environ['TEMP'] = os.environ['TMP'] = str(out)
sys.dont_write_bytecode = True
sys.path.insert(0,str(repo))


def guard(event,args):
    if event.startswith(('socket.','sqlite3.','subprocess.','os.system')):
        raise PermissionError('network_database_subprocess_forbidden')
    if event=='open' and isinstance(args[0],str|bytes|os.PathLike):
        p=Path(os.fsdecode(args[0])).resolve()
        mode,flags=args[1] or '',args[2] or 0
        if (any(c in mode for c in 'wax+') or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT)) and not p.is_relative_to(out):
            raise PermissionError('write_outside_rehearsal')
        if p.is_relative_to(Path('C:/BRASILEIRAO/DADOS_PRESERVADOS')) or p.is_relative_to(repo/'data') or p.name=='.env':
            raise PermissionError('private_or_protected_input')


sys.addaudithook(guard)
import pytest

selected=['test_followup_capture_contract.py']
if '--full-research' in sys.argv:
    selected += ['test_price_hurdle.py','test_historical_admission.py','test_historical_numeric_boundary.py',
                 'test_live_capture_admission.py','test_closing_scenario.py','test_price_strength_quotes.py']
raise SystemExit(pytest.main([*[str(repo/'tests'/name) for name in selected],'-q','-p','no:cacheprovider',
    '-o',f'log_file={out / "pytest.log"}','--basetemp',str(out/'tmp'),'--junitxml',str(out/'junit.xml')]))
