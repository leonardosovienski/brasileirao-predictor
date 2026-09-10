"""Update only current guides and the independent future capture, preserving evidence."""
import hashlib
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

BASE=Path('C:/BRASILEIRAO')
REPO=BASE/'brasileirao-predictor'
ROOT=Path(__file__).resolve().parent
DOC=REPO/'docs/continuation/execution_readiness_2026-09-09'
DC=REPO/'docs/continuation/data_completion_2026-09-09'
ACTIVE=BASE/'work/data-completion-2026-09-09'
OLD='7f18d543891cb3e68bb82c0a0d9fb58f9a8f12c0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,text):
    path.write_text(text,encoding='utf-8',newline='\n')


def save(path,data):
    write(path,json.dumps(data,ensure_ascii=False,indent=2)+'\n')


assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==OLD
(ROOT/'previous_active_scripts').mkdir(exist_ok=False)
records=[]
for name in ('followup_capture.py','audit_followup.py'):
    source=DC/'reproducao'/name
    destination=ACTIVE/name
    old_text=subprocess.check_output(['git','show',OLD+':'+source.relative_to(REPO).as_posix()],cwd=REPO).decode()
    assert destination.read_text(encoding='utf-8').replace('\r\n','\n')==old_text.replace('\r\n','\n')
    previous_hash=sha(destination)
    shutil.copyfile(destination,ROOT/'previous_active_scripts'/name)
    shutil.copyfile(source,destination)
    assert sha(destination)==sha(source)
    records.append({'active_path':str(destination),'old_sha256':previous_hash,'new_sha256':sha(source)})
activation={'activated_at':datetime.now(UTC).isoformat(),'scripts':records,'protected_collectors_or_agendas_changed':False,
            'fixture_cutoff_quota_and_bookmakers_unchanged':True}
save(ROOT/'activation.json',activation)

(DOC/'evidencias').mkdir(exist_ok=True)
manifest=DC/'reproducao/manifest.json'
shutil.copyfile(manifest,DOC/'evidencias/previous_reproduction_manifest.json')
record=json.loads(manifest.read_text(encoding='utf-8'))
record['files']={p.name:sha(p) for p in (DC/'reproducao').iterdir() if p.name!='manifest.json'}
record['revision_updated_at']=datetime.now(UTC).isoformat()
record['revision_round']='ER-20260909; only followup_capture.py and audit_followup.py changed'
record['previous_version_commit']=OLD
save(manifest,record)

sources=json.loads((ROOT/'public_sources/manifest.json').read_text(encoding='utf-8'))
contracts={
    'verified_at':datetime.now(UTC).isoformat(),'scope':'public_documented_conditions_not_personal_execution_approval',
    'bookmakerIsActive':{'source':'oddspapi_current_odds_contract',
        'meaning':'primarily_provider_collecting_this_bookmaker_for_this_fixture',
        'false_proves_bookmaker_stopped_offering_bet':False,'inactive_feed_remains_rejected':True},
    'reported_limit':{'source':'oddspapi_limit_semantics','sportsbook_semantics':'maximum_stake_reported_for_selection',
        'currency_rule':'source_account_currency','fixture_limit_currency':None,
        'API_billing_currency_is_not_proof_of_bet_currency':True,'personal_offer_capacity':None},
    'bet365_br_minimum':{'source':'bet365_br_stake_limits','reference_table_amount':'0.50','currency':'BRL',
        'actual_minimum_can_vary_with_odds':True,'personal_maximum':None,'betslip_or_account_access_performed':False},
    'tax_general_rule':{'sources':['receita_current_service','receita_2026_tables'],'reference_rate':'0.15',
        'assessment':'annual_net_prize_exceeding_applicable_exemption','flat_stake_tax':'not_supported',
        'personal_annual_tax_base':None,'actual_tax_amount':None,'applied_to_prior_replay':False},
    'unknown_actual_costs':['tax_amount','commission','slippage','rejections','fill','data_at_production_scale',
                            'infrastructure','maintenance'],
    'sources':{r['source']:{'url':r['url'],'http_status':r['http_status'],'sha256':r['sha256']} for r in sources},
    'profitability_established':False,'execution_enabled':False,
}
save(DOC/'evidencias/execution_contract.json',contracts)
for source,name in [
    (ROOT/'engineering_checks.json','engineering_checks.json'),(ROOT/'activation.json','activation.json'),
    (ROOT/'public_sources/manifest.json','public_sources_manifest.json'),
    (ROOT/'tests-04-integrated/junit.xml','tests_final.xml'),
    (ROOT/'tests-01-before-fix/junit.xml','tests_before_fix.xml'),
]:
    write(DOC/'evidencias'/name,source.read_text(encoding='utf-8'))

