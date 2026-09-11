"""Consolidate actual receipts; preserve older guides and frozen registers."""
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent
base = Path('C:/BRASILEIRAO')
repo = base/'brasileirao-predictor'
docs = repo/'docs/continuation/resolution_2026-09-10'
evidence = docs/'evidence'
evidence.mkdir(exist_ok=False)
previous = root/'previous-guides'
previous.mkdir(exist_ok=False)

def digest(path):
    raw=path.read_bytes()
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text.strip()+'\n',encoding='utf-8')

def copy(path,relative):
    target=evidence/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,target)
    assert digest(path)==digest(target)

git=lambda *args:subprocess.check_output(['git',*args],cwd=repo).decode().strip()
assert git('rev-parse','HEAD')=='3bda4c4b0abd9b94902f77509d7d211ac30e96f7'
guides=['README.md','HANDOFF.md','docs/ESTADO_ATUAL.md','docs/DATA_MAP.md','docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md']
for name in guides:
    target=previous/name;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(repo/name,target)
shutil.copyfile(base/'LEIA_PRIMEIRO.md',previous/'LEIA_PRIMEIRO_ROOT.md')

accepted=['python-integrated','player-stats-after','kernel-lifecycle-after','structural-after','restore-edges-after-02','promotions-after','coverage-after','odds-import-integrated','live-settlement-after']
cases={}
for name in accepted:
    path=root/name/'junit.xml'
    tree=ET.parse(path)
    for suite in tree.findall('testsuite'):
        assert all(int(suite.attrib.get(k,0))==0 for k in ('failures','errors','skipped')),name
    for case in tree.iter('testcase'):
        cases[(case.attrib['classname'],case.attrib['name'])]=name
test_summary=dict(scope='explicit isolated synthetic suites; not whole CI',unique_passed=len(cases),runs=accepted,
                 cases=[dict(classname=c,name=n,latest_evidence=r) for (c,n),r in sorted(cases.items())])
dump(evidence/'python-validation.json',test_summary)
# Preserve failures as well as successful test receipts. Only these public synthetic outputs.
for folder in sorted(root.iterdir()):
    if not folder.is_dir() or folder.name.startswith(('quality','package','installed-cross','node','ruff','temp','tmp')):
        continue
    for name in ('junit.xml','isolation.json','receipt.json','plan.json','dotnet-restore.log','dotnet-build.log','dotnet-test.log'):
        if (folder/name).is_file():
            copy(folder/name,Path(folder.name)/name)
for path in sorted((root/'installed-full-after/dotnet-results').rglob('*')):
    if path.is_file() and path.suffix in {'.xml','.trx'}:
        copy(path,Path('installed-full-after/dotnet-results')/path.relative_to(root/'installed-full-after/dotnet-results'))
for name in ('quality-checks-final.json','ruff-check-final.log','ruff-format-check-final.log','pyright-final.log','semantic-review-notes-05.json','semantic-pending-05.json','PLANO.md'):
    copy(root/name,Path(name))

old=repo/'docs/continuation/reconciliation_2026-09-10'
inventory=json.loads((old/'evidence/source-inventory.json').read_text(encoding='utf-8'))
notes=json.loads((root/'semantic-review-notes-05.json').read_text(encoding='utf-8'))
read={p for b in notes['batches'] for p in b['paths']}
read.add('scripts/migration/build_data_archive.py')
for row in inventory:
    if row['path'] in read:
        row['review']='semantic_read_with_recorded_findings'
    if row['review']=='protected_contract_only_no_execution':
        assert row['path'] not in git('diff','--name-only').splitlines(),row['path']
pending=[r for r in inventory if r['review']=='inventory_static_or_targeted_review_only']
dump(evidence/'source-inventory.json',inventory)
dump(evidence/'semantic-remaining.json',pending)
coverage=dict(baseline_files=len(inventory),depth=dict(Counter(r['review'] for r in inventory)),remaining_files=len(pending),
              all_sources_semantically_reviewed=False, note='New files and changed versions reviewed/tested separately. Archive builder full read after notes05: exclusive output, hashes, traversal/collision checks, SQLite-map preservation; nested-ZIP checks are metadata, not payload authenticity. Its filename policy does not certify arbitrary data as safe code-free content.')
