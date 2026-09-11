"""Install this wheel in a separate venv; reuse verified RI dependencies explicitly."""
import json
import os
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parent
ri=Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09')
python=ri/'venv/Scripts/python.exe'
uv=Path('C:/BRASILEIRAO/work/price-feasibility-2026-09-09/bootstrap/Scripts/uv.exe')
out=root/'installed-cross-environment';out.mkdir(exist_ok=False)
venv=out/'venv'
wheel=next((root/'package-runtime-02/dist').glob('*.whl'))
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT'}}
env.update(TEMP=str(out),TMP=str(out),PYTHONDONTWRITEBYTECODE='1',UV_CACHE_DIR='C:/BRASILEIRAO/work/implementacao-2026-09-10/uv-cache')
commands=[]
def run(label,argv):
    result=subprocess.run([str(x) for x in argv],cwd=out,env=env,capture_output=True,timeout=120)
    (out/(label+'.stdout')).write_bytes(result.stdout)
    (out/(label+'.stderr')).write_bytes(result.stderr)
    commands.append(dict(label=label,argv=[str(x) for x in argv],exit_code=result.returncode))
    (out/'receipt.json').write_text(json.dumps(dict(commands=commands,scope='new project venv; explicit reuse of isolated RI dependencies'),indent=2),encoding='utf-8')
    assert result.returncode==0,label
    return result.stdout
run('venv',[uv,'venv','--offline','--no-python-downloads','--python',python,venv])
run('install',[uv,'pip','install','--offline','--no-deps','--python',venv/'Scripts/python.exe',wheel])
(venv/'Lib/site-packages/verified_ri_dependencies.pth').write_text(str(ri/'venv/Lib/site-packages')+'\n',encoding='utf-8')
source=run('project-location',[venv/'Scripts/python.exe','-I','-B','-c',
    'import brasileirao_predictor.research.shadow_portfolio as m; print(m.__file__)']).decode().strip()
assert Path(source).is_relative_to(venv)
source_runner=(root/'run_dotnet_cases.py').read_text(encoding='utf-8')
line="        PYTHONPATH=os.pathsep.join([str(Path('C:/BRASILEIRAO/brasileirao-predictor/tools/runtime_lab')), str(repo)]),\n"
assert line in source_runner
(root/'run_dotnet_installed.py').write_text(source_runner.replace(line,''),encoding='utf-8')
print(json.dumps(dict(python=str(venv/'Scripts/python.exe'),installed_module=source,commands=commands)))
