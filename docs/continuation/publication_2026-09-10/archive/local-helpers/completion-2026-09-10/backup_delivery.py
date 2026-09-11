"""Checkpoint backup with byte comparison, ZIP CRC/SHA and a fresh bare Git restore."""
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
base=Path('C:/BRASILEIRAO')
repo=base/'brasileirao-predictor'
start='456b9025cfa3a596e754088ec3001fbeb5fcc7de'
out=base/'ENTREGAS/BRASILEIRAO_CPL_20260910'
bundle=base/'BACKUPS/brasileirao-predictor-CPL-20260910.bundle'
archive=base/'ENTREGAS/BRASILEIRAO_CPL_20260910_entrega.zip'
restore=root/'restored-git.git'
for path in (out,bundle,archive,restore):
    assert path.resolve().is_relative_to(base) and not path.exists(),str(path)
def git(*args,cwd=repo):
    result=subprocess.run(['git',*args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    return result.stdout.decode('utf-8').strip()
def digest(path):
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
commit=git('rev-parse','HEAD')
assert git('branch','--show-current')=='main' and not git('status','--porcelain=v1')
changed=git('diff','--name-only',start,commit).splitlines()
wheel=next((root/'package-smoke-final/dist').glob('*.whl'))
with zipfile.ZipFile(wheel) as z:
    assert z.testzip() is None
    module_checks=[]
    for name in changed:
        if name.endswith('.py') and name.startswith(('brasileirao_predictor/','brasileirao_scripts/')):
            assert z.read(name)==(repo/name).read_bytes(),name
            module_checks.append(name)
out.mkdir(parents=True)
copies={}
def copy(source,relative):
    target=out/relative;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)
    assert digest(source)==digest(target)
    copies[str(relative).replace('\\','/')]=digest(target)
for name in changed:copy(repo/name,Path('changed-files')/name)
for path in sorted((repo/'docs/continuation/completion_2026-09-10').rglob('*')):
    if path.is_file():copy(path,Path('review')/path.relative_to(repo/'docs/continuation/completion_2026-09-10'))
for path in (root/'package-smoke-final/dist').iterdir():copy(path,Path('dist')/path.name)
for name in ['run_isolated.py','check_changed.py','final_inventory.py','sources.py','sources_followup.py','write_docs.py','finalize_notes.py','prepare_integration.py','build_package.py','backup_delivery.py','precommit.diff','staged-paths.json']:
    copy(root/name,Path('reproduction')/name)
copy(base/'LEIA_PRIMEIRO.md',Path('LEIA_PRIMEIRO.md'))
copy(base/'INSTRUCOES/PROXIMO_PROMPT_APOS_CONTINUACAO_INTEGRAL_2026-09-10.md',Path('PROXIMO_PROMPT.md'))
git('bundle','create',str(bundle),'--all')
git('bundle','verify',str(bundle))
git('clone','--bare',str(bundle),str(restore))
assert git('rev-parse','HEAD',cwd=restore)==commit
git('fsck','--full',cwd=restore)
assert git('rev-parse','HEAD^{tree}',cwd=restore)==git('rev-parse','HEAD^{tree}')
copy(bundle,Path('git')/bundle.name)
receipt=dict(round='CPL-20260910',verified_at=datetime.now(UTC).isoformat(),commit=commit,base=start,
             branch='main',git_clean=True,pushed=False,deployed=False,bundle=dict(path=str(bundle),**digest(bundle)),
             bare_restore_verified=True,restored_tree=git('rev-parse','HEAD^{tree}',cwd=restore),
             wheel_changed_module_bytes_verified=module_checks,delivery_path=str(out),files=copies,
             scope='code_and_review_checkpoint_only_not_operational_database_restore',
             mandate_complete=False,profitability_established=False)
(out/'DELIVERY_MANIFEST.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in sorted(out.rglob('*')):
        if path.is_file():z.write(path,path.relative_to(out).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name in z.namelist():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert z.read(name)==(out/name).read_bytes()
    member_count=len(z.namelist())
receipt['zip']=dict(path=str(archive),**digest(archive),members_verified=member_count,crc_ok=True,all_bytes_equal=True)
audit=base/'AUDITORIA/CONTINUACAO_INTEGRAL_2026-09-10.json'
assert not audit.exists()
audit.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert not git('status','--porcelain=v1')
print(json.dumps(dict(commit=commit,changed_files=len(changed),zip=receipt['zip'],bundle=receipt['bundle'],audit=str(audit)),ensure_ascii=False))
