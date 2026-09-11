"""Check staged publication bytes and preserve proof before pushing main."""
import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

base=Path('C:/BRASILEIRAO')
repo=base/'brasileirao-predictor'
work=base/'work/publication-2026-09-10'
dest=repo/'docs/continuation/publication_2026-09-10'
tested='cc38b57bd3ba6f8c2cbdce6353eaf085d4ece14f'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args]).decode().strip()
assert git('branch','--show-current')=='main'
assert git('rev-parse','HEAD')==tested
paths=('brasileirao_predictor','brasileirao_scripts','dotnet','tools','.github','pyproject.toml','uv.lock','compose.yaml','Dockerfile.cli','Dockerfile.kernel','Dockerfile.worker','config.yaml','data','research','reports')
assert not git('diff','--name-only',tested,'--',*paths)
assert not git('diff','--cached','--name-only',tested,'--',*paths)
shutil.copyfile(work/'prepublish-scan.json',dest/'evidence/prepublish-scan.json')
receipt={'at':datetime.now(UTC).isoformat(),'initial_local_main':'ec493c8ec263ca9c11213cf3378d436b32279c44','remote_before':'ac22c56c3318623e07a722f34d44dc6cd877ea37','tested_head':tested,'runtime_config_tests_and_protected_trees_equal_to_tested_head':True,'ci_general_unchanged_in_publication_round':True,'protected_operation_not_migrated':True,'push_authorized_in_original_mandate_and_latest_request':True,'integration_method':'fast-forward main plus documentary commit; no force push or reset','global_ci':'not executed; skip marker required by documented protected scope','next':'push main, fast-forward fresh remote clone, compare index objects and evidence bytes, build final package and recover bundle'}
(dest/'evidence/integration-checks.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
manifest={}
for path in sorted(dest.rglob('*')):
    if path.is_file() and path.name!='manifest.json':
        raw=path.read_bytes()
        manifest[path.relative_to(dest).as_posix()]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
(dest/'evidence/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'publication_files':len(manifest),'runtime_equal_to_tested_head':True}))