dump(evidence/'review-coverage.json',coverage)
helpers={}
for name,expected in [('followup_capture.py','31de8315c687cc596ae3fb9aebd221701e9f6df690903248c15dfb9b84b33d88'),('audit_followup.py','ebce7ddeb384b347be4985b7a3812a1b83c7dfaceafdb3e2a6cb00f7e2d09a24')]:
    path=base/'work/data-completion-2026-09-09'/name
    helpers[name]=digest(path)
    assert helpers[name]['sha256']==expected
dump(evidence/'boundary-check.json',dict(at=datetime.now(UTC).isoformat(),protected_inventory_source_paths_not_changed=True,dc_helpers=helpers,
    operational_databases_restored=False,protected_results_evaluated=False,financial_execution=False,
    isolation_erratum='odds-display-before imported legacy module with load_config side effects. No values printed. Later import side effect removed and test audit guard explicitly blocks repo/config.yaml.'))

registry=json.loads((old/'REGISTROS.json').read_text(encoding='utf-8'))
registry.update(round='RES-20260910',dated_at=datetime.now(UTC).isoformat(),base=git('rev-parse','HEAD'),
    previous_registry='docs/continuation/reconciliation_2026-09-10/REGISTROS.json',mandate_complete=False)
updates={
'CPL-P21':('validado','Instrumentação por fase, espera de import/JIT antes da cotação sintética, launcher instalado sem PYTHONPATH e health leve. 160/160 .NET e regressões de lifecycle passaram.','Causa específica do timeout antigo continua desconhecida; falha preservada. Fechamento restrito à recuperação/diagnóstico atuais, não à atribuição retroativa.'),
'CPL-P22':('bloqueado','Sucessores isolados de dados/replay e contratos reais de entrada implementados. Cache, treino, espelho e coletores compartilhados das coortes permanecem byte-preservados.','Correção da operação compartilhada exige separação demonstrada da coleta protegida; não foi implantada.'),
'CPL-P23':('bloqueado','Removidos endpoint de exemplo e fallback silencioso de Elo/posição; modo sintético explícito. Feed normalizado tem clocks, revisões, suspensão, limites e invalidação. Entradas reais exigem identidade, Elo, posição, cobertura VORP e procedência temporal. Testes .NET passaram.','Contrato pronto; ponte comercial e dados de modelo autenticados não foram fornecidos nem homologados. A parte de software está validada, mas o requisito comercial continua aberto.'),
'CPL-P24':('bloqueado','Consulta anterior retorna cartão sem configuração legível; helpers DC novamente conferidos por SHA. Nenhuma agenda duplicada/alterada.','Estado ativo e recibo da janela continuam não comprovados; não inferir ausência/atividade a partir de TOML ausente.'),
'CPL-P25':('corrigindo',f'Revisão ampliada: {coverage["depth"]}. Todos os scripts não protegidos do inventário foram lidos semanticamente; restam {len(pending)} fontes/testes com revisão estática ou dirigida, enumerados em evidence/semantic-remaining.json.','Não há base para afirmar que todos os arquivos foram revisados integralmente. Testes aprovados não encerram esse requisito.'),
'CPL-P26':('bloqueado','Tentativa pública única de catálogo Polymarket preservada com orçamento, sem credenciais/retries; ConnectionError sem resposta útil. Contratos de dados aprimorados; BE congelado e captura futura DC preservados.','Nenhuma nova cotação nominal simultânea com condições de execução, custos e fills verificáveis. Erro de conexão não prova ausência de oportunidade.'),
'RCA-P04':('validado','Gate v3 conta eventos, identifica PSR como diagnóstico e impede promoção por DSR fornecido. Favorável retorna PENDING_DESIGN, negativos NO_GO. Regressões antes/depois passaram.','O software não aprova inferência sem desenho. Histórico real de tentativas e desenho temporal continuam necessários antes de novo desempenho; não foram fabricados.'),
'RCA-P05':('validado','Replay v3 valida identidade/labels/cortes, treina apenas com labels maduros e usa carteira Decimal com stakes, custos, reserva, pendências e reconciliação independente.','Somente back binário com full fill hipotético; não representa execução aceita. Sem desempenho real novo.'),
'RCA-P06':('validado','Curated v2 preserva revisões, status, período e linha; leitura por corte evita ressuscitar preços. v1 recusado sem alteração.','Validação sintética do sucessor; não migra operação nem recupera clocks que a fonte nunca forneceu.'),
'RCA-P07':('validado','Envelopes v2 imutáveis com vazio/remoção/indisponível/inválido, hashes, criação exclusiva, revisão e conflito. Testes antes/depois passaram.','Sucessor opt-in, coletor legado protegido preservado; sem ingestão real nesta etapa.'),
'RCA-P08':('validado','Lua compara T3 por ticks UTC de 19 dígitos; chegada antiga não substitui/renova TTL, retry preserva T4 e revisão reseta T4 sem renovar TTL.','Redis descartável; formato legado de telemetria requer migração explícita.'),
'RCA-P09':('bloqueado','Compose v5.5.0 baixado com SHA oficial; config validado sem .env real e quatro serviços. Runtime Windows Python/Redis/.NET validado.','WSL não instalado, Docker/Podman não disponíveis, sem daemon Linux. Containers e CI global desta versão não executados. Config válido não substitui homologação Linux.'),
'RCA-P10':('bloqueado','Livro coordena leitura/escrita dos dois arquivos, unidades históricas, ordem de fluxos, ambiguidades, capital e drawdown ajustado por aportes. Testes passaram.','Software validado para entradas declaradas. Moeda/câmbio/saldo/custo manual não são fatos comerciais autenticados; transação global entre arquivos não é prometida.'),
'RCA-P11':('bloqueado','Restore isolado verifica origem/destino/manifesto, preserva falhas, recusa symlinks/junctions/destinos aninhados e usa URI SQLite correta. Testes passaram.','Restauração de operação protegida e arquivos nunca recebidos não demonstrável nesta autorização. Entrega Git/ZIP recebe recibo separado.')}
for row in registry['issues']:
    if row['id'] in updates:
        status,action,limit=updates[row['id']]
        row.update(status=status,action=action,limitation=limit,updated_in='RES-20260910',evidence='docs/continuation/resolution_2026-09-10/evidence')
        claim=next((c for c in registry['claims'] if c['id']==row['claim']),None)
        if claim:
            claim.update(found=action,impact=limit,evidence=row['evidence'],conclusion='parcialmente confirmada no escopo corrigido; limites explícitos' if status=='validado' else 'parcialmente confirmada; requisito integral ainda não fechado')