path=REPO/'README.md'
text=path.read_text(encoding='utf-8')
begin=text.index('## Resultado mais recente')
end=text.index('## O que está instalado',begin)
text=text[:begin]+'''## Resultado mais recente

A [continuação ER-20260909](docs/continuation/execution_readiness_2026-09-09/RESULTADO.md)
corrigiu cinco falhas da rotina futura e confirmou contratos públicos de
limite, moeda, coleta e tributação. Passaram **153 testes**, Ruff e tipagem
explícita dos dois executores alterados. As versões testadas foram colocadas
nos caminhos da captura já agendada para 11/09 antes das 20:00 de São Paulo.

`bookmakerIsActive=false` indica principalmente falta de coleta ativa pelo
agregador para a casa/jogo. Rejeitar esse feed continua correto, mas o campo
não prova suspensão da oferta pela própria Bet365. Capacidade pessoal, custo
total e validação futura permanecem pendentes; lucro executável não demonstrado.

A [rodada DC anterior](docs/continuation/data_completion_2026-09-09/RESULTADO.md)
preserva 177 históricos, CSV de 380 jogos de 2025 e três capturas de um evento.
O closing condicional perdeu 9,24u com referência comprometida; não é ROI
executável. [Continuidade](docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md)
diária às 19:57, sem ativar coortes ou aplicação operacional completa.

'''+text[end:]
text=text.replace('| Novos dados e recibos |',
    '| Correções e contratos ER | `C:/BRASILEIRAO/work/execution-readiness-2026-09-09` |\n| Novos dados e recibos |')
write(path,text)

path=REPO/'docs/ESTADO_ATUAL.md'
text=path.read_text(encoding='utf-8').replace('rodada DC-20260909','continuação ER-20260909',1)
text=text.replace('A base desta\nrodada foi `5dec2521bab581d5dda104d954f4cc6274b74702`, posterior à pesquisa PF\ne à consolidação documental.',
                  'A base da continuação ER foi `7f18d543891cb3e68bb82c0a0d9fb58f9a8f12c0`, posterior\nà rodada DC e à consolidação dos dados.')
text=text.replace('AUDITORIA/DADOS_COMPLEMENTARES_2026-09-09.json','AUDITORIA/EXECUTION_READINESS_2026-09-09.json')
text=text.replace('Bet365 Brasil inativa nas três','coleta Bet365 Brasil sinalizada como inativa nas três')
text=text.replace('**138 testes passaram**: 80 existentes e 58 novos. Ruff e Pyright dos três\nnovos módulos passaram; uma conferência com Fraction confirmou a conta sem\nimportar esses módulos. Seis fronteiras UTC e execução fora da janela\nverificaram a espera sem consumo de API.',
'''**153 testes passaram**: os 138 da rodada DC mais 15 ensaios novos da rotina
futura. Cinco regressões falharam antes das correções. Ruff e Pyright dos dois
executores alterados passaram. A tipagem dos três módulos puros e a conferência
Fraction anteriores permanecem válidas para o código inalterado. A rotina
corrigida preserva respostas inválidas e produz rejeições rastreáveis.''')
text=text.replace('## Limite da garantia da pasta',
'''## Correções e condições ER

[Resultado ER](continuation/execution_readiness_2026-09-09/RESULTADO.md): cinco
fontes públicas HTTP 200, sem consulta autenticada ou uso de quota de odds.
O campo bookmakerIsActive descreve principalmente coleta do agregador; false
não prova suspensão na casa. Regras públicas de limite e imposto foram
documentadas sem preencher capacidade, moeda ou custo pessoais desconhecidos.

As duas rotinas corrigidas foram copiadas para seus caminhos ativos em
`C:/BRASILEIRAO/work/data-completion-2026-09-09`; versões anteriores, fontes e
recibos novos estão em `C:/BRASILEIRAO/work/execution-readiness-2026-09-09`.
Fixture, horário, quota e agenda não mudaram. Falha HTTP não autoriza retry;
corpo de captura inválido pode e deve receber auditoria de rejeição.

## Limite da garantia da pasta''')
write(path,text)

