"""Run selected synthetic tests with process-local filesystem/network guards."""
import os
import platform
import sys
from pathlib import Path

base = Path(__file__).resolve().parent
candidate = base / "br"
os.chdir(candidate)
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
os.environ['BRASILEIRAO_PROJECT_ROOT'] = str(candidate)
os.environ['BRASILEIRAO_CONFIG_PATH'] = str(candidate / 'config.yaml')
os.environ['BRASILEIRAO_RUNTIME_ROOT'] = str(base / 'runtime')
os.environ['TEMP'] = os.environ['TMP'] = str(base / 'temp')
(base / 'temp').mkdir(exist_ok=True)
sys.dont_write_bytecode = True
sys.path.insert(0, str(candidate))
protected = Path('C:/BRASILEIRAO').resolve()
runtime = Path(sys.prefix).resolve()
stdlib = Path(sys.base_prefix).resolve()
platform.uname()  # Cache Windows metadata before the subprocess prohibition.
sys.path[:] = [p for p in sys.path if Path(p).resolve() != runtime.parent]
# JUnit only needs a display hostname; avoid platform's Windows shell fallback.
platform.node = lambda: 'isolated-qa'


def audit(event, args):
    if (event.startswith('socket.') and event != 'socket.gethostname') or event in {'subprocess.Popen', 'os.system'}:
        raise RuntimeError(f'Isolated QA forbids {event}')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1:3]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        )
        if writing and not path.is_relative_to(base):
            raise RuntimeError(f'QA write outside isolation: {path}')
        if path.is_relative_to(protected) and not (
            path.is_relative_to(base) or path.is_relative_to(runtime) or path.is_relative_to(stdlib)
        ):
            raise RuntimeError(f'Protected source read forbidden: {path}')


sys.addaudithook(audit)
import pytest

raise SystemExit(pytest.main([
    '-q', '-o', 'addopts=', '-p', 'no:cacheprovider', '--basetemp', str(base / 'temp' / 'pytest'),
    '--log-file', str(base / 'pytest.log'),
    'tests/test_evaluate_h14_prospective.py', 'tests/test_evaluate_h15_prospective.py',
    'tests/test_prospective_evaluation_guard.py', 'tests/test_prospective_protocol_compatibility.py',
    'tests/test_prospective_metrics.py',
    'tests/test_audit_hardening.py', 'tests/test_prospective_protocol_v2.py',
    '--junitxml', str(base / 'protocol-v2-test-results.xml'),
]))