extra=[
('Preços residuais usavam casa ofertante como referência, descartavam pendências e omitiam disponibilidade de contexto','reference fixed-house, market/period, revisions, clock/skew/age and explicit abstentions','test_resolution_residual_dataset'),
('Health/imports pesados e PubSub sem limite de handlers','kernel_cli leve, timeouts Redis, máximo 32 handlers PubSub e 32 poller independente','test_resolution_kernel_lifecycle'),
('Parâmetros não finitos ou grade inválida chegavam ao Numba','domínio numérico antes de aquecimento/cliente','test_resolution_kernel_params'),
('Detector aceitava oferta soft antiga e inputs inválidos; raiz power limitada artificialmente','oferta e referência com idade; cópia imutável; bracket expansível e finitude','test_resolution_structural_edge'),
('Promovidos tinham coerções silenciosas, duplicatas e temporadas incompletas','schema estrito, chaves JSON únicas e quatro posições/equipes por temporada','test_resolution_promotions'),
('Player stats carimbava pós-jogo como pré-jogo e aceitava números inválidos','disponibilidade real declarada v2; ausente permanece desconhecida; valida contagens e cache','test_resolution_player_stats'),
('Cobertura tratava zero denominador/arquivo ausente como aprovação e publicava .NET antigo','N/A, exige arquivos/blocos/branches, inclui CLI e protocolo; .NET vindo de recibo separado','test_resolution_coverage'),
('Importador podia gravar em DB existente, publicar parcial e aceitar odds/contagens inválidas','nova saída exclusiva após integrity/fsync; bytes/hash da mesma fonte; rejeições explícitas','test_resolution_historical_import'),
('Exibição de odds anunciava janela validada e emitia comandos de aposta sem evidência','somente diagnóstico; mercado completo, casas únicas, clocks e preços válidos; sem config no import','test_resolution_odds_shop'),
('Liquidação diagnóstica aceitava evento/placar/probabilidades inválidos e concorrência/retry inseguros','v2 com identidade, hashes de previsão/fatos/recibo e writer lock; conserva primeiro recibo','test_resolution_live_settlement')]
for index,(problem,action,test) in enumerate(extra,1):
    pid=f'RES-P{index:02d}';aid=f'RES-A{index:02d}'
    registry['issues'].append(dict(id=pid,claim=aid,problem=problem,type='software/contrato',severity='alta',dependencies=test,action=action,closure_test=test,status='validado',limitation='Dados sintéticos; não demonstra lucro/comércio nem modifica pesquisa congelada.'))
    registry['claims'].append(dict(id=aid,claim='O contrato corrige a falha descrita em '+pid,origin='RES-20260910',scope=test,required='regressão falha antes e passa depois',found=action,conclusion='confirmada no escopo sintético',impact='integridade do caminho isolado',evidence='evidence/python-validation.json',issue=pid))