path=REPO/'docs/continuation/RETOMADA.md'
text=path.read_text(encoding='utf-8').replace('DC-20260909','ER-20260909',1)
text=text.replace('Base da rodada `main` em `5dec2521bab581d5dda104d954f4cc6274b74702`',
                  'Base da continuação `main` em `7f18d543891cb3e68bb82c0a0d9fb58f9a8f12c0`')
text=text.replace('AUDITORIA/DADOS_COMPLEMENTARES_2026-09-09.json','AUDITORIA/EXECUTION_READINESS_2026-09-09.json')
text=text.replace('oferta Bet365 Brasil tinha `bookmakerIsActive=false`','coleta Bet365 Brasil tinha `bookmakerIsActive=false`')
text=text.replace('estado inativo do bookmaker','estado de coleta inativo do agregador')
text=text.replace('Os 138 testes da pesquisa\npassaram.','Os 153 testes da pesquisa\npassaram após as correções ER.')
text=text.replace('## Próxima ação concreta',
'''A [continuação ER](execution_readiness_2026-09-09/RESULTADO.md) corrigiu cinco
falhas na captura/auditoria, com 15 testes novos. A regra pública não fornece
limite pessoal. O flag de coleta não prova suspensão da aposta na casa.
As versões novas já estão nos caminhos ativos; conservar a captura congelada.

## Próxima ação concreta''')
write(path,text)

path=REPO/'docs/PROMPT_PROXIMA_SESSAO.md'
text=path.read_text(encoding='utf-8').replace('[resultado DC](continuation/data_completion_2026-09-09/RESULTADO.md)',
    '[resultado ER](continuation/execution_readiness_2026-09-09/RESULTADO.md)')
text=text.replace('Brasil estava inativa no estado do bookmaker.','Brasil estava sinalizada sem coleta ativa no agregador; isso não prova\nsuspensão da oferta na casa.')
text=text.replace('AUDITORIA/DADOS_COMPLEMENTARES_2026-09-09.json','AUDITORIA/EXECUTION_READINESS_2026-09-09.json')
write(path,text)

path=REPO/'docs/DATA_MAP.md'
text=path.read_text(encoding='utf-8').replace('## Aquisição DC-20260909',
'''## Continuação ER-20260909

`C:/BRASILEIRAO/work/execution-readiness-2026-09-09` contém cinco novas fontes
públicas, contrato de condições, ensaios isolados, hashes de ativação e versões
anteriores das duas rotinas futuras. Os 177 históricos e payloads DC não foram
reescritos. Ensaios sintéticos não são novas observações de mercado.
[Resultado ER](continuation/execution_readiness_2026-09-09/RESULTADO.md) e
[reprodução](continuation/execution_readiness_2026-09-09/REPRODUZIR.md).

## Aquisição DC-20260909''')
write(path,text)

path=REPO/'docs/HISTORICAL_SOURCE_REGISTER.md'
text=path.read_text(encoding='utf-8').replace('## Verificação DC-20260909',
'''## Esclarecimento ER-20260909

O flag bookmakerIsActive indica principalmente coleta ativa no agregador,
não prova de suspensão da oferta na casa. Fontes públicas de limite/moeda e
tributação foram recuperadas sem completar condições pessoais de execução.
[Resultado ER e fontes](continuation/execution_readiness_2026-09-09/RESULTADO.md).
Os registros DC abaixo preservam a classificação de sua rodada.

## Verificação DC-20260909''')
write(path,text)

path=DC/'CONTINUIDADE.md'
text=path.read_text(encoding='utf-8').replace('apesar de preços ativos nas seleções; não homologar esses preços.',
    'apesar de preços ativos nas seleções; não homologar esses preços. O flag\nindica principalmente coleta no agregador, não suspensão provada na casa.\n[Esclarecimento e correções ER](../execution_readiness_2026-09-09/RESULTADO.md).')
