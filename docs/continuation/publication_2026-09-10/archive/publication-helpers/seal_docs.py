"""Seal final documents and evidence without changing the tested runtime."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

base=Path('C:/BRASILEIRAO')
root=base/'work/publication-2026-09-10'
repo=base/'brasileirao-predictor'
dest=repo/'docs/continuation/publication_2026-09-10'
python=base/'work/revisao-integral-2026-09-09/venv/Scripts/python.exe'
for script in ('prepare_archive_index.py','prepublish.py'):
    subprocess.run([str(python),'-I','-B',str(root/script)],cwd=repo,check=True)
shutil.copyfile(root/'prepublish-scan.json',dest/'evidence/prepublish-scan.json')
manifest={}
for path in sorted(dest.rglob('*')):
    if path.is_file() and path.name!='manifest.json':
        raw=path.read_bytes()
        manifest[path.relative_to(dest).as_posix()]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
(dest/'evidence/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
runtime=('brasileirao_predictor','brasileirao_scripts','dotnet','tools','.github','pyproject.toml','uv.lock','compose.yaml','Dockerfile.cli','Dockerfile.kernel','Dockerfile.worker','config.yaml','data','research','reports')
assert not subprocess.check_output(['git','-C',str(repo),'diff','--name-only','cc38b57bd3ba6f8c2cbdce6353eaf085d4ece14f','--',*runtime]).strip()
print(json.dumps({'final_manifest_entries':len(manifest),'runtime_equal_to_tested':True}))
