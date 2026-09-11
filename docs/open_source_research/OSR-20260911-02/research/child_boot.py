"""Audited Python I/O policy, applied before numerical imports."""
import sys,os,pathlib,datetime,runpy
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent
target=pathlib.Path(sys.argv[1]).resolve()
if target.parent!=HERE:raise ValueError('invalid script')
# Parent assigns memory/process JobObject before releasing this gate.
if sys.stdin.readline().strip()!='GO':raise RuntimeError('parent gate missing')
DEPENDENCIES=pathlib.Path('C:/BRASILEIRAO/work/open-source-research-OSR-20260911-01/venv/Lib/site-packages').resolve()
read_roots=[ROOT,pathlib.Path(sys.prefix).resolve(),pathlib.Path(sys.base_prefix).resolve(),DEPENDENCIES]
def guard(event,args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.exec','os.spawn','os.startfile'}:
        raise PermissionError('OSR policy denies network/process')
    if event=='sqlite3.connect' and args[0]!=':memory:':raise PermissionError('memory SQLite only')
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        p=pathlib.Path(os.fsdecode(args[0])).resolve()
        mode=args[1];flags=args[2] or 0
        writing=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing:
            if not p.is_relative_to(ROOT/'evidence'):raise PermissionError('write outside evidence')
        elif not any(p.is_relative_to(a) for a in read_roots):raise PermissionError('read outside allowed roots')
sys.addaudithook(guard)
sys.path[:0]=[str(HERE),str(HERE/'references'),str(DEPENDENCIES)]
runpy.run_path(str(target),run_name='__main__')