text=text.replace('Após a captura, auditar em processo separado e sem credenciais:',
    'As duas rotinas foram corrigidas e ensaiadas na etapa ER. Quando existir\n`followup/capture.json`, inclusive um corpo inválido preservado, auditar em\nprocesso separado e sem credenciais:')
write(path,text)

path=REPO/'HANDOFF.md'
text=path.read_text(encoding='utf-8')
title,rest=text.split('\n',1)
entry='''
## 2026-09-09 — ER-20260909: cinco falhas corrigidas na rotina futura

Base `7f18d543891cb3e68bb82c0a0d9fb58f9a8f12c0`.
[Resultado ER](docs/continuation/execution_readiness_2026-09-09/RESULTADO.md),
[reprodução](docs/continuation/execution_readiness_2026-09-09/REPRODUZIR.md).
Cinco fontes públicas recuperadas; significado de coleta/limite/custos
esclarecido. O flag bookmakerIsActive=false não prova suspensão pela casa.

Corrigidas preservação de resposta inválida, recibo de falha de configuração,
rejeição de schema incompleto, recuperação de pasta parcial e contrato de origem
do recibo. Cinco regressões falharam antes; 153 testes passaram ao final,
incluindo 15 novos. Ruff e tipagem explícita dos dois executores aprovados.
Rotinas corrigidas nos caminhos ativos da coleta independente. Corte, fixture,
quota, agenda e resultados DC intactos. Zero consulta autenticada nesta etapa.

Evidências em `C:/BRASILEIRAO/work/execution-readiness-2026-09-09`; recibo final
em `C:/BRASILEIRAO/AUDITORIA/EXECUTION_READINESS_2026-09-09.json`. Capacidade,
custo total e validação futura pendentes; capital bloqueado. Nenhuma alteração
de H14/H15/H9/A1 ou instalação operacional.

---

'''
write(path,title+'\n'+entry+rest.lstrip('\n'))

path=BASE/'LEIA_PRIMEIRO.md'
text=path.read_text(encoding='utf-8').replace('continuaTION','continuation')
text=text.replace('continuation/data_completion_2026-09-09/RESULTADO.md','continuation/execution_readiness_2026-09-09/RESULTADO.md')
text=text.replace('Passaram 138 testes delimitados.','Passaram 153 testes delimitados após as correções da etapa ER.')
text=text.replace('A rodada DC obteve',
    'A etapa ER corrigiu cinco falhas das rotinas futuras e documentou condições\npúblicas de limite/coleta/tributação. As versões novas estão nos caminhos ativos.\n\nA rodada DC obteve')
write(path,text)

index=REPO/'docs/INDICE_DOCUMENTACAO.md'
old=index.read_text(encoding='utf-8')
categories={m.group(1):m.group(2) for m in re.finditer(r'^\| \[([^\]]+)\]\([^\n]+?\) \| ([^\n]+) \|$',old,re.M)}
files=sorted((p for p in REPO.rglob('*.md') if '.git' not in p.parts),key=lambda p:p.relative_to(REPO).as_posix().lower())
prefix=old.split('## Inventário completo:')[0].replace('continuation/data_completion_2026-09-09/RESULTADO.md',
    'continuation/execution_readiness_2026-09-09/RESULTADO.md')
lines=[prefix.rstrip(),'','## Inventário completo: '+str(len(files))+' documentos','','| Documento | Categoria |','| --- | --- |']
for p in files:
    name=p.relative_to(REPO).as_posix()
    category=categories.get(name,'Continuação ER — resultado, reprodução e protocolo')
    if name.startswith('docs/continuation/execution_readiness_2026-09-09/') and p.name=='PROTOCOL.md':
        category='Protocolo congelado — preservar'
    target=name[5:] if name.startswith('docs/') else '../'+name
    lines.append(f'| [{name}]({target}) | {category} |')
write(index,'\n'.join(lines)+'\n')
save(DOC/'evidencias/manifest.json',{'created_at':datetime.now(UTC).isoformat(),
    'files':{p.name:sha(p) for p in (DOC/'evidencias').iterdir() if p.name!='manifest.json'}})
print(json.dumps({'active_helpers_updated':2,'markdown_index':len(files),'public_sources':len(sources)}))