registry['states']=dict(software='correções delimitadas validadas; revisão global incompleta',data='parcial; disponibilidade comercial não comprovada',economics='lucro executável não demonstrado; capital false')
registry['summary']=dict(issues=len(registry['issues']),statuses=dict(Counter(r['status'] for r in registry['issues'])),original_14=[dict(id=k,status=v[0]) for k,v in updates.items()],new_regressions=len(extra))
dump(docs/'REGISTROS.json',registry)
rows=['| ID | Estado | Correção / ação | Limite |','| --- | --- | --- | --- |']
for r in registry['issues']:
    rows.append('| '+' | '.join(str(r.get(k,'')).replace('|','/').replace('\n',' ') for k in ('id','status','action','limitation'))+' |')
write(docs/'REGISTROS.md','# Registro central — RES-20260910\n\nGerado de REGISTROS.json. Registros antigos preservados; correção de software não fecha automaticamente requisitos comerciais/protegidos.\n\n'+'\n'.join(rows))
count=len(cases)
result=f'''# Resultado das correções — RES-20260910

Foram implementadas correções nos componentes que sustentavam as 14 pendências, com regressões antes/depois, além de dez falhas adicionais encontradas na leitura. O mandato global ainda não está integralmente concluído: há dependências protegidas/externas e {len(pending)} arquivos do inventário cuja revisão ainda é estática ou dirigida. Não se declara zero pendências.

O registro único é [REGISTROS.json](REGISTROS.json), com versão legível em [REGISTROS.md](REGISTROS.md). Os contratos e compatibilidade estão em [CONTRATOS.md](CONTRATOS.md). Fontes, falhas e testes estão em evidence/. A base desta etapa é main/3bda4c4b0abd9b94902f77509d7d211ac30e96f7; o SHA integrado e a restauração ficam no recibo C:/BRASILEIRAO/AUDITORIA/RESOLUCAO_2026-09-10.json.

## O que mudou

Carteira e replay passaram a reconciliar caixa, principal, custos, reservas e resultados pendentes. A materialização exige casa ofertante fixa excluída da referência, relógios válidos e contexto disponível. Curated v2 e envelopes de escalação preservam revisões/remoções e não recuperam estados antigos depois de suspensão. O gate estatístico bloqueia aprovação sem desenho e histórico de tentativas.

O Worker exige entradas de modelo com identidade, versão, Elo, posição e cobertura VORP; fallback demonstrativo passou a ser explícito. Feed vazio está desativado, mensagens comerciais precisam cumprir o contrato normalizado e o cache invalida preço suspenso, conflitante, antigo ou desconectado. A telemetria mantém ordem por T3 sem renovação indevida de TTL. O kernel tem health leve, validação numérica antes do JIT e concorrência limitada.

Importação histórica publica somente um novo DB íntegro; recuperação confere também o destino e rejeita links/junctions. Estatísticas de jogadores não inventam disponibilidade pré-jogo. Promoções exigem schema completo. Cobertura não aprova denominador vazio/arquivos ausentes. Odds exibidas são diagnóstico; comandos de aposta e alegações de janela validada foram retirados. Liquidação diagnóstica valida o jogo e o vetor de probabilidades, coordena escritores e conserva o primeiro recibo em retries.

## Validação e limites

{count} casos Python distintos passaram nas suítes explícitas, sem contar repetições; detalhes em evidence/python-validation.json. Ruff, formato e Pyright passaram nos 41 arquivos Python alterados, incluindo pesquisa, testes e ferramentas que a configuração global normalmente exclui. A suíte .NET completa passou 160/160, sem skips, com restore locked/build warnaserror. Cobertura .NET: 86,91% de linhas e 81,90% de branches. O Redis portátil descartável foi encerrado. Não é homologação de produção.

Compose config passou para init-data/kernel/redis/worker com feed e modo sintético desabilitados por padrão. Não há engine Linux/WSL instalado neste host; containers e CI global da versão não foram executados. A aprovação de tipagem/testes delimitados não afirma a cobertura global Python. Pacote final, instalação e ensaio entre processos terão seus recibos anexados antes da integração.

Erros intermediários foram preservados: timeout antigo de causa desconhecida, cotação de fixture envelhecida durante inicialização, fsync em descritor somente leitura no Windows e diagnósticos de tipagem. O baseline odds-display-before importou o módulo legado que chama load_config; nenhum valor foi impresso, mas não se afirma ausência absoluta de acesso à configuração nessa reprodução. A correção removeu o efeito no import e o guard passou a bloquear config.yaml.

## Decisão econômica

A pergunta principal continua: existe oferta nominal observada simultaneamente com referência independente que sobreviva a custos e preenchimentos verificáveis? Ela tem prioridade porque um modelo bem calibrado não cria uma oferta executável. Não houve novo teste de desempenho nem seleção de variante nesta etapa; os estudos BE e negativos anteriores estão preservados.

Foi feita uma tentativa pública delimitada de catálogo de mercados, com 1 GET, sem credenciais, retries, ordens ou resultados: falhou com ConnectionError antes de obter resposta útil. Isso demonstra a falha dessa tentativa, não a inexistência de oportunidade. Cotações/capacidade/aceitação/custos pessoais continuam sem evidência suficiente; zero não substitui desconhecido.

A descoberta decisiva é a distância entre cálculo condicionado a full fill e lucro executável: corrigir a carteira e a informação temporal elimina aprovações indevidas, mas não fornece aceitação comercial. Trocar/tunar modelo perde prioridade enquanto essa entrada não existe. A próxima informação decisiva é o recibo de oferta nominal dentro do corte congelado, acompanhado de regras, capacidade e custos admissíveis. A captura DC mantém decisão em 11/09/2026 23:00 UTC, reserva20 e helpers intactos; a agenda não foi duplicada nem alterada. Capital permanece desabilitado.

## Trabalho que permanece

Concluir a revisão semântica enumerada em evidence/semantic-remaining.json, principalmente testes e contratos de infraestrutura. Não executar fontes legacy que fazem consultas/treino no import. Corrigir dependências compartilhadas exige separar comprovadamente a operação protegida. Fonte comercial, estado legível da agenda, engine Linux e restauração operacional têm requisitos próprios ainda não satisfeitos. Essas limitações não foram convertidas em sucesso documental.
'''
write(docs/'RESULTADO.md',result)
next_prompt='''Continue em C:/BRASILEIRAO/brasileirao-predictor, solo. Leia os dois mandatos em C:/BRASILEIRAO/INSTRUCOES e o registro RES-20260910. Confira HEAD/alterações, recibo AUDITORIA/RESOLUCAO_2026-09-10.json e processos reais. Preserve H14/H15/H9/A1, suas dependências de coleta, dados, claims e agendas; capital false. Não repetir desempenho BE nem o que já passou sem mudança/concernimento. Complete evidence/semantic-remaining.json (revisão ainda dirigida/estática, não semântica integral); consolide os achados com notas05 e os sucessores corrigidos. Root/work/resolution-2026-09-10 contém testes antes/depois, runners isolados e instalação. As correções não migraram operação. P22/P23/P24/P26/P09/P10/P11 continuam com limites protegidos ou externos especificados, não podem virar zero por reclassificação. Preserve janela DC de 11/09/2026 23:00 UTC e reserve20; não criar outra agenda. Corrija o que for autorizado e verificável e só feche com evidência.'''
write(docs/'PROXIMO_PROMPT.md','# Continuação do trabalho\n\n'+next_prompt)
write(base/'INSTRUCOES/PROXIMO_PROMPT_APOS_RESOLUCAO_2026-09-10.md',next_prompt)
write(docs/'REPRODUZIR.md',f'''# Reprodução delimitada

Todos os caminhos são C:/BRASILEIRAO. Python 3.13.12/extras em work/revisao-integral-2026-09-09/venv; SDK .NET 10.0.401 e NuGet no mesmo workspace; Redis 8.2.9 portátil em work/implementacao-2026-09-10/software. Dependências verificadas na RCA não equivalem a serviços ativos. O launcher run_isolated.py limpa ambiente, bloqueia rede/subprocessos e escritas fora de nova saída, DBs/coortes/config privados; não usar pytest global.

Casos e nomes exatos das {len(accepted)} suítes estão em evidence/python-validation.json e isolation.json correspondentes. Execute somente allowlist revisada em diretório novo pelo runner, com -I -B. Runners e comandos completos: C:/BRASILEIRAO/work/resolution-2026-09-10. O laboratório .NET exige porta 26380 livre antes de iniciar seu próprio Redis e verifica PID/run_id/SHA; limpa somente o processo próprio. O recibo guarda restore/build/test e tempos, não são medidas de latência de produção.

A wheel final é derivada do sdist offline e instalada em venv separado sem PYTHONPATH, com reutilização explícita das dependências isoladas já verificadas. Isso não representa reinstalação independente da cadeia inteira. Recibo package-final/receipt.json e installed-cross-final/receipt.json descrevem resultados reais. Build/CLI help/health usam dados sintéticos. Não executar CLI de coleta, backfill ou settlement em caminhos operacionais.
''')
rel='docs/continuation/resolution_2026-09-10'
write(repo/'README.md',f'''# brasileirao-predictor

Pesquisa e previsão do Brasileirão com Python e laboratório Redis/.NET. Estado corrente: RES-20260910. Correções de caixa, causalidade, persistência, runtime e entradas validadas; revisão global ainda incompleta e lucro executável não demonstrado.

[Resultado e limites]({rel}/RESULTADO.md), [registro central]({rel}/REGISTROS.md), [contratos]({rel}/CONTRATOS.md), [reprodução]({rel}/REPRODUZIR.md). {count} casos Python distintos e 160 testes .NET passaram em ambientes isolados. Compose config validado; execução Linux/CI global e conexão comercial não homologadas.

Capital desabilitado. Trabalho em C:/BRASILEIRAO, solo; H14/H15/H9/A1 e operação protegida preservados. [Estado](docs/ESTADO_ATUAL.md), [dados](docs/DATA_MAP.md), [retomada](docs/continuation/RETOMADA.md). Guias anteriores preservados no Git e em work/resolution-2026-09-10/previous-guides. Código demonstrativo não comprova oferta aceita.
''')
write(repo/'HANDOFF.md',f'# Handoff — RES-20260910\n\nCorreções extensas implementadas e validadas; o mandato global continua incompleto. Leia [resultado]({rel}/RESULTADO.md), [registro central]({rel}/REGISTROS.json) e [continuação]({rel}/PROXIMO_PROMPT.md).\n\n{count} testes Python distintos; 160 .NET; qualidade dos 41 Python alterados. Pacote e entrega recuperável têm recibos próprios. Fronteiras H14/H15/H9/A1 permanecem. Não fazer migração operacional ou novo tuning para produzir lucro. Todos os arquivos em C:/BRASILEIRAO. Base desta etapa 3bda4c4; conferir commit no recibo AUDITORIA/RESOLUCAO_2026-09-10.json. Histórico RCA/BE e guias anteriores preservados.')
write(repo/'docs/ESTADO_ATUAL.md','# Estado — RES-20260910\n\nSoftware: correções delimitadas validadas; revisão integral ainda não concluída. Dados: parciais, relógios históricos/comerciais insuficientes. Economia: lucro executável não demonstrado; capital false.\n\nLeia [resultado](continuation/resolution_2026-09-10/RESULTADO.md), [registro único](continuation/resolution_2026-09-10/REGISTROS.json) e [contratos](continuation/resolution_2026-09-10/CONTRATOS.md). Contagens/status derivam desse registro, sem apagar pendências externas. Recibo Git/ZIP em C:/BRASILEIRAO/AUDITORIA/RESOLUCAO_2026-09-10.json.')
write(repo/'docs/continuation/RETOMADA.md','# Retomada — RES-20260910\n\nLeia [continuação](resolution_2026-09-10/PROXIMO_PROMPT.md), [resultado](resolution_2026-09-10/RESULTADO.md) e [registro](resolution_2026-09-10/REGISTROS.json). Work: C:/BRASILEIRAO/work/resolution-2026-09-10. Mandatos, proteção, capital false e janela DC permanecem. Não repetir os testes aprovados sem motivo; completar a revisão pendente e dependências admissíveis. Não supor que o primeiro prompt terminou.')
write(repo/'docs/DATA_MAP.md','# Dados — RES-20260910\n\n[Mapa histórico por requisito](continuation/reconciliation_2026-09-10/MAPA_DADOS.md), [contratos atuais](continuation/resolution_2026-09-10/CONTRATOS.md) e [registro](continuation/resolution_2026-09-10/REGISTROS.json).\n\nNesta etapa, nenhuma base comercial nova foi admitida. Testes usam dados sintéticos em C:/BRASILEIRAO/work/resolution-2026-09-10; catálogo público falhou e tem recibo. Curated v2, envelopes e replay isolados não migram bancos protegidos. Estatísticas pós-jogo exigem available_at real; odds históricas sem relógios permanecem cenário.\n\nDados recebidos: C:/BRASILEIRAO/DADOS_PRESERVADOS; captura DC: work/data-completion-2026-09-09; estudo congelado BE: work/economic-search-2026-09-10. Nenhum arquivo da máquina antiga é presumido recebido. Ambientes RI/IE e dependências de sistema são separados de dados. Backups/ENTREGAS/AUDITORIA contêm recibos de código, distintos de restauração operacional.')
write(repo/'docs/INDICE_DOCUMENTACAO.md','# Índice — RES-20260910\n\n- [Resultado](continuation/resolution_2026-09-10/RESULTADO.md)\n- [Registro central](continuation/resolution_2026-09-10/REGISTROS.md)\n- [Contratos corrigidos](continuation/resolution_2026-09-10/CONTRATOS.md)\n- [Reprodução](continuation/resolution_2026-09-10/REPRODUZIR.md)\n- [Continuação](continuation/resolution_2026-09-10/PROXIMO_PROMPT.md)\n- [Matriz integral dos mandatos na RCA](continuation/reconciliation_2026-09-10/MATRIZ_MANDATO.md)\n- [Histórico reconciliado](continuation/reconciliation_2026-09-10/HISTORICO.md)\n- [Sistema na RCA](continuation/reconciliation_2026-09-10/MAPA_SISTEMA.md)\n\nDocumentos RCA e anteriores são fotografias datadas, preservadas. A evolução RES está no registro corrente; não são listas concorrentes de estado.')
write(base/'LEIA_PRIMEIRO.md','# BRASILEIRAO — RES-20260910\n\nCheckout C:/BRASILEIRAO/brasileirao-predictor. Leia README.md e docs/continuation/resolution_2026-09-10/RESULTADO.md. Correções implementadas/validadas, revisão integral ainda incompleta e lucro executável não demonstrado.\n\nAmbientes/evidências em work/resolution-2026-09-10; recibo da integração/backup em AUDITORIA/RESOLUCAO_2026-09-10.json. Continuação: INSTRUCOES/PROXIMO_PROMPT_APOS_RESOLUCAO_2026-09-10.md. H14/H15/H9/A1, coletas/claims/agendas protegidas; capital false. Tudo em C:/BRASILEIRAO; solo.')
dump(evidence/'manifest.json',{p.relative_to(docs).as_posix():digest(p) for p in sorted(evidence.rglob('*')) if p.is_file()})
print(json.dumps(dict(python_unique=count,coverage=coverage,registry=registry['summary']),ensure_ascii=False))
