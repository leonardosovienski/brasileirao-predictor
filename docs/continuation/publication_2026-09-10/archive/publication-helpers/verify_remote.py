"""Compare independently cloned Git objects and publication evidence after pull."""
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

base=Path('C:/BRASILEIRAO')
root=base/'work/publication-2026-09-10'
repo=base/'brasileirao-predictor'
clone=root/'remote-clone'
stage=sys.argv[1]
if stage not in {'first','final'}: raise ValueError('unknown_verification_stage')
def git(path,*args):
    return subprocess.check_output(['git','-C',str(path),*args],stderr=subprocess.PIPE).decode().strip()
head=git(repo,'rev-parse','HEAD')
assert head==git(clone,'rev-parse','HEAD')==git(repo,'rev-parse','origin/main')==git(clone,'rev-parse','origin/main')
assert not git(repo,'status','--porcelain') and not git(clone,'status','--porcelain')
assert git(repo,'rev-parse','HEAD^{tree}')==git(clone,'rev-parse','HEAD^{tree}')
assert git(repo,'ls-files','--stage')==git(clone,'ls-files','--stage')
fsck=git(clone,'fsck','--full')
prefix=Path('docs/continuation/publication_2026-09-10')
manifest=json.loads((repo/prefix/'evidence/manifest.json').read_text())
checked=[]
for relative,meta in manifest.items():
    path=clone/prefix/relative
    content=path.read_bytes()
    # Only archive/evidence files are byte-preserving; ordinary text is normalized by Git.
    if relative.startswith(('archive/','evidence/')):
        assert len(content)==meta['bytes'] and hashlib.sha256(content).hexdigest()==meta['sha256'],relative
        checked.append(relative)
tested='cc38b57bd3ba6f8c2cbdce6353eaf085d4ece14f'
runtime=('brasileirao_predictor','brasileirao_scripts','dotnet','tools','.github','pyproject.toml','uv.lock','compose.yaml','Dockerfile.cli','Dockerfile.kernel','Dockerfile.worker','config.yaml','data','research','reports')
assert not git(clone,'diff','--name-only',tested,head,'--',*runtime)
result={'at':datetime.now(UTC).isoformat(),'stage':stage,'head':head,'tree':git(clone,'rev-parse','HEAD^{tree}'),'remote':'https://github.com/leonardosovienski/brasileirao-predictor.git','remote_before_clone':'ac22c56c3318623e07a722f34d44dc6cd877ea37','cloned_from_remote_then_pulled_ff_only':True,'independent_clone':str(clone),'both_worktrees_clean':True,'all_index_objects_equal':True,'git_fsck_exit_code':0,'git_fsck_output':fsck,'evidence_byte_checks':checked,'runtime_identical_to_linux_tested_head':tested,'private_local_data_restoration_claimed':False}
output=root/f'remote-{stage}.json'
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'head':head,'tree':result['tree'],'verified_evidence':len(checked),'both_clean':True,'runtime_equal':True}))
