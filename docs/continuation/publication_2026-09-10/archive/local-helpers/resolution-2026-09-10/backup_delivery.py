"""Create the exact RES delivery and verify Git restoration and ZIP byte equality."""
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
start='3bda4c4b0abd9b94902f77509d7d211ac30e96f7'
out=base/'ENTREGAS/BRASILEIRAO_RES_20260910'
bundle=base/'BACKUPS/brasileirao-predictor-RES-20260910.bundle'
archive=base/'ENTREGAS/BRASILEIRAO_RES_20260910_entrega.zip'
restore=root/'restored-git.git'
audit=base/'AUDITORIA/RESOLUCAO_2026-09-10.json'
docs=repo/'docs/continuation/resolution_2026-09-10'
for path in (out,bundle,archive,restore,audit):
    assert path.resolve().is_relative_to(base) and not path.exists(),str(path)

def git_bytes(*args,cwd=repo):
    return subprocess.run(['git',*args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
def git(*args,cwd=repo):
    return git_bytes(*args,cwd=cwd).decode('utf-8').strip()
def digest(path):
    b=path.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

commit=git('rev-parse','HEAD')
assert commit!=start and git('rev-parse','HEAD^')==start
assert git('branch','--show-current')=='main'
assert not git('status','--porcelain=v1')
changed=git('diff','--name-only',start,commit).splitlines()
assert set(changed)==set(json.loads((root/'staged-paths.json').read_text()))
package=json.loads((root/'package-final-02/receipt.json').read_text())
assert package['completed']
wheel=next((root/'package-final-02/dist').glob('*.whl'))
with zipfile.ZipFile(wheel) as z:
    assert z.testzip() is None
    module_checks=[]
    for name in package['wheel_source_bytes_checked']:
        assert z.read(name)==(repo/name).read_bytes(),name
        module_checks.append(name)
assert len(module_checks)==231
out.mkdir(parents=True)
copies={}
def copy(source,relative):
    target=out/relative
    assert source.resolve().is_relative_to(base) and target.resolve().is_relative_to(out)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)
    assert digest(source)==digest(target)
    copies[relative.as_posix()]=digest(target)

for name in changed:copy(repo/name,Path('changed-files')/name)
for path in sorted(docs.rglob('*')):
    if path.is_file():copy(path,Path('review')/path.relative_to(docs))
for path in (root/'package-final-02/dist').iterdir():
    if path.name.endswith(('.whl','.tar.gz')):copy(path,Path('dist')/path.name)
helpers='''run_isolated.py check_changed.py write_delivery_docs.py prepare_integration.py build_package_final.py build_package_final_02.py finish_package_checks.py backup_delivery.py precommit.diff staged-paths.json index-evidence-check.json PLANO.md pyright.json prepare_lab.py run_dotnet_cases.py run_dotnet_installed.py invoke_lab.ps1 invoke_installed_lab.ps1 prepare_installed_cross.py install_compose_check.py validate_compose_final.py probe_public_catalog.py finalize_docs.py complete_source_review.py final_evidence.py'''.split()
for name in helpers:copy(root/name,Path('reproduction')/name)
copy(base/'LEIA_PRIMEIRO.md',Path('LEIA_PRIMEIRO.md'))
copy(base/'INSTRUCOES/PROXIMO_PROMPT_APOS_RESOLUCAO_2026-09-10.md',Path('PROXIMO_PROMPT.md'))
for path in sorted((root/'previous-guides').rglob('*')):
    if path.is_file():copy(path,Path('previous-guides')/path.relative_to(root/'previous-guides'))
print('delivery-files-copied',len(copies),flush=True)
git('bundle','create',str(bundle),'--all')
git('bundle','verify',str(bundle))
git('clone','--bare',str(bundle),str(restore))
assert git('rev-parse','HEAD',cwd=restore)==commit
git('fsck','--full',cwd=restore)
assert git('rev-parse','HEAD^{tree}',cwd=restore)==git('rev-parse','HEAD^{tree}')
evidence_paths=sorted(p.relative_to(repo).as_posix() for p in (docs/'evidence').rglob('*') if p.is_file())
with subprocess.Popen(['git','cat-file','--batch'],cwd=restore,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as process:
    for name in evidence_paths:
        process.stdin.write(('HEAD:'+name+'\n').encode());process.stdin.flush()
        header=process.stdout.readline().decode().split()
        assert len(header)==3 and header[1]=='blob',name
        b=process.stdout.read(int(header[2]));assert process.stdout.read(1)==b'\n'
        assert b==(repo/name).read_bytes(),name
    process.stdin.close();assert process.wait(timeout=30)==0
assert evidence_paths==sorted(json.loads((root/'index-evidence-check.json').read_text())['files'])
copy(bundle,Path('git')/bundle.name)
print('git-restoration-verified',flush=True)
registry=json.loads((docs/'REGISTROS.json').read_text(encoding='utf-8'))
receipt=dict(round='RES-20260910',verified_at=datetime.now(UTC).isoformat(),commit=commit,base=start,branch='main',git_clean=True,pushed=False,deployed=False,bundle=dict(path=str(bundle),**digest(bundle)),bare_restore_verified=True,restored_tree=git('rev-parse','HEAD^{tree}',cwd=restore),restored_evidence_bytes_verified=evidence_paths,wheel_source_module_bytes_verified=module_checks,delivery_path=str(out),files=copies,scope='code_and_review_checkpoint_only_not_operational_database_restore',mandate_complete=False,profitability_established=False,capital_enabled=False,issue_status_counts=registry['summary']['statuses'],allowed_source_semantic_review_completed=True,validation=dict(python_unique_passed=336,dotnet_passed=160,latest_cross_process_passed=1,whole_ci_executed=False),protected_operation_unchanged=True)
dump(out/'DELIVERY_MANIFEST.json',receipt)
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in sorted(out.rglob('*')):
        if path.is_file():z.write(path,path.relative_to(out).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert len(names)==len(set(names))==len(copies)+1
    for name in names:
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert z.read(name)==(out/name).read_bytes()
receipt['zip']=dict(path=str(archive),**digest(archive),members_verified=len(names),crc_ok=True,all_bytes_equal=True)
dump(audit,receipt)
assert not git('status','--porcelain=v1')
print(json.dumps(dict(commit=commit,changed_files=len(changed),zip=receipt['zip'],bundle=receipt['bundle'],audit=str(audit)),ensure_ascii=False))
