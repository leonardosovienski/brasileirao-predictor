"""Back up the committed Git history and acquired data; publish local receipts."""
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

BASE=Path('C:/BRASILEIRAO')
REPO=BASE/'brasileirao-predictor'
ROOT=Path(__file__).resolve().parent
DOC=REPO/'docs/continuation/data_completion_2026-09-09'
AUDIT=BASE/'AUDITORIA'
BACKUP=BASE/'BACKUPS'
DELIVERY=BASE/'ENTREGAS/BRASILEIRAO_DC_20260909'
OUTPUT=Path('C:/Users/leona/Documents/Codex/2026-09-09/le/outputs/DADOS_BRASILEIRAO_20260909')
OLD='5dec2521bab581d5dda104d954f4cc6274b74702'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def git(args,cwd=REPO):
    p=subprocess.run(['git',*map(str,args)],cwd=cwd,capture_output=True,text=True,timeout=120)
    if p.returncode:
        raise RuntimeError(p.stderr)
    return p.stdout.strip(),p.stderr.strip()


head=git(['rev-parse','HEAD'])[0]
assert git(['rev-parse','HEAD^'])[0]==OLD
assert git(['status','--porcelain'])[0]==''
diff=git(['diff','--name-status',OLD,head])[0]
assert len(diff.splitlines())==57
git(['diff','--check',OLD,head])
for area in ('evidencias','reproducao'):
    records=json.loads((DOC/area/'manifest.json').read_text(encoding='utf-8'))['files']
    for name,expected in records.items():
        p=DOC/area/name
        assert sha(p)==expected
        blob=subprocess.check_output(['git','show',head+':'+p.relative_to(REPO).as_posix()],cwd=REPO)
        assert hashlib.sha256(blob).hexdigest()==expected,'Git_manifest_byte_mismatch'
git(['fsck','--full'])
bundle=BACKUP/'brasileirao-predictor-dados-2026-09-09.bundle'
if bundle.exists():
    raise RuntimeError('backup_already_exists')
git(['bundle','create',bundle,'--all'])
verify_out,verify_err=git(['bundle','verify',bundle])
restore=BASE/'work/backup-verification-dc-20260909.git'
if restore.exists():
    raise RuntimeError('restore_target_already_exists')
git(['clone','--bare',bundle,restore])
assert git(['rev-parse','HEAD'],restore)[0]==head
fsck_out,fsck_err=git(['fsck','--full'],restore)
print(json.dumps({'git_backup':'VERIFIED_WITH_BARE_RESTORE','head':head,'bundle_bytes':bundle.stat().st_size}),flush=True)

archive=BACKUP/'DC-20260909-dados-e-recibos.zip'
if archive.exists():
    raise RuntimeError('data_backup_already_exists')
files=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
entries=[]
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as z:
    for p in files:
        stat=p.stat()
        name='data-completion-2026-09-09/'+p.relative_to(ROOT).as_posix()
        h=hashlib.sha256()
        count=0
        with p.open('rb') as source,z.open(name,'w',force_zip64=True) as target:
            for block in iter(lambda:source.read(1024*1024),b''):
                count+=len(block)
                h.update(block)
                target.write(block)
        after=p.stat()
        assert count==stat.st_size==after.st_size and stat.st_mtime_ns==after.st_mtime_ns,'source_changed_during_backup'
        entries.append({'path':name,'bytes':count,'sha256':h.hexdigest()})
    for p in [AUDIT/'automacao_dados_2026-09-09.toml',BASE/'LEIA_PRIMEIRO.md',DOC/'RESULTADO.md']:
        raw=p.read_bytes()
        name='_metadata/'+p.name
        z.writestr(name,raw)
        entries.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    z.writestr('MANIFESTO_SHA256.json',json.dumps({'created_at':datetime.now(UTC).isoformat(),'entries':entries},indent=2)+'\n')
with zipfile.ZipFile(archive) as z:
    for r in entries:
        h=hashlib.sha256()
        count=0
        with z.open(r['path']) as source:
            for block in iter(lambda:source.read(1024*1024),b''):
                count+=len(block)
                h.update(block)
        assert count==r['bytes'] and h.hexdigest()==r['sha256'],'data_zip_verification_failed'
save(AUDIT/'inventario_backup_DC_20260909.json',{'archive':str(archive),'entries':entries,'sha256_verified_after_compression':True})
print(json.dumps({'data_backup':'ALL_ENTRIES_CRC_SHA256_VERIFIED','entries':len(entries),'zip_bytes':archive.stat().st_size}),flush=True)

