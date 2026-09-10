"""Verify current Git/data backups and publish the ER report in the requested root."""
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

base=Path('C:/BRASILEIRAO')
repo=base/'brasileirao-predictor'
root=Path(__file__).resolve().parent
doc=repo/'docs/continuation/execution_readiness_2026-09-09'
dc=repo/'docs/continuation/data_completion_2026-09-09'
audit=base/'AUDITORIA'
delivery=base/'ENTREGAS/BRASILEIRAO_ER_20260909'
display=Path('C:/Users/leona/Documents/Codex/2026-09-09/le/outputs/BRASILEIRAO_ER_20260909')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def git(args,cwd=repo):
    p=subprocess.run(['git',*map(str,args)],cwd=cwd,capture_output=True,text=True,timeout=90)
    assert p.returncode==0,p.stderr
    return p.stdout.strip(),p.stderr.strip()


head=git(['rev-parse','HEAD'])[0]
assert head=='60c95aa6b1b6b87f00da3ac5b59d67f0bf9bb369'
assert git(['rev-parse','HEAD^'])[0]=='7f18d543891cb3e68bb82c0a0d9fb58f9a8f12c0'
assert git(['status','--porcelain'])[0]==''
git(['diff','--check','HEAD^','HEAD'])
for folder in (doc/'evidencias',dc/'reproducao'):
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest['files'].items():
        p=folder/name
        assert sha(p)==expected
        blob=subprocess.check_output(['git','show',head+':'+p.relative_to(repo).as_posix()],cwd=repo)
        assert hashlib.sha256(blob).hexdigest()==expected
bundle=base/'BACKUPS/brasileirao-predictor-execution-readiness-2026-09-09.bundle'
assert not bundle.exists()
git(['bundle','create',bundle,'--all'])
bundle_check=git(['bundle','verify',bundle])
restore=base/'work/backup-verification-er-20260909.git'
assert not restore.exists()
git(['clone','--bare',bundle,restore])
assert git(['rev-parse','HEAD'],restore)[0]==head
git(['fsck','--full'],restore)

