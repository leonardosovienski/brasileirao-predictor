"""Owned subprocess test of the actual OS-lock context; no financial entry point."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parent
out = root / 'process-lab-v2'
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')

if len(sys.argv) > 1:
    assert out.exists()
    sys.path.insert(0, str(repo))
    os.chdir(out)
    def guard(event, args):
        if event.startswith(('socket.', 'subprocess.', 'os.system', 'sqlite3.')):
            raise PermissionError('child_network_process_database_forbidden')
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).resolve()
            mode, flags = args[1] or '', args[2] or 0
            if (any(c in mode for c in 'wax+') or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)) and not path.is_relative_to(out):
                raise PermissionError('child_write_outside_lab')
            if path.name == '.env' or any(path.is_relative_to(repo / p) for p in ('data', 'reports', 'research')):
                raise PermissionError('child_operational_data_forbidden')
        if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename'}:
            for value in args[:2] if event == 'os.rename' else args[:1]:
                if isinstance(value, (str, bytes, os.PathLike)) and not Path(os.fsdecode(value)).resolve().is_relative_to(out):
                    raise PermissionError('child_mutation_outside_lab')
    sys.addaudithook(guard)
    from brasileirao_predictor.bet_log import _writer_lock
    mode = sys.argv[1]
    try:
        with _writer_lock(out / 'synthetic.jsonl'):
            if mode == 'holder':
                (out / 'ready').write_text(str(os.getpid()))
                sys.stdin.readline()
            print(json.dumps({'acquired': True}), flush=True)
    except BlockingIOError:
        print(json.dumps({'acquired': False}), flush=True)
    raise SystemExit(0)

out.mkdir(exist_ok=False)
env = {k: v for k, v in os.environ.items() if k.upper() in {'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT'}}
env.update(TEMP=str(out), TMP=str(out), PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
interpreter = Path(sys._base_executable).resolve()
assert interpreter.is_relative_to(Path('C:/BRASILEIRAO'))
command = [str(interpreter), '-I', '-B', str(Path(__file__).resolve())]
records = []
holder = subprocess.Popen(command + ['holder'], cwd=out, env=env, stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    deadline = time.monotonic() + 15
    while not (out / 'ready').exists():
        assert holder.poll() is None, 'holder exited before lock'
        assert time.monotonic() < deadline, 'holder readiness timeout'
        time.sleep(0.05)
    assert int((out / 'ready').read_text()) == holder.pid
    blocked = subprocess.run(command + ['attempt'], cwd=out, env=env, capture_output=True, timeout=15, check=True)
    assert json.loads(blocked.stdout) == {'acquired': False}, blocked.stdout
    records.append({'phase': 'separate_process_conflict', 'result': json.loads(blocked.stdout)})
    # Terminate only this owned synthetic holder to prove OS release on abrupt exit.
    holder.kill()
    holder.communicate(timeout=10)
    recovered = subprocess.run(command + ['attempt'], cwd=out, env=env, capture_output=True, timeout=15, check=True)
    assert json.loads(recovered.stdout) == {'acquired': True}, recovered.stdout
    records.append({'phase': 'after_owned_holder_termination', 'result': json.loads(recovered.stdout)})
    assert (out / 'synthetic.jsonl.writer.lock').exists()
    receipt = dict(platform=sys.platform, lock_source_sha256=hashlib.sha256((repo / 'brasileirao_predictor/bet_log.py').read_bytes()).hexdigest(),
                   holder_pid=holder.pid, holder_stopped=holder.poll() is not None, phases=records,
                   scope='Windows local filesystem OS lock; actual ledger calls tested separately with threads')
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)
finally:
    if holder.poll() is None:
        holder.kill()
        holder.communicate(timeout=10)
