"""Verify Git recovery and deliver only scoped review artifacts under C:/BRASILEIRAO."""
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

BASE = Path('C:/BRASILEIRAO')
ROOT = Path(__file__).resolve().parent
REPO = BASE / 'brasileirao-predictor'
SOURCE = REPO / 'docs/continuation/integral_review_2026-09-09'
DEST = BASE / 'ENTREGAS/BRASILEIRAO_RI_20260909'
EXPECTED = 'a7ded8800536a2b9ad845ebdb9f3ee1758d97861'

def run(args, cwd=REPO):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError({'args':args,'exit':result.returncode,'output':result.stdout+result.stderr})
    return result.stdout + result.stderr

def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            result.update(chunk)
    return result.hexdigest()

assert run(['git','rev-parse','HEAD']).strip()==EXPECTED
assert not run(['git','status','--porcelain']).strip()
bundle=BASE/'BACKUPS/brasileirao-predictor-revisao-integral-2026-09-09.bundle'
assert not bundle.exists()
run(['git','bundle','create',str(bundle),'--all'])
verification=run(['git','bundle','verify',str(bundle)])
restored=ROOT/'restored-git.git'
assert not restored.exists()
clone=run(['git','clone','--bare',str(bundle),str(restored)])
restored_head=run(['git','--git-dir='+str(restored),'rev-parse','HEAD']).strip()
assert restored_head==EXPECTED
source_tree=run(['git','rev-parse','HEAD^{tree}']).strip()
restored_tree=run(['git','--git-dir='+str(restored),'rev-parse','HEAD^{tree}']).strip()
assert source_tree==restored_tree
fsck=run(['git','--git-dir='+str(restored),'fsck','--full','--strict'])
(ROOT/'git-recovery.log').write_text(verification+clone+fsck,encoding='utf-8',newline='\n')

assert not DEST.exists()
shutil.copytree(SOURCE,DEST)
manifest=json.loads((SOURCE/'MANIFESTO.json').read_text(encoding='utf-8'))
for rel, expected in manifest['files'].items():
    assert digest(SOURCE/rel)==expected,rel
    assert digest(DEST/rel)==expected,rel
assert digest(DEST/'MANIFESTO.json')==digest(SOURCE/'MANIFESTO.json')
local=DEST/'validacao_local'
local.mkdir()
extra_files=['preintegration-check.json','staged-verification.json','activation-receipt.json',
             'dotnet-sdk-receipt.json','environment.json','link-check.json','git-recovery.log','final-staged.patch']
for name in extra_files:
    shutil.copyfile(ROOT/name,local/name)
for round_name in ['regressions-before','regressions-after','temporal-before','temporal-after','domain-before',
                   'concurrency-before','event-before','baseline-broad','baseline-failure-recheck','final-corrections','isolation-boundary']:
    target=local/round_name
    target.mkdir()
    for name in ['junit.xml','isolation.json']:
        source=ROOT/round_name/name
        if source.exists():
            shutil.copyfile(source,target/name)
shutil.copytree(ROOT/'data-audit-02',local/'data-audit-02')
shutil.copytree(ROOT/'dist-final',DEST/'pacotes')

# Preserve the public contract bodies locally, outside Git; no private data or runtime caches.
archive=BASE/'BACKUPS/RI-20260909-revisao-fontes-ensaios.zip'
assert not archive.exists()
zip_sources={}
for path in DEST.rglob('*'):
    if path.is_file():
        zip_sources['entrega/'+path.relative_to(DEST).as_posix()]=path
for folder in ['public-sources','previous-active','previous-guides']:
    for path in (ROOT/folder).rglob('*'):
        if path.is_file():
            zip_sources['work/'+path.relative_to(ROOT).as_posix()]=path
for path in ROOT.iterdir():
    if path.is_file() and path.suffix in {'.py','.ps1','.json','.md','.log','.Config'}:
        zip_sources['work/'+path.name]=path
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as output:
    for name,path in sorted(zip_sources.items()):
        assert path.name!='.env' and path.suffix not in {'.db','.sqlite3'}
        output.write(path,name)
with zipfile.ZipFile(archive) as check:
    assert check.testzip() is None
    for name,path in zip_sources.items():
        assert hashlib.sha256(check.read(name)).hexdigest()==digest(path),name

