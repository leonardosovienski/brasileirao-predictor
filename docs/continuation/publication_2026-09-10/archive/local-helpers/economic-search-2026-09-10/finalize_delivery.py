"""Archive the completed study without modifying prior runs or operational data."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT = Path('C:/BRASILEIRAO')
REPO = ROOT / 'brasileirao-predictor'
WORK = ROOT / 'work/economic-search-2026-09-10'
DELIVERY = ROOT / 'ENTREGAS/BRASILEIRAO_BE_20260910'
BUNDLE = ROOT / 'BACKUPS/brasileirao-predictor-BE-20260910.bundle'
ZIP = ROOT / 'BACKUPS/BRASILEIRAO_BE_20260910_entrega.zip'
RESTORE = WORK / 'restored-git.git'

def git(*args, cwd=REPO):
    return subprocess.check_output(['git', *args], cwd=cwd, stderr=subprocess.STDOUT)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for p in (DELIVERY, BUNDLE, ZIP, RESTORE):
    assert p.resolve().is_relative_to(ROOT.resolve()) and not p.exists(), p
head = git('rev-parse', 'HEAD').decode().strip()
assert head == '456b9025cfa3a596e754088ec3001fbeb5fcc7de'
assert not git('status', '--porcelain')
DELIVERY.mkdir()
shutil.copytree(REPO/'docs/continuation/economic_search_2026-09-10', DELIVERY/'relatorio')
for rel in ['brasileirao_predictor/research/price_strength/economic_search.py','tests/test_economic_search.py',
            'README.md','HANDOFF.md','docs/ESTADO_ATUAL.md','docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md',
            'docs/continuation/RETOMADA.md','.gitattributes','.gitignore']:
    target = DELIVERY/'codigo'/rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO/rel,target)
for directory in ['run-01','sources','source-recovery','tests-before-results','tests-final','dist-final']:
    shutil.copytree(WORK/directory, DELIVERY/directory)
for name in ['run_study.py','run_isolated.py','audit_results.py','freeze-receipt.json','independent-audit.json',
             'run-01-isolation.json','package-verification.json','build.stdout.txt','build.stderr.txt',
             'build-final.stdout.txt','build-final.stderr.txt','run-01.stdout.txt','run-01.stderr.txt']:
    shutil.copyfile(WORK/name, DELIVERY/name)
(DELIVERY/'input').mkdir()
shutil.copyfile(ROOT/'work/data-completion-2026-09-09/public_sources/football_data_bra_origin_csv.csv',
                DELIVERY/'input/football_data_bra_origin_csv.csv')
shutil.copyfile(ROOT/'INSTRUCOES/MANDATO_RECEBIDO_2026-09-09.txt',DELIVERY/'MANDATO_RECEBIDO.txt')
shutil.copyfile(ROOT/'INSTRUCOES/PROMPT_FINAL_REVISAO_INTEGRAL_2026-09-09.md',DELIVERY/'PROMPT_REVISAO.md')
(DELIVERY/'change.patch').write_bytes(git('diff','b95dabaf05800918ee46f4a40f1cfa74688ce4a8',head,'--binary'))
note = {'head':head,'branch':'main','clean':True,'pushed':False,'reviewed_changed_files':34,
        'study':'BE-20260910','technical_tests_unique':10,'calculation_runs':1,
        'arbitrage_candidate_baskets':226,'arbitrage_conditional_net_units':4.637604517669509,
        'model_net_units':-99.60,'real_bets':0,'executable_profit_demonstrated':False,
        'protected_cohorts_untouched':True,'dc_capture_unchanged':True,'direct_public_gets':10}
(DELIVERY/'delivery.json').write_text(json.dumps(note,indent=2)+'\n',encoding='utf-8')
manifest = {str(p.relative_to(DELIVERY)).replace('\\','/'):{'sha256':sha(p),'bytes':p.stat().st_size}
            for p in sorted(DELIVERY.rglob('*')) if p.is_file()}
(DELIVERY/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
git('bundle','create',str(BUNDLE),'--all')
verify = git('bundle','verify',str(BUNDLE)).decode(errors='replace')
git('clone','--bare',str(BUNDLE),str(RESTORE))
assert git('rev-parse','HEAD',cwd=RESTORE).decode().strip()==head
fsck = git('fsck','--full','--strict',cwd=RESTORE).decode(errors='replace')
doc_manifest=json.loads((DELIVERY/'relatorio/MANIFEST.json').read_text())
for name, digest in doc_manifest['files'].items():
    data=git('show',head+':docs/continuation/economic_search_2026-09-10/'+name,cwd=RESTORE)
    assert hashlib.sha256(data).hexdigest()==digest
with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for p in sorted(DELIVERY.rglob('*')):
        if p.is_file():archive.write(p,p.relative_to(DELIVERY).as_posix())
with zipfile.ZipFile(ZIP) as archive:
    assert archive.testzip() is None
    for name, item in manifest.items():
        assert hashlib.sha256(archive.read(name)).hexdigest()==item['sha256']
receipt={**note,'completed_at':datetime.now(timezone.utc).isoformat(),'delivery':str(DELIVERY),
         'delivery_files':len(manifest)+1,'bundle':{'path':str(BUNDLE),'bytes':BUNDLE.stat().st_size,'sha256':sha(BUNDLE),'verification':verify},
         'restore':{'path':str(RESTORE),'head_verified':head,'fsck_passed':True,'fsck_output':fsck,'manifest_members_verified':len(doc_manifest['files'])},
         'zip':{'path':str(ZIP),'bytes':ZIP.stat().st_size,'sha256':sha(ZIP),'all_crc_and_member_hashes_verified':True},
         'frozen_helpers_sha256':{name:sha(ROOT/'work/data-completion-2026-09-09'/name) for name in ['followup_capture.py','audit_followup.py']}}
assert not git('status','--porcelain')
path=ROOT/'AUDITORIA/BUSCA_ECONOMICA_2026-09-10.json'
with path.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt,indent=2))
