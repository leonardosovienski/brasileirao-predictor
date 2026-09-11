"""Dated continuation records derived from preserved test receipts and source inventory."""
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parent
base=Path('C:/BRASILEIRAO')
repo=base/'brasileirao-predictor'
prior=repo/'docs/continuation/completion_2026-09-10'
docs=repo/'docs/continuation/closeout_2026-09-10'
ev=docs/'evidence';ev.mkdir(parents=True,exist_ok=True)
start='9b8cde83f40565278375d343b658afaa385e235e'
def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write(name,value):
    (docs/name).write_text(value,encoding='utf-8')
def digest(path):
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def copy(src,dest):
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    assert digest(src)==digest(dest)

shutil.copyfile(prior/'evidence/.gitattributes',ev/'.gitattributes')
for name in ['before','after','coverage-before','status-before','research-before','supplemental-after','integrated-final']:
    for file in ['junit.xml','isolation.json']:
        copy(root/name/file,ev/name/file)
for name in ['runtime','latency-before','latency-after']:
    for path in (root/name).iterdir():
        if path.is_file() and (path.suffix=='.log' or path.name=='receipt.json'):
            copy(path,ev/name/path.name)
    for path in (root/name/'dotnet-results').rglob('*'):
        if path.is_file() and (path.suffix=='.trx' or path.name=='coverage.cobertura.xml'):
            copy(path,ev/name/path.name)
for path in (root/'quality-first').iterdir():copy(path,ev/'quality-first'/path.name)
for name in ['quality-checks-final.json','ruff-fix-final.log','ruff-format-final.log','ruff-check-final.log',
             'ruff-format-check-final.log','pyright-final.log','integration-test-scope.json']:
    copy(root/name,ev/name)

