"""Restore-test Git and verify the final local delivery, without operational data."""

import hashlib
import json
import shutil
import socket
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
repo=Path('C:/BRASILEIRAO/brasileirao-predictor')
doc=repo/'docs/continuation/implementation_2026-09-10'
base='a7ded8800536a2b9ad845ebdb9f3ee1758d97861'
delivery=Path('C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_IE_20260910')
backup=Path('C:/BRASILEIRAO/BACKUPS')
bundle=backup/'brasileirao-predictor-IE-20260910.bundle'
archive=backup/'BRASILEIRAO_IE_20260910_entrega.zip'
restored=root/'restored-git.git'
for target in [delivery,bundle,archive,restored]:
    assert not target.exists(),str(target)


def git(*args,cwd=repo):
    return subprocess.check_output(['git',*args],cwd=cwd,stderr=subprocess.STDOUT)


def digest(p):
    raw=p.read_bytes()
    return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


assert not git('status','--porcelain').strip()
head=git('rev-parse','HEAD').decode().strip()
assert git('branch','--show-current').decode().strip()=='main'
manifest=json.loads((doc/'MANIFEST.json').read_text(encoding='utf-8'))
for name,entry in manifest['files'].items():
    assert digest(doc/name)==entry,name
    raw=git('show',head+':docs/continuation/implementation_2026-09-10/'+name)
    assert hashlib.sha256(raw).hexdigest()==entry['sha256'],name

backup.mkdir(exist_ok=True)
git('bundle','create',str(bundle),'--all')
(root/'bundle-verify.log').write_bytes(git('bundle','verify',str(bundle)))
(root/'git-restore.log').write_bytes(git('clone','--bare',str(bundle),str(restored)))
(root/'git-fsck.log').write_bytes(git('fsck','--full','--strict',cwd=restored))
assert git('rev-parse','refs/heads/main',cwd=restored).decode().strip()==head
for name,entry in manifest['files'].items():
    raw=git('show',head+':docs/continuation/implementation_2026-09-10/'+name,cwd=restored)
    assert hashlib.sha256(raw).hexdigest()==entry['sha256']

shutil.copytree(doc,delivery)
changed=git('diff','--name-only',base,head).decode().splitlines()
for name in changed:
    if name.startswith('docs/continuation/implementation_2026-09-10/'):
        continue
    target=delivery/'codigo_alterado'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(repo/name,target)
package_dir=delivery/'pacote'
shutil.copytree(root/'dist-final-02',package_dir)
software=delivery/'infraestrutura';software.mkdir()
shutil.copyfile(root/'software/Redis-8.2.9-Windows-x64-msys2.zip',software/'Redis-8.2.9-Windows-x64-msys2.zip')
shutil.copyfile(root/'software-source.json',software/'memurai-source-metadata.json')
receipts=delivery/'fechamento';receipts.mkdir()
for name in ['final_backup.py','seal_before_commit.py','package_smoke_final.py','bundle-verify.log','git-restore.log','git-fsck.log','staged-files.json']:
    shutil.copyfile(root/name,receipts/name)
(receipts/'changes.diff').write_bytes(git('diff','--binary',base,head))
shutil.copyfile(Path('C:/BRASILEIRAO/LEIA_PRIMEIRO.md'),receipts/'LEIA_PRIMEIRO.md')
shutil.copyfile(Path('C:/BRASILEIRAO/INSTRUCOES/PROXIMO_PROMPT_APOS_IMPLEMENTACAO_2026-09-10.md'),receipts/'PROXIMO_PROMPT.md')
inventory={p.relative_to(delivery).as_posix():digest(p) for p in sorted(delivery.rglob('*')) if p.is_file()}
(delivery/'MANIFEST_ENTREGA.json').write_text(json.dumps({'commit':head,'files':inventory},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name,entry in inventory.items():
    assert digest(delivery/name)==entry
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(delivery.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(delivery).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(inventory)+1
    for name,entry in inventory.items():
        assert hashlib.sha256(z.read(name)).hexdigest()==entry['sha256'],name
with socket.socket() as probe:
    probe.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
    probe.bind(('127.0.0.1',26380))

result={
    'round':'IE-20260910','closed_at':datetime.now(UTC).isoformat(),'repository':str(repo),'branch':'main',
    'base':base,'head':head,'commits':git('log','--format=%H %s',base+'..'+head).decode().splitlines(),
    'git_clean':not git('status','--porcelain').strip(),'changed_files':len(changed),
    'push_performed':False,'remote_main_last_verified':'ac22c56c3318623e07a722f34d44dc6cd877ea37',
    'remote_ci_for_this_head_executed':False,
    'delivery':{'path':str(delivery),'files':len(inventory)+1,'all_hashes_verified':True},
    'bundle':{'path':str(bundle),**digest(bundle),'verified':True,'bare_restore':str(restored),'fsck_strict_passed':True},
    'archive':{'path':str(archive),**digest(archive),'crc_and_every_member_hash_verified':True},
    'package':{p.name:digest(p) for p in package_dir.iterdir()},
    'tests':{'python_scope_passed':282,'python_scope_skipped':4,'python_real_redis_passed':27,'dotnet_passed':110,'dotnet_skipped':0,'guard_probes_passed':7},
    'states':{'technical':'ready_in_tested_lab_not_globally_ready','data':'insufficient_for_execution','economic':'executable_profit_not_measurable'},
    'prospective_independent_fixture':'id1000032566887012','capture_decision_at':'2026-09-11T23:00:00Z',
    'new_authenticated_odds_calls':0,'protected_cohorts_used':False,'real_capital_enabled':False,
    'owned_redis_stopped_and_port_free':True,
    'limits':['No production Compose/feed homologation','No protected cohort or operational restore','No new remote CI','No executable profit demonstrated','Existing automation activity still not confirmed'],
}
audit=Path('C:/BRASILEIRAO/AUDITORIA/IMPLEMENTACAO_2026-09-10.json')
assert not audit.exists()
audit.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
audit.with_suffix('.md').write_text(f'''# Fechamento IE-20260910

Commit local main: {head}. Checkout limpo, sem push. As correções e a integração sintética foram verificadas; lucro executável não demonstrado.

282 testes Python aprovados/4pulos,27 com Redis real,110.NET/0pulos e7barreiras. Build/wheel, tipagem, lint, manifesto e links verificados. Instância Redis própria encerrada; porta26380 livre ao fechamento.

Entrega: {delivery}. Bundle: {bundle}. ZIP: {archive}. Os arquivos foram conferidos por SHA256; ZIP por CRC e SHA de cada membro. Bundle restaurado em bare e fsck --full --strict aprovado. Isso verifica Git/evidências, não restaura serviços ou dados operacionais protegidos.

Próxima dependência econômica é a captura DC congelada e posterior evidência comercial/validação independente. Não houve novas odds autenticadas, labels2026, operações financeiras ou alteração de H14/H15/H9/A1. Detalhes, commits, hashes e limitações estão no JSON homônimo.
''',encoding='utf-8')
print(json.dumps({'head':head,'delivery_files':len(inventory)+1,'bundle_bytes':result['bundle']['bytes'],'archive_bytes':result['archive']['bytes'],'restore_verified':True,'git_clean':result['git_clean']},indent=2))
