"""Normalize versioned text, verify local links and record the bounded diff."""
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parent
REPO=Path('C:/BRASILEIRAO/brasileirao-predictor')
DOC=REPO/'docs/continuation/data_completion_2026-09-09'
AUDIT=Path('C:/BRASILEIRAO/AUDITORIA')
BASE='5dec2521bab581d5dda104d954f4cc6274b74702'
CURRENT=['README.md','HANDOFF.md','docs/ESTADO_ATUAL.md','docs/DATA_MAP.md','docs/HISTORICAL_SOURCE_REGISTER.md',
         'docs/PROMPT_PROXIMA_SESSAO.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md',
         'brasileirao_predictor/research/price_strength/README.md']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


paths=[REPO/p for p in CURRENT]+[p for p in DOC.rglob('*') if p.is_file()]
for path in paths:
    text=path.read_text(encoding='utf-8')
    if path.name=='RESULTADO.md':
        text=text.replace('às20:00','às 20:00')
    path.write_text(text,encoding='utf-8',newline='\n')
for name in ('PROTOCOL.md','ACQUISITION_ADDENDUM.md'):
    expected={'PROTOCOL.md':'40b45152f77db425787739136a7092ee375a3ce0f34e07457b5cf43b6c10de21',
              'ACQUISITION_ADDENDUM.md':'c684190305fbf8dae6375c1790641e8cf98eb2d2224af5aa0512d4c555393132'}[name]
    assert sha(DOC/name)==expected,'frozen_protocol_bytes_changed'
for area in ('reproducao','evidencias'):
    manifest=DOC/area/'manifest.json'
    record=json.loads(manifest.read_text(encoding='utf-8'))
    record['files']={p.name:sha(p) for p in (DOC/area).iterdir() if p.is_file() and p.name!='manifest.json'}
    record['versioned_text_encoding']='UTF-8 LF; original acquisition/output byte hashes refer to canonical work files'
    write(manifest,record)

report=AUDIT/'DADOS_COMPLEMENTARES_2026-09-09.md'
report.write_text('''# Auditoria dos dados complementares — DC-20260909

Todos os novos dados, código, scripts, relatórios e recibos desta rodada estão
sob `C:/BRASILEIRAO`. Foram verificados 177/177 históricos, 623.271.596 bytes;
recuperou-se o CSV oficial de 380 jogos de 2025 e coletaram-se três capturas
atuais de um evento. Isso não completa a evidência econômica exigida.

Passaram 138 testes (80 anteriores e 58 novos), Ruff e tipagem explícita de três
módulos. A regressão de status booleano falhou antes da correção. Os três
resultados do piloto permaneceram idênticos. Contabilidade closing conferida
com Fraction: −9,24u condicional; referência comprometida em todas as 32 seleções.

- [Resultado completo](../brasileirao-predictor/docs/continuation/data_completion_2026-09-09/RESULTADO.md)
- [Pendências](../brasileirao-predictor/docs/continuation/data_completion_2026-09-09/PENDENCIAS.md)
- [Reprodução](../brasileirao-predictor/docs/continuation/data_completion_2026-09-09/REPRODUZIR.md)
- [Continuidade agendada](../brasileirao-predictor/docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md)

Cinco consultas de quota gratuita, contador final 67/250, reserva 20 preservada.
Nenhuma compra, aposta, ativação operacional ou alteração de coorte protegida.
Faltam procedência temporal suficiente, oferta ativa, capacidade, custos reais
e validação futura. Acompanhamento diário às 19:57 de São Paulo na tarefa atual,
com janela fixa em 11/09 antes das 20:00; o aplicativo precisa estar em execução.

O recibo JSON de mesmo nome identifica base, commit final, inventários, checks,
manifestos e backups. O bundle Git cobre código/histórico; o ZIP DC cobre os
novos dados e recibos até sua captura. A agenda ativa reside no aplicativo e
possui uma cópia documental em `automacao_dados_2026-09-09.toml`.

A garantia cobre o material recebido e produzido nesta máquina. Não atesta
arquivos nunca entregues ou posteriores ao snapshot do computador antigo.
Documentos históricos e contratos congelados foram preservados.
''',encoding='utf-8',newline='\n')

links=[]
checkpaths=[REPO/p for p in CURRENT]+list(DOC.glob('*.md'))+[Path('C:/BRASILEIRAO/LEIA_PRIMEIRO.md'),report]
for path in checkpaths:
    text=path.read_text(encoding='utf-8')
    if path.name=='HANDOFF.md':
        text=text.split('\n---\n')[0]
    if path==REPO/'brasileirao_predictor/research/price_strength/README.md':
        text=text.split('## Limites')[0] if '## Limites' in text else text
    for m in re.finditer(r'\[[^\]\n]*\]\(([^)\n]+)\)',text):
        target=m.group(1).strip().strip('<>')
        if re.match(r'^[a-zA-Z]+://',target) or target.startswith('#'):
            continue
        clean=unquote(target.split('#')[0])
        resolved=(path.parent/clean).resolve()
        links.append({'source':str(path),'target':target,'resolved':str(resolved),'exists':resolved.exists()})
missing=[r for r in links if not r['exists']]
write(ROOT/'documentation_links.json',{'checked_at':datetime.now(UTC).isoformat(),'links':links,'missing':missing,
                                     'scope':'current_guides_new_round_index_paths_not_protected_document_contents'})
assert not missing,missing

current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
assert current==BASE,'base_changed'
modified=subprocess.check_output(['git','diff','--name-only',BASE],cwd=REPO,text=True).splitlines()
assert set(modified)==set(CURRENT),modified
all_md=sorted(p for p in REPO.rglob('*.md') if '.git' not in p.parts)
write(ROOT/'documentation_inventory.json',{'checked_at':datetime.now(UTC).isoformat(),'markdown_count':len(all_md),
     'files':[{'path':str(p.relative_to(REPO)),'sha256':sha(p)} for p in all_md],
     'historical_content_not_interpreted':True})
write(ROOT/'preintegration_review.json',{'reviewed_at':datetime.now(UTC).isoformat(),'base':BASE,
     'modified_existing':modified,'new_scope':['3 pure research modules','4 test files','DC documentation/evidence/scripts'],
     'protected_runtime_contracts_dependencies_modified':False,'active_local_links_checked':len(links),
     'broken_active_local_links':0,'markdown_inventory':len(all_md),'real_capital_enabled':False})
print(json.dumps({'markdown_files':len(all_md),'links_checked':len(links),'broken_links':len(missing),'base_unchanged':True}))
