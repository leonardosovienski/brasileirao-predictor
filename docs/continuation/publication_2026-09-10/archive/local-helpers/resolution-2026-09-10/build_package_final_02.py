"""Build wheel from sdist offline, install in owned venv, check actual CLI."""
import hashlib
import json
import os
import subprocess
import time
import zipfile
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
ri=Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09')
python=ri/'venv/Scripts/python.exe'
uv=Path('C:/BRASILEIRAO/work/price-feasibility-2026-09-09/bootstrap/Scripts/uv.exe')
out=root/'package-final-02';out.mkdir(exist_ok=False)
venv=root/'installed-cross-environment/venv'
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT'}}
env.update(TEMP=str(out),TMP=str(out),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',UV_CACHE_DIR='C:/BRASILEIRAO/work/implementacao-2026-09-10/uv-cache')
env['PATH']=str(python.parent)+os.pathsep+str(Path(env['SYSTEMROOT'])/'System32')
receipt=dict(commands=[],dependency_scope='project wheel installed in separate owned venv; explicit existing .pth reuse of verified RI dependencies; no PYTHONPATH')

def save():
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')

def run(name,args,cwd=out,expected=0,timeout=180):
    start=time.monotonic()
    argv=[str(a) for a in args]
    with (out/(name+'.log')).open('xb') as log:
        p=subprocess.Popen(argv,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            code=p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            subprocess.run([str(Path(env['SYSTEMROOT'])/'System32/taskkill.exe'),'/PID',str(p.pid),'/T','/F'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW,check=False)
            p.wait(timeout=15);code=124
    receipt['commands'].append(dict(name=name,argv=argv,pid=p.pid,exit_code=code,expected=expected,elapsed_seconds=time.monotonic()-start))
    save();print(name,code,flush=True)
    assert code==expected,name
    return (out/(name+'.log')).read_text(encoding='utf-8',errors='replace').strip()

run('sdist',[uv,'build','--sdist','--offline','--no-python-downloads','--python',python,'--out-dir',out/'dist'],cwd=repo)
sdist=next((out/'dist').glob('*.tar.gz'))
run('wheel-from-sdist',[uv,'build',sdist,'--wheel','--offline','--no-python-downloads','--python',python,'--out-dir',out/'dist'])
wheel=next((out/'dist').glob('*.whl'))
with zipfile.ZipFile(wheel) as z:
    assert z.testzip() is None
    checks=[]
    for package in ('brasileirao_predictor','brasileirao_scripts'):
        for path in (repo/package).rglob('*.py'):
            relative=path.relative_to(repo).as_posix()
            assert z.read(relative)==path.read_bytes(),relative
            checks.append(relative)
    receipt['wheel_source_bytes_checked']=checks
receipt['artifacts']={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (out/'dist').iterdir()}
save()
run('install',[uv,'pip','install','--offline','--no-deps','--reinstall-package','brasileirao-predictor','--python',venv/'Scripts/python.exe',wheel])
installed=run('module-location',[venv/'Scripts/python.exe','-I','-B','-c','import brasileirao_predictor.kernel_cli as m; print(m.__file__)'])
assert Path(installed).is_relative_to(venv)
receipt['installed_module']=installed
run('kernel-help',[venv/'Scripts/brasileirao-kernel.exe','--help'])
run('kernel-health-unconfigured',[venv/'Scripts/brasileirao-kernel.exe','--healthcheck'],expected=2)
for name in ('brasileirao_predictor.data.odds_api_snapshot','brasileirao_scripts.import_ou25_historical_backfill','brasileirao_scripts.odds_shop','brasileirao_scripts.settle_live_prediction'):
    run(name.rsplit('.',1)[-1]+'-help',[venv/'Scripts/python.exe','-I','-B','-m',name,'--help'])
receipt['completed']=True;save()
print(json.dumps(dict(completed=True,files=receipt['artifacts'],module_count=len(checks))))