record={
 'review':'RI-20260909','completed_at_utc':datetime.now(UTC).isoformat(),
 'base_commit':'ac22c56c3318623e07a722f34d44dc6cd877ea37','commit':EXPECTED,'branch':'main',
 'working_tree_clean':not run(['git','status','--porcelain']).strip(),
 'remote_main_verified_before_integration':'ac22c56c3318623e07a722f34d44dc6cd877ea37',
 'pushed':False,'new_remote_ci_triggered':False,
 'integration_scope':'local main; isolated checks only; no deployment or protected evaluator execution',
 'technical_state':'corrected modules ready in isolated tested scope; whole project not ready',
 'data_state':'integrity and conditional 2025 arithmetic admissible; execution/future-profit conclusions insufficient',
 'economic_state':'executable net profit not measurable; insufficient evidence',
 'python_latest_unique_cases':{'passed':1291,'skipped':1,'not_one_full_suite':True},
 'harness_boundary_tests_passed':4,'dotnet_tests':{'passed':69,'skipped':41},
 'scoped_ruff_pyright_python_build_package_smoke_dotnet_build':'passed; see logs and exclusions',
 'historical_files_verified':177,'csv_2025_matches':380,'pilot_captures':3,'pilot_independent_events':1,
 'execution_admitted':0,'conditional_2025_net_pnl_units':'-9.24','new_independent_validation':False,
 'protected_cohort_results_used':False,'operational_db_or_redis_started':False,'financial_actions':0,
 'capture_collector_and_schedule_changed':False,'auditor_activation':json.loads((ROOT/'activation-receipt.json').read_text(encoding='utf-8-sig')),
 'source_directory':str(SOURCE),'delivery_directory':str(DEST),
 'review_manifest_sha256':digest(SOURCE/'MANIFESTO.json'),
 'source_delivery_files_verified':len(manifest['files'])+1,
 'delivery_files':{p.relative_to(DEST).as_posix():digest(p) for p in sorted(DEST.rglob('*')) if p.is_file()},
 'git_recovery':{'bundle':str(bundle),'sha256':digest(bundle),'bytes':bundle.stat().st_size,
                 'bare_clone':str(restored),'restored_head':restored_head,'tree':restored_tree,
                 'bundle_verify_exit':0,'fsck_full_strict_exit':0,'operational_recovery_not_performed':True},
 'artifact_backup':{'path':str(archive),'sha256':digest(archive),'bytes':archive.stat().st_size,
                    'members':len(zip_sources),'crc_and_all_member_hashes_verified':True,
                    'final_receipt_is_separate_to_avoid_circular_hash':True},
 'final_staged_patch_sha256':digest(ROOT/'final-staged.patch'),
 'dependencies_external_to_folder':['Windows','Git installation','Codex app and scheduler','external providers/network','disposable Redis/Docker not installed here'],
}
text=json.dumps(record,ensure_ascii=False,indent=2)+'\n'
receipt=BASE/'AUDITORIA/REVISAO_INTEGRAL_2026-09-09.json'
assert not receipt.exists()
receipt.write_text(text,encoding='utf-8',newline='\n')
(DEST/'FECHAMENTO.json').write_text(text,encoding='utf-8',newline='\n')
(ROOT/'FECHAMENTO.json').write_text(text,encoding='utf-8',newline='\n')
(BASE/'AUDITORIA/REVISAO_INTEGRAL_2026-09-09.md').write_text(f'''# Fechamento da revisão RI-20260909

Commit local main `{EXPECTED}`, árvore limpa, sem push ou implantação. [Entrega](../ENTREGAS/BRASILEIRAO_RI_20260909/RESULTADO.md), [registro verificável](REVISAO_INTEGRAL_2026-09-09.json).

Correções validadas em escopo isolado; projeto globalmente não pronto. 1.291 casos únicos Python aprovados e um pulado em lotes delimitados; .NET 69 aprovados e 41 pulados. Build/pacote/lint/tipagem passam no escopo documentado. 177 históricos íntegros, 380 partidas2025, três capturas de um evento; zero execução admitida. Conta conhecida−9,24u reproduzida somente como cenário.

Bundle novo verificado, clonado em bare com HEAD/tree idênticos; fsck completo/strict passou. ZIP da revisão tem CRC e SHA256 de todos os membros conferidos. Entrega copiada com igualdade de hash. Isso verifica Git/artefatos, não restauração de operação protegida.

Coletor e agenda congelados, somente auditor independente corrigido e ativado. Estado atual da agenda não comprovado pela resposta legível da ferramenta. H14/H15/H9/A1 e dependências de coleta preservados; sem resultados/avaliação protegida, DB/Redis operacionais, credenciais de pesquisa, compras ou ações financeiras.
''',encoding='utf-8',newline='\n')
print(json.dumps({'commit':EXPECTED,'clean':record['working_tree_clean'],'delivery':str(DEST),
                  'source_files_verified':record['source_delivery_files_verified'],'bundle_bytes':bundle.stat().st_size,
                  'zip_bytes':archive.stat().st_size,'zip_members':len(zip_sources),
                  'git_recovery_verified':True,'receipt':str(receipt)},ensure_ascii=False))