archive=base/'BACKUPS/ER-20260909-fontes-ensaios-rotinas.zip'
assert not archive.exists()
files=[(p,'execution-readiness-2026-09-09/'+p.relative_to(root).as_posix())
       for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
for name in ('followup_capture.py','audit_followup.py','capture_pilot.py'):
    files.append((base/'work/data-completion-2026-09-09'/name,'data-completion-2026-09-09/'+name))
files.append((audit/'automacao_dados_2026-09-09.toml','_metadata/automacao_dados_2026-09-09.toml'))
entries=[]
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for p,name in sorted(files):
        raw=p.read_bytes()
        z.writestr(name,raw)
        entries.append({'file':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    z.writestr('MANIFESTO_SHA256.json',json.dumps(entries,indent=2)+'\n')
with zipfile.ZipFile(archive) as z:
    for r in entries:
        raw=z.read(r['file'])
        assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']

record={'completed_at':datetime.now(UTC).isoformat(),'round':'ER-20260909','root':str(base),
        'base':git(['rev-parse','HEAD^'])[0],'commit':head,'branch':'main','worktree_clean':True,'push_performed':False,
        'changes':git(['diff','--name-status','HEAD^','HEAD'])[0].splitlines(),
        'tests':{'passed':153,'new_rehearsal_cases':15,'demonstrated_failures_before_fix':5,'ruff':'PASS',
                 'pyright':'PASS','explicit_typechecked_executors':2,'real_API_calls_during_checks':0,
                 'full_operational_stack_tested':False},
        'public_sources':{'logical_GETs':5,'successful':5,'authenticated_calls':0,'odds_quota_consumed':0},
        'documentation':{'markdown_indexed':159,'local_links_checked':218,'broken_links':0},
        'active_helpers':json.loads((root/'activation.json').read_text(encoding='utf-8')),
        'backup':{'git_bundle':str(bundle),'git_sha256':sha(bundle),'bundle_verify':'\n'.join(bundle_check),
                  'bare_restore':str(restore),'restored_HEAD':head,'git_fsck':'PASS',
                  'data_zip':str(archive),'data_sha256':sha(archive),'data_entries':len(entries),
                  'all_data_entries_CRC_SHA256_verified':True,'data_manifest_additional_entry':1},
        'cohort_or_operational_changes':False,'new_automation_created':False,'existing_schedule_changed':False,
        'next_decision_at':'2026-09-11T23:00:00+00:00','quota_budget_for_future_capture':1,
        'remaining':['active_contemporaneous_feed','personal_offer_capacity_and_currency',
                     'actual_total_costs','acceptance_and_fill_evidence','independent_future_validation'],
        'profitability_established':False,'all_economic_requirements_met':False,'real_capital_enabled':False,
        'delivery':str(delivery),'display_copy':str(display)}
save(audit/'EXECUTION_READINESS_2026-09-09.json',record)
summary=f'''# Correções e prontidão da coleta — ER-20260909

Cinco falhas da rotina futura foram corrigidas e reproduzidas em regressões.
**153 testes passaram**, incluindo 15 novos. Ruff e tipagem explícita dos dois
executores passaram. As versões testadas estão nos caminhos ativos da coleta.

Cinco fontes públicas foram preservadas com HTTP 200 e SHA-256. O campo
bookmakerIsActive indica principalmente coleta no agregador; false não prova
suspensão da oferta na casa. Limites/moeda e regras fiscais foram documentados
sem preencher condições pessoais desconhecidas. Nenhuma API de odds foi
consumida nesta etapa.

O projeto ainda depende de observação ativa antes do corte, capacidade,
custos reais e validação futura. A coleta de 11/09 antes das 20:00 de São Paulo
permanece agendada no acompanhamento diário às 19:57. O aplicativo e o
computador precisam estar em execução. Não houve aposta ou compra.

Tudo desta etapa está em `C:/BRASILEIRAO`; commit local `{head}` em main,
sem push. Há bundle Git com restauração bare verificada e ZIP dos novos
arquivos conferido por CRC/SHA-256. Os 159 Markdown estão indexados e os
218 links locais dos guias conferidos não apresentaram falha.

[Resultado completo e fontes](relatorio/RESULTADO.md),
[reprodução](relatorio/REPRODUZIR.md) e [recibo final](RECIBO_FINAL.json).
'''
for dest in (delivery,display):
    dest.mkdir(parents=True,exist_ok=False)
    shutil.copytree(doc,dest/'relatorio')
    shutil.copyfile(dc/'CONTINUIDADE.md',dest/'relatorio/CONTINUIDADE_DC.md')
    p=dest/'relatorio/REPRODUZIR.md'
    p.write_text(p.read_text(encoding='utf-8').replace('../data_completion_2026-09-09/CONTINUIDADE.md','CONTINUIDADE_DC.md'),
                 encoding='utf-8',newline='\n')
    p=dest/'relatorio/CONTINUIDADE_DC.md'
    p.write_text(p.read_text(encoding='utf-8').replace('../execution_readiness_2026-09-09/RESULTADO.md','RESULTADO.md'),
                 encoding='utf-8',newline='\n')
    (dest/'LEIA_PRIMEIRO.md').write_text(summary,encoding='utf-8',newline='\n')
    save(dest/'RECIBO_FINAL.json',record)
    save(dest/'MANIFESTO_ENTREGA.json',{'files':{p.relative_to(dest).as_posix():sha(p)
        for p in dest.rglob('*') if p.is_file() and p.name!='MANIFESTO_ENTREGA.json'}})
for p in delivery.rglob('*'):
    if p.is_file():
        assert sha(p)==sha(display/p.relative_to(delivery))
audit_body=summary.replace('relatorio/RESULTADO.md','../brasileirao-predictor/docs/continuation/execution_readiness_2026-09-09/RESULTADO.md')
audit_body=audit_body.replace('relatorio/REPRODUZIR.md','../brasileirao-predictor/docs/continuation/execution_readiness_2026-09-09/REPRODUZIR.md')
audit_body=audit_body.replace('RECIBO_FINAL.json','EXECUTION_READINESS_2026-09-09.json')
(audit/'EXECUTION_READINESS_2026-09-09.md').write_text(audit_body,encoding='utf-8',newline='\n')
assert git(['status','--porcelain'])[0]==''
print(json.dumps({'status':'VERIFIED_DELIVERED','commit':head,'data_backup_entries':len(entries),
                  'canonical_delivery':str(delivery),'report':str(display/'LEIA_PRIMEIRO.md')}))