cases=list(ET.parse(root/'integrated-final/junit.xml').iter('testcase'))
assert len(cases)==275 and all(not any(c.tag in {'failure','error','skipped'} for c in case) for case in cases)
ns={'t':'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
trx=next((root/'latency-after/dotnet-results').glob('*.trx'))
counters=ET.parse(trx).find('.//t:Counters',ns).attrib
assert counters['passed']=='127' and counters['failed']=='0' and counters['notExecuted']=='0'
coverage=ET.parse(next((root/'latency-after/dotnet-results').rglob('coverage.cobertura.xml'))).getroot().attrib
assert min(float(coverage[x]) for x in ('line-rate','branch-rate'))>=0.8
assert json.loads((root/'latency-after/receipt.json').read_text())['server_stopped']
quality=json.loads((root/'quality-checks-final.json').read_text())
assert all(r['exit_code']==0 for r in quality['commands'])

rows=json.loads((prior/'evidence/source-inventory.json').read_text(encoding='utf-8'))
reviewed=set('''brasileirao_predictor/bootstrap.py brasileirao_predictor/evaluator.py brasileirao_predictor/status.py brasileirao_predictor/check_coverage.py brasileirao_predictor/kernel_message.py brasileirao_predictor/research/economic_decision.py brasileirao_predictor/research/calibration_gate.py brasileirao_predictor/research/residual_gate.py brasileirao_predictor/research/market_residual.py brasileirao_predictor/research/temporal_replay.py brasileirao_predictor/research/pit_features/contracts.py brasileirao_predictor/research/pit_features/contextual.py brasileirao_predictor/research/pit_features/absences.py brasileirao_predictor/research/pit_features/lineup.py brasileirao_predictor/research/pit_features/isolated_xg.py brasileirao_predictor/research/pit_features/hierarchical_home_advantage.py brasileirao_scripts/collect_market_research.py dotnet/LineupWorker/Services/WorkerHealth.cs dotnet/LineupWorker/Services/WatchdogStateStore.cs dotnet/LineupWorker/Services/LatencyAuditService.cs tests/test_bet_id.py tests/test_bet_log.py tests/test_market_residual.py tests/test_pit_contextual_features.py tests/test_pit_features_scaffold.py'''.split())
new_files=['tests/test_closeout_integrity.py','tests/test_closeout_coverage.py','tests/test_closeout_status.py',
           'tests/test_closeout_research_inputs.py','dotnet/LineupWorker.Tests/LatencyAuditIntegrityTests.cs']
known={r['path'] for r in rows}
for name in new_files:
    if name not in known: rows.append(dict(path=name,review='semantic_read_with_recorded_findings'))
for row in rows:
    name=row['path']
    if name=='brasileirao_predictor/math_utils.py':
        row.update(review='protected_contract_only_no_execution',protection_reason='A1 imports shin_probabilities; preserved unchanged')
        row.pop('sha256',None)
    elif name in reviewed and not row['review'].startswith('protected'):
        row['review']='semantic_read_with_recorded_findings'
    if not row['review'].startswith('protected'):
        row.update(**digest(repo/name),lines=len((repo/name).read_bytes().splitlines()))
counts={kind:sum(r['review']==kind for r in rows) for kind in sorted({r['review'] for r in rows})}
dump(ev/'source-inventory.json',rows)
dump(ev/'coverage-summary.json',dict(files=len(rows),by_depth=counts,full_semantic_review=False))
extra=['pyproject.toml','compose.yaml','Dockerfile.cli','Dockerfile.kernel','Dockerfile.worker','.dockerignore',
       '.github/workflows/ci.yml','.github/dependabot.yml','contracts/redis-protocol-v2.schema.json','contracts/redis-fair-odds-v2.schema.json']
dump(ev/'build-contract-review.json',[dict(path=p,**digest(repo/p),review='semantic_contract_review_no_deployment') for p in extra])
changed=subprocess.check_output(['git','diff','--name-only'],cwd=repo,text=True).splitlines()
protected={r['path'] for r in rows if r['review'].startswith('protected')}
frozen=json.loads((prior/'evidence/boundary-check.json').read_text())['shared_or_frozen_files_unchanged']
assert not (set(changed)&(protected|set(frozen)))
dump(ev/'boundary-check.json',dict(base=start,protected_files_modified=[],preserved_shared_or_frozen_files=frozen,
    protected_files=len(protected),cohort_evaluators_executed=False,operational_data_read=False,
    metered_or_authenticated_calls=0,new_market_prices=0,new_market_performance=False))
dump(ev/'validation-summary.json',dict(base=start,python_passed=275,python_failures=0,redis_python_passed=27,
    dotnet_passed=127,dotnet_failed=0,dotnet_skipped=0,dotnet_coverage={k:coverage[k] for k in ('line-rate','branch-rate')},
    regressions_python_before=dict(failed=51,passed=1),regressions_dotnet_before=dict(failed=6,passed=119),
    prior_bootstrap_failure_cause='undetermined; repeated full suites now passed; no production stability guarantee',
    quality_scope=quality['files'],full_semantic_review=False,profitability_established=False))

registry=json.loads((prior/'REGISTROS.json').read_text(encoding='utf-8'))
registry.update(round='CLO-20260910',dated_at=datetime.now(UTC).isoformat(),base=start,
                supersedes_current_register=str(prior/'REGISTROS.json'))
additions=[
 ('Livro aceita apenas liquidações reconciliadas','bet_log.py','Resumo somava duplicatas/órfãos; int truncava gols; JSON aceitava NaN/chaves repetidas',
  'Validar JSON, IDs e lucro contra aposta antes de somar; contagens inteiras; retirar CLV automático de banco latest-state',
  'before; integrated-final','Manual e bruto; custos/aceite/concorrência/unidade histórica continuam sem certificação'),
 ('Fechamento usa o último estado do mesmo evento e contrato','data/pit_backfill.py','Último preço válido ressuscitava estado antigo e misturava eventos/linhas',
  'closing/v2: exigir fonte/evento/período; rejeitar mistura, suspensão, desconhecido e conflito final; validar clocks de cura',
  'before; integrated-final','Último estado observado não é closing comercial nem preço executável; schema curated antigo não armazena todos os estados'),
 ('Declaração de prontidão autentica evidência oficial','prediction_protocol.py','OFFICIAL e elegibilidade prospectiva eram emitidos apenas a partir da declaração do chamador',
  'Contrato/v2 com proveniência não verificada; tipos estritos, identidade não branca e cronologia coerente',
  'before; integrated-final','ready significa contrato coerente; proveniência e evidência econômica continuam falsas'),
 ('Cobertura compara o mesmo universo e tolera base vazia','check_coverage.py','Universo vazio dividia por zero; órfãos geravam300% de cobertura',
  'Denominador de eventos distintos, interseções no mesmo universo e N/A quando vazio; conexão fecha em finally',
  'coverage-before; integrated-final','Presença em tabelas não comprova qualidade, validade temporal ou oferta comercial'),
 ('Relatório de estado é somente leitura e informa frescor real','status.py','Abrir status podia criar/migrar banco e classificava cache existente como fresh mesmo desatualizado',
  'Conexão RO/finally, estado stale conforme cache_is_current e ROI indefinido como N/A; rótulo bruto',
  'status-before; integrated-final','Regra compartilhada de frescor continua baseada em contagem/config, não hash dos dados; não é admissão econômica'),
 ('Política shadow recusa probabilidades/stakes inválidos','research/economic_decision.py','NaN, stake negativo e intervalo invertido podiam gerar SHADOW_BET',
  'Validar finitude/domínio/ordem dos limites; stake zero abstém; declarar fração de banca de referência e evidência falsa',
  'research-before; integrated-final','Modelo/offset e condições comerciais não foram revalidados; custos continuam hipóteses de simulação'),
 ('Features contextuais representam entrada e vintage declarados','research/pit_features/contracts.py/contextual.py','Booleano textual viravaTrue; coordenadas impossíveis, gols fracionários e recibo pós-kickoff admitidos',
  'Tipos/limites físicos, contagens inteiras, anúncio até available_at e recebimento pré-jogo; GO estritamente booleano',
  'research-before; integrated-final','Scaffold; ainda exige corte de decisão e recibo/autenticidade externos; sem novo treinamento real'),
 ('Auditoria de latência tem retenção e atualização consistente','dotnet/LineupWorker/Services/LatencyAuditService.cs','Sorted set crescia indefinidamente; read-modify-write perdia versão nova e admitia T4 anterior a T3',
  'Janela por relógio Redis e capacidade, percentis atômicos, CAS com KEEPTTL, rejeitar T4 anterior, excluir clocks inválidos; namespacev2 preserva histórico',
  'latency-before; latency-after','Telemetria diagnóstica com timestamps declarados; não homologa latência de publicação/feed/execução')]
for number,(claim,scope,problem,action,evidence,limit) in enumerate(additions,1):
    cid=f'CLO-A{number:02d}';pid=f'CLO-P{number:02d}'
    registry['claims'].append(dict(id=cid,claim=claim,origin='Inspeção adicional10/09/2026',scope=scope,
        required='Regressão sintética e contrato explícito',found=problem+'; '+action,evidence=evidence,
        conclusion='refutada na base; corrigida e validada no escopo indicado',impact=limit,issue=pid))
    registry['issues'].append(dict(id=pid,claim=cid,problem=problem,type='software/contrato',severity='alta',
        dependencies=scope,action=action,closure_test=evidence,status='validado',limitation=limit))
for issue in registry['issues']:
    if issue['id']=='CPL-P21':
        issue.update(action='Nova suíte completa127/127 após instrumentação; falha original e causa desconhecida preservadas',
                     closure_test='runtime; latency-before; latency-after',status='em investigação',
                     limitation='Inicialização passou em três novas suítes completas; causa da ocorrência anterior continua desconhecida')
    if issue['id']=='CPL-P25':
        issue.update(action=f'Inventário atualizado: {len(rows)} arquivos, profundidade {counts};10 contratos adicionais de build/CI inspecionados',
                     limitation='Cobertura semântica integral de todos os arquivos permanece não demonstrada; não afirmar revisão global concluída')
for claim in registry['claims']:
    if claim['id']=='CPL-A21':claim.update(found='Nova integração completa127/127; cold-start passou novamente',evidence='latency-after',conclusion='parcialmente confirmada no laboratório; causa original desconhecida')
    if claim['id']=='CPL-A25':claim.update(found=f'{len(rows)} arquivos; {counts}',evidence='source-inventory.json; build-contract-review.json')
dump(docs/'REGISTROS.json',registry)
claimmap={c['id']:c for c in registry['claims']}
lines=['# Registros centrais atuais CLO-20260910\n','CPL/RI/IE/BE preservados; esta cópia consolidada acrescenta as correções CLO e atualiza evidências abertas.\n',
       '|Problema/alegação|Escopo|Ação|Estado e limite|','|---|---|---|---|']
for issue in registry['issues']:
    c=claimmap[issue['claim']]
    lines.append(f"|{issue['id']} / {c['id']}|{c['scope']}|{issue['action']}|{issue['status']}; {issue['limitation']}|")
write('REGISTROS.md','\n'.join(lines)+'\n')

write('RESULTADO.md',f'''# Verificação adicional CLO-20260910

Base main/{start}. Foram corrigidos mais oito grupos de falhas materiais, com dados sintéticos isolados. **O mandato integral continua aberto e lucro executável não foi demonstrado.** A entrega é um checkpoint verificável de código, não homologação global.

Os [registros centrais](REGISTROS.md) consolidam26 itens CPL e8 itens CLO. Nenhuma API limitada/autenticada, nova cotação, novo resultado de jogo, aposta ou avaliação econômica foi executada nesta etapa. H14/H15/H9/A1 e dependências identificadas permanecem preservados.

- Técnica: pronta no escopo dos contratos corrigidos; **sistema global não pronto**.275 testes Python em uma execução,27 Redis e127.NET na suíte completa final,0 falhas/0 skips. Ruff/formato e Pyright no conjunto Python alterado passaram. Build.NET sem avisos/erros; cobertura de linhas{float(coverage['line-rate']):.2%} e ramos{float(coverage['branch-rate']):.2%} no lote final.
- Dados: **parciais/insuficientes para lucro executável**. Recibos/documentação CPL preservados; nenhuma nova aquisição nesta etapa. Datas de exemplo nos testes são sintéticas. Metadata de publicação desconhecida não foi transformada em fato.
- Economia: **não mensurável como execução real**. As hipóteses e resultados BE seguem congelados; nenhuma correção técnica foi apresentada como ganho econômico.

As51 falhas Python antes das correções,1 caso já aprovado e6 regressões.NET reproduzidas estão preservadas. A primeira verificação de qualidade encontrou4 linhas longas e2 acessos opcionais sem assert; foram corrigidos, sem supressão de critérios. A falha de inicialização CPL não se repetiu nas novas suítes completas; sua causa segue desconhecida. Não apagar a falha nem inferir estabilidade operacional a partir das passagens.

Inventário: {len(rows)} arquivos de fonte/testes, com profundidade{counts};10 contratos de build/CI adicionais foram lidos. Isso não representa leitura semântica integral de cada arquivo. O [mapa](MAPA_SISTEMA.md) registra decisões e áreas preservadas. A cobertura detalhada é evidence/source-inventory.json.

Mudanças incompatíveis deliberadas: prediction-readiness/2 usa CONTRACT_PRE_MATCH/CONTRACT_LIVE e não certifica procedência; closing/v2 exige contexto de identidade/período e status ACTIVE, abstendo no último estado inválido. O ledger conserva registros históricos, mas novas liquidações não inferem CLV do banco latest-state. Campo legado validated continua apenas como compatibilidade do funil; o resumo declara valores manuais brutos e evidência econômica falsa.

Auditoria.NET: por padrão48h e10.000 registros, configurável entre1..172.800 segundos e1..100.000 registros. O namespacev2 conserva as estatísticas v1. Retenção é por recebimento Redis, sem escolher quais latências descartar pelo seu valor. Clocks inconsistentes ficam fora dos percentis. Contadores locais de chamadas e universo retido são diferentes. A atualização T4 usa CAS e conserva TTL; sem vínculo autenticado ao feed comercial, é diagnóstico.

Nenhum Docker/Compose local foi executado: Docker/Podman continuam não instalados; build Linux/CI remoto não é substituído pelos testes Windows. Arquivos Docker/Compose e contratos foram inspecionados. A configuração de agendamento não foi alterada; o estado ativo da automação permanece não verificável pelo retorno textual da ferramenta.

## Rodada econômica e próxima decisão

'''+(prior/'RESULTADO.md').read_text(encoding='utf-8').split('## Rodada econômica:14 itens\n',1)[1].split('## Continuação necessária',1)[0]+'''
Os14 itens acima preservam a decisão econômica CPL/BE; CLO não consumiu o saldo de GETs nem criou experimento de performance. A informação que decide avanço continua sendo oferta nominal simultânea, estados/revisões e condições verificáveis de preenchimento/custos. A captura DC fixa de11/09/2026 23UTC trata somente sua dupla e não valida a carteira de três pernas.

O próximo passo e os limites estão em PROXIMO_PROMPT.md. Recibo da integração/restauração: C:/BRASILEIRAO/AUDITORIA/VERIFICACAO_ADICIONAL_2026-09-10.json. Arquivos de trabalho e ambientes permanecem em C:/BRASILEIRAO.
''')
write('MAPA_SISTEMA.md',(prior/'MAPA_SISTEMA.md').read_text(encoding='utf-8')+'''
## Atualização CLO

O mapa CPL acima é contexto datado; os registros CLO são o estado atual. Status/coverage passam a ser consumidores RO com fechamento garantido, denominadores no mesmo universo e saída N/A para vazio. Livro reconcilia IDs/valores e não consulta automaticamente fechamento. Readiness/v2 verifica declarações, sem selo oficial. Gate shadow valida domínio finito e features contextuais recusam coerções/recibos tardios. Auditoria.NET tem retenção, percentis de universo atômico e atualização condicionada ao recibo lido.

Inspeções adicionais: kernel_message é parser puro sem I/O no import; WorkerHealth verifica duas funções/mesma sessão e TTL; WatchdogStateStore usa CAS e tempo do Redis. LatencyAuditService alocava strings/JSON apesar do comentário contrário; comentário corrigido. O protocolo não autentica a fonte comercial.

evaluator/backtest/bootstrap legados: cortes por kickoff não comprovam publicação/recepção de labels; predicted_at derivado do último jogo não é horário real de treino. Shin é uma estimativa de margem, não probabilidade verdadeira, e é dependência A1 preservada. Não reavaliados nem admitidos para lucro. calibration_gate/residual_gate e modelos residuais continuam exploração; GO declaratório/intervalos de modelo não autenticam artefatos/custos nem valem como holdout novo. Features absences/lineup/xG/home-advantage são declarações, não modelos implantados.

Decisões: manter caminho BE congelado para investigação de preço; corrigir consumidores/contratos; manter coletas compartilhadas intocadas; não investir em outro tuning antes de resolver a procedência comercial. Pendências preservadas: schema latest-state/cache compartilhado, envelope vazio de escalações, feed exemplo, Elo1500/UNKNOWN no Worker, custos/fills desconhecidos e cobertura semântica global parcial. Essas áreas não estão homologadas.
''')
write('MAPA_DADOS.md',(prior/'MAPA_DADOS.md').read_text(encoding='utf-8')+'''
## Atualização CLO

Nenhuma nova aquisição. curate_odds normaliza published_at UTC quando conhecido e recusa observed/published posteriores ao recibo. SOURCE_REGISTER não concede elegibilidade econômica ao Sofascore por nome. closing/v2 trabalha em linhas explicitamente identificadas com período/status; curated/1 não possui todos esses campos e não reconstrói estados omitidos. O sucessor bitemporal/offline permanece a referência para novos contratos isolados, sem migrar bancos existentes.

Readiness/v2 é declaração de cronologia, nunca prova de recebimento, publicação ou autenticidade. Ledger JSONL mantém unidades brutas e desconhecidos de execução/custos. Novas liquidações usam clv_close=null com motivo, mantendo resultados antigos intactos. Cobertura SQL informa presença no universo definido, não admissibilidade dos dados. Telemetria v2 de Redis mede janela de recibos do serviço, não disponibilidade comercial.
''')
next_prompt='''Leia integralmente o mandato original e PROMPT_FINAL_REVISAO_INTEGRAL_2026-09-09.md em C:/BRASILEIRAO/INSTRUCOES. Continue sozinho, sem agentes e mantendo tudo em C:/BRASILEIRAO. Esta entrega não encerra o mandato.

Confira HEAD/status e AUDITORIA/VERIFICACAO_ADICIONAL_2026-09-10.json, RESULTADO.md, REGISTROS.json, mapas e inventário de docs/continuation/closeout_2026-09-10.275 testes Python,27 Redis e127.NET passaram nas últimas execuções; preserves51 falhas Python/6.NET anteriores. A falha antiga de bootstrap não se repetiu, mas a causa continua desconhecida. Não repetir sucessos sem motivo concreto.

Continue a cobertura semântica necessária por impacto, sem igualar inventário a leitura integral. Respeite a retirada de modelos/avaliações legadas da decisão econômica; não retune pesquisas negativas. Sucessores de schema latest-state/lineups/cache só se necessários ao caminho econômico e comprovadamente independentes de coletas protegidas. A revisão dos modelos residuais/artifacts ainda não equivale a homologação. O journal é manual e não certifica concorrência/custos/moeda histórica. Worker/feed comercial permanece exemplo sem dados e contrato admissíveis.

Preserve H14/H15/H9/A1, resultados, avaliadores, claims, travas, agendas e dependências. Não altere db/ratings/model/xg/cron/identity/math_utils/A1, TheOddsApi/bookmaker_stability nem serving_evaluator misto. Não consulte resultados/coortes, não liquide nem execute avaliadores. Toda execução financeira é simulada, capital desabilitado.

BE congelado:226 carteiras anônimas hipotéticas; modelo de gols reprovado. Próxima informação decisiva é oferta nominal/simultânea e condições verificáveis de preenchimento/custos. Nenhum novo experimento ou coleta sem protocolo prévio, plano/quota/custos/reservas. Não repetir lotes íntegros ou inferir recebimento histórico a partir de captura atual.

Leia CONTINUIDADE DC antes de qualquer captura. Fixtureid1000032566887012, Pinnacle/bet365.bet.br, decisão11/09/2026 23UTC, kickoff12/09 00UTC. Janela22:58:30..<23UTC, helperinicial22:55..22:59:15, uma chamada limitada/reserva20/marcador anterior. Não antecipar, mudar horários/casas, duplicar automação completar-dados-do-brasileir-o nem capturar desfechos. A automação pertence à tarefa01a08756-2962-7c43-9773-c790cc81329d; o retorno da consulta foi só um cartão, sem prova textual de ACTIVE. Helpers preservados.

Atualize registros/guias e produza backups verificáveis em cada integração. Não declare revisão integral, fonte admissível ou lucro sem prova no escopo correspondente. Continue o trabalho necessário, viável e autorizado.
'''
write('PROXIMO_PROMPT.md',next_prompt)
(base/'INSTRUCOES/PROXIMO_PROMPT_APOS_VERIFICACAO_ADICIONAL_2026-09-10.md').write_text(next_prompt,encoding='utf-8')
write('REPRODUZIR.md','''# Reprodução isolada

Ambientes existentes e versões: ver recibos CPL e quality-checks-final.json. Python explícito C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe. Runners em C:/BRASILEIRAO/work/closeout-2026-09-10.

run_isolated.py exige pasta nova e lista explícita de testes; integration-test-scope.json registra34 arquivos. Ele impede rede/subprocessos/SQLite fora do destino sintético, não é licença para executar testes protegidos. integrated-final passou275; a única tentativa bloqueada foi socket.bind, sem conexão. O guard não é herdado automaticamente por processos filhos: CLIs da wheel usam ambiente explicitamente controlado.

O laboratório tools/runtime_lab/run.py exige Redis portátil comSHA, DB13/14/15 e run_id próprios. Seus recibos registram comandos, logs, encerramento e TRX.127.NET/27 Python Redis finais. Não reutilizar saída ou endpoint com dados. Não rodar Compose/cron/status/coletores contra destinos operacionais para reproduzir esta entrega.

check_changed.py roda Ruff e Pyright apenas no diff Python. build_package.py gera wheel/sdist offline, instala em destino explícito com --python RI e valida sete comandos de CLI com entradas sintéticas. backup_delivery.py confere bytes, ZIP CRC e restaura bundle em Git bare novo. Use pastas novas ao repetir; os scripts recusam sobrepor evidências.
''')

prefix='''**Atualização CLO-20260910:** oito grupos adicionais de falhas corrigidos;275 testes Python,27 Redis e127.NET aprovados. Mandato integral permanece aberto; dados comerciais insuficientes e lucro executável não demonstrado. [Resultado atual](LINK/RESULTADO.md), [registro central](LINK/REGISTROS.md), [continuação](LINK/PROXIMO_PROMPT.md).

'''
backup=root/'previous-guides';backup.mkdir(exist_ok=True)
guides=['README.md','HANDOFF.md','docs/ESTADO_ATUAL.md','docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md']
for name in guides:
    path=repo/name;old=path.read_text(encoding='utf-8')
    if '**Atualização CLO-20260910:**' in old:continue
    saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,saved)
    link='docs/continuation/closeout_2026-09-10' if '/' not in name else 'closeout_2026-09-10' if name.endswith('RETOMADA.md') else 'continuation/closeout_2026-09-10'
    if name=='README.md':
        lines=old.splitlines(keepends=True);old=lines[0]+'\n'+prefix.replace('LINK',link)+''.join(lines[1:]).lstrip()
    else:old=prefix.replace('LINK',link)+old
    path.write_text(old,encoding='utf-8')
guide=base/'LEIA_PRIMEIRO.md'
old=guide.read_text(encoding='utf-8')
if '**Atualização CLO-20260910:**' not in old:
    copy(guide,backup/'LEIA_PRIMEIRO.md')
    guide.write_text(prefix.replace('LINK','brasileirao-predictor/docs/continuation/closeout_2026-09-10')+old,encoding='utf-8')
print(json.dumps(dict(inventory=len(rows),depth=counts,python=275,dotnet=127,records=len(registry['issues'])),ensure_ascii=False))
