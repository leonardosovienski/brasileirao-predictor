"""Package sanitized evidence, scripts, current docs and automation definition."""
import hashlib
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=Path('C:/BRASILEIRAO/brasileirao-predictor')
DOC=REPO/'docs/continuation/data_completion_2026-09-09'
AUDIT=Path('C:/BRASILEIRAO/AUDITORIA')
EVIDENCE=DOC/'evidencias'
SCRIPTS=DOC/'reproducao'
EVIDENCE.mkdir(exist_ok=True)
SCRIPTS.mkdir(exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


current=[REPO/'README.md',REPO/'HANDOFF.md',REPO/'docs/ESTADO_ATUAL.md',REPO/'docs/DATA_MAP.md',
         REPO/'docs/continuation/RETOMADA.md',Path('C:/BRASILEIRAO/LEIA_PRIMEIRO.md'),
         DOC/'RESULTADO.md',DOC/'PENDENCIAS.md',DOC/'REPRODUZIR.md']
for path in current:
    text=path.read_text(encoding='utf-8')
    # HANDOFF contains historical checkpoints; change only the newly prepended section.
    active,sep,rest=text.partition('\n---\n') if path.name=='HANDOFF.md' else (text,'','')
    active=active.replace('137 testes','138 testes').replace('137\n','138\n').replace('e57 novos','e 58 novos').replace('e 57 novos','e 58 novos')
    active=active.replace('tests-02/','tests-05/').replace('`tests-02`','`tests-05`')
    path.write_text(active+sep+rest,encoding='utf-8')

path=DOC/'RESULTADO.md'
text=path.read_text(encoding='utf-8')
replacements={
    'universo177':'universo de 177', 'respondeu503':'respondeu 503','respondeu200':'respondeu 200',
    'foi154/177':'foi 154/177','Em15 eventos':'Em 15 eventos','de120s':'de 120s','relaxar120s/30s':'relaxar 120s/30s',
    'de2026':'de 2026','tinha336':'tinha 336','e202 Bet365':'e 202 Bet365',';158 pares':'; 158 pares',
    'selecionou32':'selecionou 32','preservaram-se348':'preservaram-se 348','Preservaram-se348':'Preservaram-se 348',
    'abstenções:222':'abstenções: 222','e126 fora':'e 126 fora','custo2%':'custo 2%','banca100u':'banca 100u','stake1u':'stake 1u',
    'perderam8,60u':'perderam 8,60u','com1/2/3/5%':'com 1/2/3/5%','seria−12,22u':'seria −12,22u',
    'por34 semanas':'por 34 semanas','semente20260909':'semente 20260909','percentil95%':'percentil 95%',
    'de2025':'de 2025','desde23/07/2025':'desde 23/07/2025','as32 seleções':'as 32 seleções',
    'em09/09':'em 09/09','de1,243s,1,079s e1,819s':'de 1,243s, 1,079s e 1,819s',
    'reportados450':'reportados 450','para2025':'para 2025','transforma2%':'transforma 2%',
    'plano250':'plano 250','inicial62':'inicial 62','final67 de250':'final 67 de 250','Restam183':'Restam 183',
    'reserva20':'reserva 20','retornou200 confirmando67':'retornou 200 confirmando 67','conta:5':'conta: 5',
    'as32 escolhas':'as 32 escolhas','e−9,24u':'e −9,24u','Python3.13.12':'Python 3.13.12',
    'pytest8.4.2':'pytest 8.4.2','Ruff0.12.12':'Ruff 0.12.12','Pyright1.1.405':'Pyright 1.1.405',
    'às19:57':'às 19:57','de11/09':'de 11/09',
}
for a,b in replacements.items():
    text=text.replace(a,b)
text=text.replace('O coletor futuro e a auditoria executam em processos separados.',
                  'O coletor futuro e a auditoria executam em processos separados.\n'
                  'A tipagem final incluiu explicitamente os três módulos, pois a configuração\n'
                  'do runtime exclui pesquisa. Corrigiu-se o estreitamento de tipo do limite\n'
                  'opcional e adicionou-se uma regressão que falhou antes da correção: status\n'
                  'booleano não pode representar o código numérico de pré-jogo. Os três\n'
                  'payloads do piloto conservaram resultados idênticos após esse endurecimento.\n'
                  'Versões anteriores, falhas e recibos da verificação foram preservados.')
path.write_text(text,encoding='utf-8')

sources={
    'historical_summary.json':'admission-01/historical_summary.json',
    'pilot_summary.json':'admission-01/pilot_summary.json',
    'closing_source_quality.json':'admission-01/closing_source_quality.json',
    'admission_manifest.json':'admission-01/manifest.json',
    'closing_summary.json':'closing-01/summary.json',
    'closing_manifest.json':'closing-01/manifest.json',
    'freeze_receipt.json':'closing-01/freeze_receipt.json',
    'closing_independent_check.json':'closing_independent_check.json',
    'pilot_hardening_check.json':'pilot_hardening_check.json',
    'engineering_checks.json':'engineering_checks.json',
    'account_final_recheck.json':'account_final_recheck.json',
    'transport_repair.json':'transport_repair.json',
    'public_sources_manifest.json':'public_sources/manifest.json',
    'extra_sources_manifest.json':'extra_docs/public_sources/manifest.json',
    'tests_final.xml':'tests-05/junit.xml',
    'pyright_final.txt':'engineering-02/pyright_explicit_config.txt',
}
for dest,src in sources.items():
    shutil.copyfile(ROOT/src,EVIDENCE/dest)
scripts=['account_recheck.py','acquire_history.py','audit_followup.py','audit_results.py','capture_pilot.py',
         'check_account.py','fetch_public.py','fetch_public_extra.py','followup_capture.py','repair_transport.py',
         'run_closing.py','validate_offline.py','verify_closing_independently.py','pyrightconfig.json']
for name in scripts:
    shutil.copyfile(ROOT/name,SCRIPTS/name)
save(SCRIPTS/'manifest.json',{'packaged_at':datetime.now(UTC).isoformat(),
     'execution_root':str(ROOT),'files':{name:sha(SCRIPTS/name) for name in scripts},
     'online_acquisition_is_not_offline_reproduction':True})
save(EVIDENCE/'completude.json',{
    'as_of':datetime.now(UTC).isoformat(),'round':'DC-20260909','all_economic_data_complete':False,
    'historical_files':{'required':177,'verified':177,'missing':0,'bytes':623271596},
    'public_2025':{'fixtures':380,'numerical_pairs':158,'reference_quality':'COMPROMISED_ALL_32_SELECTIONS'},
    'prospective_pilot':{'captures':3,'independent_fixtures':1,'active_offer_pairs':0},
    'execution_admitted':0,'profitability_established':False,'real_capital_enabled':False,
    'missing':['historical_point_in_time_receipts_and_schedule','active_contemporaneous_offer',
               'offer_capacity_and_currency','applicable_total_costs','acceptance_slippage_and_fill',
               'independent_prospective_validation'],
    'next_action':'fixed_single_capture_2026-09-11_before_23:00_UTC_then_offline_audit',
    'quota':{'before':62,'after':67,'monthly_limit':250,'protected_reserve':20,'next_max_metered_calls':1},
    'additional_cash_spend':0,'full_runtime_installed':False,
})
save(EVIDENCE/'manifest.json',{'packaged_at':datetime.now(UTC).isoformat(),
     'source_directory':str(ROOT),'files':{p.name:sha(p) for p in EVIDENCE.iterdir() if p.name!='manifest.json'}})
shutil.copyfile(Path('C:/Users/leona/.codex/automations/completar-dados-do-brasileir-o/automation.toml'),
                AUDIT/'automacao_dados_2026-09-09.toml')

# Complete path inventory without reading any protected Markdown content.
index=REPO/'docs/INDICE_DOCUMENTACAO.md'
old=index.read_text(encoding='utf-8')
categories={m.group(1):m.group(2) for m in re.finditer(r'^\| \[([^\]]+)\]\([^\n]+?\) \| ([^\n]+) \|$',old,re.M)}
files=sorted((p for p in REPO.rglob('*.md') if '.git' not in p.parts),key=lambda p:p.relative_to(REPO).as_posix().lower())
prefix=old.split('## Inventário completo:')[0]
prefix=prefix.replace('continuation/price_feasibility_2026-09-09/RESULTADO.md','continuation/data_completion_2026-09-09/RESULTADO.md')
prefix=prefix.replace('Essas cópias históricas',
    'Os novos guias DC e seus hashes constam também do recibo de dados em AUDITORIA.\nEssas cópias históricas')
lines=[prefix.rstrip(),'','## Inventário completo: '+str(len(files))+' documentos','','| Documento | Categoria |','| --- | --- |']
for path in files:
    name=path.relative_to(REPO).as_posix()
    if name.startswith('docs/continuation/data_completion_2026-09-09/'):
        category='Protocolo congelado — preservar' if path.name in ('PROTOCOL.md','ACQUISITION_ADDENDUM.md','REPARO_TRANSPORTE.md') else 'Rodada atual DC — resultados, evidências e continuidade'
    else:
        category=categories.get(name,'Referência técnica — não atesta operação local')
    target=name[5:] if name.startswith('docs/') else '../'+name
    lines.append(f'| [{name}]({target}) | {category} |')
index.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'markdown_documents':len(files),'scripts_packaged':len(scripts),'evidence_files':len(list(EVIDENCE.iterdir()))}))
