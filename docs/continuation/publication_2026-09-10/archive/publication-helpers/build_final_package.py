"""Build from the remote checkout without running collectors or evaluations."""
import hashlib
import json
import os
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

base=Path('C:/BRASILEIRAO')
root=base/'work/publication-2026-09-10'
repo=root/'remote-clone'
out=root/'package-final'
out.mkdir(exist_ok=False)
python=base/'work/revisao-integral-2026-09-09/venv/Scripts/python.exe'
uv=base/'work/price-feasibility-2026-09-09/bootstrap/Scripts/uv.exe'
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT'}}
env.update(TEMP=str(out),TMP=str(out),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',UV_CACHE_DIR=str(base/'work/implementacao-2026-09-10/uv-cache'))
receipt={'at':datetime.now(UTC).isoformat(),'head':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip(),'source':'independent clone pulled from origin/main','commands':[],'runtime_scope':'same application modules as Linux CI; local offline builder reuses cached build dependencies'}
def save(): (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
def run(name,args,cwd=out,expected=0):
    with (out/(name+'.log')).open('xb') as stream:
        result=subprocess.run([str(a) for a in args],cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    receipt['commands'].append({'name':name,'exit_code':result.returncode,'expected':expected})
    save()
    assert result.returncode==expected,name
    print(name,result.returncode,flush=True)
run('sdist',[uv,'build','--sdist','--offline','--no-python-downloads','--python',python,'--out-dir',out/'dist'],repo)
sdist=next((out/'dist').glob('*.tar.gz'))
run('wheel-from-sdist',[uv,'build',sdist,'--wheel','--offline','--no-python-downloads','--python',python,'--out-dir',out/'dist'])
wheel=next((out/'dist').glob('*.whl'))
module_checks=[]
with zipfile.ZipFile(wheel) as z:
    assert z.testzip() is None
    for package in ('brasileirao_predictor','brasileirao_scripts'):
        for path in (repo/package).rglob('*.py'):
            name=path.relative_to(repo).as_posix()
            assert z.read(name)==path.read_bytes(),name
            module_checks.append(name)
run('venv',[uv,'venv','--offline','--no-python-downloads','--python',python,out/'venv'])
run('install',[uv,'pip','install','--offline','--no-deps','--python',out/'venv/Scripts/python.exe',wheel])
# Health/help are light entrypoints and do not need application dependencies.
run('kernel-help',[out/'venv/Scripts/brasileirao-kernel.exe','--help'])
run('kernel-health-unconfigured',[out/'venv/Scripts/brasileirao-kernel.exe','--healthcheck'],expected=2)
receipt.update(completed=True,module_count=len(module_checks),module_paths=module_checks,artifacts={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (out/'dist').iterdir()},installation_scope='new venv with project wheel only, no reused application dependency path; CLI light help/health tested; complete dependency graph tested separately in Linux CI')
save()
print(json.dumps({'completed':True,'head':receipt['head'],'modules':len(module_checks),'artifacts':receipt['artifacts']}))