for p in (DELIVERY,OUTPUT):
    p.mkdir(parents=True,exist_ok=False)
    shutil.copytree(DOC,p/'relatorio')
    shutil.copyfile(REPO/'docs/ESTADO_ATUAL.md',p/'ESTADO_ATUAL.md')
    shutil.copyfile(AUDIT/'automacao_dados_2026-09-09.toml',p/'automacao_dados_2026-09-09.toml')
    # Delivery links leave the research repository; adapt only the delivered copy.
    pending=p/'relatorio/PENDENCIAS.md'
    body=pending.read_text(encoding='utf-8').replace('../../ESTADO_ATUAL.md','../ESTADO_ATUAL.md')
    pending.write_text(body,encoding='utf-8',newline='\n')
    readme=f'''# Dados do Brasileirão — entrega de 09/09/2026

**Dados adicionais adquiridos e testados. A evidência econômica continua incompleta.**

- 177/177 históricos de partidas verificados, total de 623.271.596 bytes.
- CSV oficial com 380 jogos de 2025 e três capturas atuais de um evento.
- 138 testes aprovados, Ruff, tipagem explícita e conferência aritmética separada.
- 156 Markdown indexados; 235 links locais verificados nos guias atuais, sem falhas.
- Commit local `{head}` em main; não houve push ou implantação operacional.
- Bundle Git com restauração bare verificada e ZIP dos novos dados conferido por CRC/SHA-256.

[Relatório completo](relatorio/RESULTADO.md), [pendências](relatorio/PENDENCIAS.md),
[reprodução](relatorio/REPRODUZIR.md) e [continuidade](relatorio/CONTINUIDADE.md).

Os arquivos canônicos estão em `C:/BRASILEIRAO`. Esta entrega tem cópia em
`C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_DC_20260909`; os dados brutos ficam em
`C:/BRASILEIRAO/work/data-completion-2026-09-09` e os backups em `C:/BRASILEIRAO/BACKUPS`.

Acompanhamento diário às 19:57 de São Paulo, com uma captura prevista antes de
11/09 às 20:00. O computador deve estar ligado e o aplicativo Codex em execução.
Agendamento não garante chegada à janela. A rotina rejeita dados tardios/inativos.

Faltam oferta ativa e contemporânea, capacidade, custos reais e validação futura.
A própria fonte pública sinaliza referência Pinnacle desatualizada no período
de todas as 32 seleções do replay condicional. O saldo de −9,24u é um cenário
aritmético, não ROI executável. Nenhuma aposta ou compra foi realizada.

A garantia da pasta cobre material recebido e produzido nesta máquina; não
atesta arquivos nunca enviados ou posteriores à captura do computador antigo.
'''
    (p/'LEIA_PRIMEIRO.md').write_text(readme,encoding='utf-8',newline='\n')

receipt={'completed_at':datetime.now(UTC).isoformat(),'round':'DC-20260909','canonical_root':str(BASE),
         'base':OLD,'commit':head,'branch':'main','push_performed':False,'worktree_clean':True,
         'changed_files':diff.splitlines(),'protected_runtime_contracts_dependencies_modified':False,
         'data':json.loads((DOC/'evidencias/completude.json').read_text(encoding='utf-8')),
         'engineering':{'tests_passed':138,'new_tests':58,'typechecked_modules':3,'ruff_passed':True,
                        'independent_fraction_check':'PASS','regression_failed_before_fix':True,
                        'pilot_results_unchanged_after_fix':True,'full_runtime_build_tested':False},
         'documentation':{'markdown_indexed':156,'current_local_links_checked':235,'broken_current_links':0,
                          'inventory':str(ROOT/'documentation_inventory.json'),'links':str(ROOT/'documentation_links.json')},
         'git_backup':{'path':str(bundle),'sha256':sha(bundle),'bytes':bundle.stat().st_size,
                       'bundle_verify':verify_out+'\n'+verify_err,'bare_restore':str(restore),'restored_head':head,
                       'fsck':fsck_out+'\n'+fsck_err},
         'data_backup':{'path':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,
                        'entries':len(entries),'manifest_extra_entry':1,'all_payload_entries_crc_sha256_verified':True,
                        'excluded_generated_caches':['__pycache__'],'future_outputs_not_in_snapshot':True},
         'automation':{'id':'completar-dados-do-brasileir-o','status':'ACTIVE','schedule_local':'daily 19:57 America/Sao_Paulo',
                        'spec_copy':str(AUDIT/'automacao_dados_2026-09-09.toml'),'app_and_computer_required':True},
         'delivery':str(DELIVERY),'display_copy':str(OUTPUT),
         'economic_task_complete':False,'real_capital_enabled':False,'all_received_and_current_known_project_material_in_requested_root':True,
         'guarantee_limit':'received_snapshot_and_current_work_only_not_unprovided_old_computer_files_or_external_system_dependencies'}
save(AUDIT/'DADOS_COMPLEMENTARES_2026-09-09.json',receipt)
for p in (DELIVERY,OUTPUT):
    save(p/'RECIBO_FINAL.json',receipt)
    inventory={f.relative_to(p).as_posix():sha(f) for f in p.rglob('*') if f.is_file()}
    save(p/'MANIFESTO_ENTREGA.json',{'created_at':datetime.now(UTC).isoformat(),'files':inventory})
for p in DELIVERY.rglob('*'):
    if p.is_file() and p.name!='MANIFESTO_ENTREGA.json':
        assert sha(p)==sha(OUTPUT/p.relative_to(DELIVERY)),'delivery_copy_mismatch'
assert git(['status','--porcelain'])[0]==''
print(json.dumps({'status':'DELIVERED_VERIFIED','commit':head,'canonical_delivery':str(DELIVERY),
                  'display_report':str(OUTPUT/'LEIA_PRIMEIRO.md'),'economic_task_complete':False}),flush=True)
