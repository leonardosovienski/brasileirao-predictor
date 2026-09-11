"""Create a single current checkpoint and reconcile every mandate section with evidence."""
import collections
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent
base = Path('C:/BRASILEIRAO')
repo = base / 'brasileirao-predictor'
start = '6c850454418a1c7e878fdb6a461dea509571caec'
prior = repo / 'docs/continuation/artifact_integrity_2026-09-10'
docs = repo / 'docs/continuation/reconciliation_2026-09-10'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip() == start
docs.mkdir(exist_ok=False)
evidence = docs / 'evidence'
evidence.mkdir()

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + '\n', encoding='utf-8')

def dump(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2))

def digest(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    assert digest(source) == digest(target)

validation = {}
for phase in ('before', 'after', 'final'):
    cases = list(ET.parse(root / phase / 'junit.xml').getroot().iter('testcase'))
    validation[phase] = dict(tests=len(cases), failures=sum(c.find('failure') is not None for c in cases),
        errors=sum(c.find('error') is not None for c in cases), skips=sum(c.find('skipped') is not None for c in cases))
    for name in ('junit.xml', 'isolation.json'):
        copy(root / phase / name, evidence / phase / name)
assert validation['before'] == dict(tests=46, failures=42, errors=0, skips=0)
assert validation['final'] == dict(tests=49, failures=0, errors=0, skips=0)
assert all(c['exit_code'] == 0 for c in json.loads((root / 'quality-checks-final.json').read_text())['commands'])
package = json.loads((root / 'package-receipt-final.json').read_text())
assert len(package['commands']) == 7 and all(c['exit_code'] == c['expected'] for c in package['commands'])
for name in ('chat-recovery.json', 'dependencies.json', 'dependency-extras.json', 'current-state.json',
             'inventory-verification.json', 'prior-evidence-verification.json', 'data-metadata.json',
             'quality-checks-final.json', 'package-receipt-final.json'):
    copy(root / name, evidence / name)
for path in root.glob('*-final.log'):
    copy(path, evidence / path.name)
for path in (root / 'package-smoke-final').glob('*.log'):
    copy(path, evidence / 'package-smoke-final' / path.name)
copy(prior / 'evidence/.gitattributes', evidence / '.gitattributes')
copy(root / 'PLANO.md', docs / 'PLANO.md')
dump(evidence / 'validation-summary.json', {'python': validation, 'unique_final_tests': 49,
    'scope': 'Two pure gates, synthetic cases only. No frozen A10 report or protected outcomes.',
    'quality_files': 3, 'offline_package_commands': 7, 'dotnet_redis_rerun': False,
    'new_economic_evaluation': False, 'capital_enabled': False})

# Snapshot current guides by bytes before replacing them. History remains in Git as well.
guide_names = ['README.md','HANDOFF.md','docs/ESTADO_ATUAL.md','docs/DATA_MAP.md',
               'docs/INDICE_DOCUMENTACAO.md','docs/continuation/RETOMADA.md']
previous_guides = {}
for name in guide_names:
    path = repo / name
    target = root / 'previous-guides' / name
    copy(path, target)
    previous_guides[name] = {'path': str(target), **digest(target), 'git_commit': start}
copy(base / 'LEIA_PRIMEIRO.md', root / 'previous-guides/LEIA_PRIMEIRO_ROOT.md')
previous_guides['C:/BRASILEIRAO/LEIA_PRIMEIRO.md'] = {
    'path': str(root / 'previous-guides/LEIA_PRIMEIRO_ROOT.md'), **digest(root / 'previous-guides/LEIA_PRIMEIRO_ROOT.md')}
dump(evidence / 'previous-guides.json', previous_guides)

inventory = json.loads((prior / 'evidence/source-inventory.json').read_text(encoding='utf-8'))
indexed = {r['path']:r for r in inventory}
reviewed = ['brasileirao_predictor/research/calibration_gate.py','brasileirao_predictor/research/residual_gate.py',
            'tests/test_reconciliation_gate_contracts.py', 'brasileirao_predictor/data/lineup_archive.py']
for name in reviewed:
    path = repo / name
    indexed[name] = dict(path=name, **digest(path), lines=len(path.read_text(encoding='utf-8').splitlines()),
        review='semantic_read_with_recorded_findings', evidence='RCA-P02/P03/P07; gates tested synthetically, lineup persistence not executed')
depth = dict(collections.Counter(r['review'] for r in indexed.values()))
dump(evidence / 'source-inventory.json', sorted(indexed.values(), key=lambda r:r['path']))

registry = json.loads((prior / 'REGISTROS.json').read_text(encoding='utf-8'))
registry.update(round='RCA-20260910', dated_at=datetime.now(UTC).isoformat(), base=start,
    previous_registry='../artifact_integrity_2026-09-10/REGISTROS.json', mandate_complete=False)
for item in registry['issues']:
    if item['id'] == 'CPL-P25':
        item['action'] = f'Inventário atual: {len(indexed)} fontes/testes, profundidades {depth}. Conferência de hashes não é nova revisão semântica; completar os arquivos permitidos ainda pendentes.'
    if item['id'] == 'CPL-P23':
        item['limitation'] = 'Worker: Elo 1500/1500 e posição UNKNOWN; MarketOddsCache: wss://exchange.example.com/odds/ws; Compose: wss://exchange.invalid/odds/ws. Feed genérico sem contrato comercial; LastUpdated é recibo local, sem estado/revisão/clock da fonte e sem limite total de mensagem fragmentada. Não homologado, não iniciado nesta rodada.'
    if item['id'] == 'CPL-P24':
        item['action'] = 'Nova consulta view nesta rodada também retornou somente cartão. TOML no caminho esperado ausente; isso não prova ausência da automação. Helpers DC intactos e sem tentativa/recibo às 19:17 UTC de 10/09; não duplicar ou alterar janela.'

new_rows = [
('01','O primeiro mandato e a lista de pendências estavam integralmente concluídos',
 'Guias sobrepostos usavam vários estados vigentes; cobertura parcial e pendências apenas em mapas impediam a alegação de conclusão.',
 'documentação/rastreabilidade','alta','Guias, histórico visível, inventário e registros RI/IE/BE/CPL/CLO/LGC/ARI',
 'Relidos os dois mandatos e todo histórico visível recuperado; criada matriz de todas as seções, errata datada, um estado atual e registro central ampliado.',
 'MATRIZ_MANDATO.md, HISTORICO.md, evidence/chat-recovery.json e previous-guides.json', 'validado',
 'Corrigida a representação do estado; a revisão integral do sistema permanece aberta.'),
('02','O gate A10 só decide a partir de métricas numéricas válidas',
 'float aceitava strings/bools e infinito negativo podia satisfazer melhora; estruturas inválidas produziam exceções acidentais.',
 'validação/integridade','alta','research/calibration_gate.py; somente consumidor puro, sem replay de relatório congelado',
 'Validar estrutura e números reais finitos sem coerção; schema v2 com procedência/evidência econômica/capital false; preservar guardrail ausente como NO_GO.',
 'Regressões RCA before falham e final passa; nenhuma métrica histórica recalculada.', 'validado',
 'O relatório é declarado pelo chamador; v2 não autentica amostra, treino, independência ou lucro.'),
('03','O gate residual conserva universo e usa unidade financeira coerente',
 'Aceitava números/configurações inválidos, descartava incompletos e podia retornar GO no subconjunto; ignorava stake explícita diferente de um.',
 'validação/universo/contabilidade','alta','research/residual_gate.py; Bootstrap/PSR Core existentes',
 'Validar domínio antes da amostra; PENDING_DATA se faltarem campos; contar universo/incompletos; recusar stake não unitária; declarar hipótese unitária e DSR fornecido; PSR indefinido vira null.',
 'RCA before: GO em subconjunto incompleto; final 49 casos direcionados aprovados.', 'validado',
 'ROI continua média de PnL sob hipótese unitária declarada. Não é carteira, aceitação, autenticação ou validação econômica.'),
('04','GO no gate residual já incorpora dependência e seleção de tentativas',
 'PSR usa retornos por linha sem ajuste de dependência; DSR é fornecido, não calculado de um registro de tentativas.',
 'estatística/procedência','alta','research/residual_gate.py; protocolo, universo e registro de tentativas',
 'Limites explícitos em v2; manter fora da homologação econômica. Definir inferência e procedência antes de qualquer nova avaliação de performance.',
 'Novo protocolo com clusters/universo/tentativas e critérios prévios; testes numéricos não fecham esta questão.', 'identificado',
 'Não recalcular estudo congelado nem promover GO_CANDIDATE a capital.'),
('05','O walk-forward residual é uma carteira financeira completa',
 'Calcula retorno por seleção em unidade fixa, sem aplicar stake da decisão e sem caixa/reserva/execução; linha de resultado usa int(outcome).',
 'arquitetura/contabilidade/entrada','alta','research/residual_walkforward.py; dados/labels e quotes declarados',
 'Retirar da interpretação de lucro executável; sucessor necessita contratos de entrada/identidade/cortes e carteira se voltar ao caminho escolhido.',
 'Regressões de labels/cortes e reconciliação financeira independente em sucessor; ainda não executadas nesta rodada.', 'identificado',
 'Dois testes sintéticos anteriores demonstram somente cenários cobertos; não avaliam todas as entradas ou lucro.'),
('06','Curated/1 conserva os campos necessários ao closing/v2',
 'curated_odds não possui status, período ou linha; matches têm PK latest-state. Não permite reconstrução integral de revisões a partir dessa tabela.',
 'schema/arquitetura/temporalidade','alta','data/pit_backfill.py; schema pit-curated/1.0 e contratos closing-v2',
 'Não admitir a tabela como histórico comercial completo; elaborar sucessor isolado versionado antes de nova ingestão. Sem migração do banco operacional.',
 'Round-trip com suspensão, linhas/períodos e revisões empatadas; ausência de reaparição de estado ativo superado.', 'identificado',
 'Receber raw explícito em outro consumidor não corrige os campos que o schema não conserva.'),
('07','O arquivo de escalações preserva uma observação vazia ou removida',
 'persist_lineups grava somente linhas de jogadores; vazio não registra envelope/tombstone; JSON inválido histórico é ignorado e gravação não coordena escritores.',
 'persistência/arquitetura','alta','data/lineup_archive.py; consumidores e protocolos de coleta precisam ser mapeados antes da substituição',
 'Fora da admissão PIT integral; sucessor de envelopes imutáveis e política explícita de corrupção/concorrência, sem trocar coletor protegido.',
 'Fixtures de vazio, remoção, revisão, corrupção e concorrência com consulta por corte; não executadas nesta rodada.', 'identificado',
 'Leitura semântica do código feita; nenhum arquivo real de escalações foi aberto ou alterado.'),
('08','A auditoria de latência mantém o registro com T3 mais recente por chave',
 'RecordAsync usa SET incondicional no Lua; chegada atrasada pode substituir o registro da chave por versão T3 anterior.',
 'concorrência/telemetria','média','dotnet/LineupWorker/Services/LatencyAuditService.cs, WindowScript',
 'Registrar limite distinto do CAS de MarkMarketRead; definir identidade/revisão e corrigir no laboratório Redis isolado.',
 'Duas gravações em ordem inversa preservam o registro novo e o histórico; atualização T4 continua CAS sem renovar TTL.', 'identificado',
 'CLO corrigiu retenção/percentis e corrida de leitura T4; isso não resolve a ordem de gravações RecordAsync.'),
('09','Todas as dependências e implantações estão disponíveis e homologadas',
 'Docker/Podman não encontrados no PATH, nenhum serviço Docker/Podman identificado; Compose local e CI da nova revisão não executados.',
 'infraestrutura/reprodução','alta','compose.yaml, Dockerfiles, CI e runtime compatível isolado',
 'Python/extras/SDK verificados; build offline passa. Manter a homologação Compose/CI separada da instalação de bibliotecas e dos ensaios Windows.',
 'Executar Compose e CI no runtime suportado sem volumes/serviços protegidos; não substituído pelo Redis portátil.', 'bloqueado',
 'A ausência no PATH não prova ausência de todo binário possível. Instalar/usar engine requer definir host compatível e impacto; nenhum daemon foi iniciado.'),
('10','O livro manual certifica patrimônio líquido e custos reais',
 'LGC estabilizou escritores cooperantes e reconciliação por IDs; moeda/unidade/fluxos e custos declarados não são fatos comerciais autenticados nem transação conjunta dos dois arquivos.',
 'contabilidade/procedência','alta','bet_log.py; fontes de saldo/fluxos/unidade/custos permitidas',
 'Manter valores manuais brutos e escopo explícito; definir contrato financeiro e coordenação entre arquivos antes de homologar patrimônio.',
 'Casos de mudança de unidade, ordem de fluxos, custo, simultaneidade entre arquivos e reconciliação com fatos verificáveis.', 'identificado',
 'Nenhum ledger operacional foi aberto. Não estimar moeda/câmbio/custo desconhecido como zero.'),
('11','O backup verificado recupera toda a operação e os dados da máquina anterior',
 'Git/ZIP e manifesto recebido são verificáveis; restauração de bancos/serviços protegidos e conteúdo não recebido não foi demonstrada.',
 'recuperação/escopo','alta','Snapshots e arquivos recebidos; fronteiras do mandato e máquina de origem',
 'Conferir bytes e restauração Git separadamente; preservar os cinco snapshots, sem restaurar dados operacionais ou supor arquivos ausentes recebidos.',
 'Teste operacional específico somente se permitido; recibo Git/ZIP desta etapa não o substitui.', 'bloqueado',
 'Reflete RI-P16, não uma constatação de corrupção dos backups.'),
]
for suffix, allegation, problem, typ, severity, deps, action, test, status, limit in new_rows:
    aid, pid = 'RCA-A'+suffix, 'RCA-P'+suffix
    registry['claims'].append(dict(id=aid, claim=allegation, origin='Conciliação RCA, 10/09/2026', scope=deps,
        required=test, found=problem+' '+action, conclusion='refutada como alegação geral; ver limite e estado do problema',
        impact=limit, evidence=test, issue=pid))
    registry['issues'].append(dict(id=pid, claim=aid, problem=problem, type=typ, severity=severity,
        dependencies=deps, action=action, closure_test=test, status=status, limitation=limit))

links = {
 'RI-P01':['RCA-P09'], 'RI-P02':['CPL-P26'], 'RI-P03':['CPL-P20'], 'RI-P04':['CPL-P20'],
 'RI-P05':['CPL-P20'], 'RI-P06':['CPL-P25'], 'RI-P07':['CPL-P25'], 'RI-P08':['CPL-P25'],
 'RI-P09':['CPL-P25'], 'RI-P10':['CPL-P25'], 'RI-P11':['CPL-P22'], 'RI-P12':['RCA-P09','CPL-P23'],
 'RI-P13':['RCA-P01','CPL-P25'], 'RI-P14':['CPL-P26'], 'RI-P15':['CPL-P24'],
 'RI-P16':['RCA-P11'], 'RI-P17':['CPL-P25'], 'RI-P18':['CPL-P22'],
 'IE01':['CPL-P21'], 'IE02':['CPL-P20'], 'IE03':['RCA-P09'], 'IE04':['CPL-P21'],
 'IE05':['CPL-P20'], 'IE06':['RCA-P01'], 'IE07':['CPL-P26'],
 'BE-P01':['RCA-P01'], 'BE-P02':['CPL-P26'], 'BE-P03':['CPL-P26'], 'BE-P04':['RCA-P01']}
historical = []
for filename, prefix, key in [('implementation_2026-09-10/REGISTROS_RI_UTF8.json','RI-','problems'),
                              ('implementation_2026-09-10/REGISTROS.json','','issues'),
                              ('economic_search_2026-09-10/REGISTROS.json','','issues')]:
    content = json.loads((repo / 'docs/continuation' / filename).read_text(encoding='utf-8'))
    for item in content[key]:
        identity = prefix + item['id']
        historical.append(dict(id=identity, source='../'+filename, problem=item['problem'],
            original_status=item['status'], current_related_issues=links[identity],
            note='Status histórico preservado; relação temática não implica reabertura ou fechamento do experimento.'))
registry['historical_reconciliation'] = historical
registry['states'] = dict(technical='não pronto globalmente; contratos corrigidos passam no escopo sintético',
    data='parciais/insuficientes para execução comercial; calendários/fontes não universalmente atualizados',
    economic='lucro executável não mensurável; BE apenas cenário e investigação de preço',
    mandate='não concluído; ações e cobertura pendentes explicitadas')
assert len(registry['issues']) == 49 and len(historical) == 29
dump(docs / 'REGISTROS.json', registry)
table = ['# Registro central RCA', '',
 '49 itens correntes: 38 herdados e 11 explicitados nesta conciliação. Além deles, os 29 registros RI/IE/BE têm correspondência histórica no mesmo JSON. Não são 49 bugs independentes nem a lista de todos os erros possíveis.', '',
 '[Alegações, causa, impacto, dependências, prova de fechamento e histórico](REGISTROS.json). Os registros anteriores continuam preservados.', '',
 '| Alegação / problema | Status | Problema e ação |', '| --- | --- | --- |']
for item in registry['issues']:
    table.append(f"| {item['claim']} / {item['id']} | {item['status']} | {item['problem'].replace('|','/')} {item['action'].replace('|','/')} |")
write(docs / 'REGISTROS.md', '\n'.join(table))

consolidated = [
('1','Local e instruções','Atendido nesta etapa','Dois textos e histórico relidos; solo; C:/BRASILEIRAO. Sistema/Git/Codex externos identificados.','RCA-P01/RCA-P09'),
('2','Missão e sequência','Parcial','RI/IE/BE/CPL/CLO/LGC/ARI corrigiram problemas e testaram hipóteses; lucro e revisão integral não alcançados.','CPL-P25/CPL-P26'),
('3','Fronteiras','Preservadas no trabalho observado','Testes sintéticos; nenhum acesso a desfechos/coortes/ledger operacional, capital ou agenda nesta etapa.','RCA-P11'),
('4','Reconhecimento/checkpoint','Atendido nesta etapa','Base, worktree, estado, ambiente e PLANO; serviço não inferido de script existente.','RCA-P01/RCA-P09'),
('5','Inventário/rastreabilidade','Parcial, corrigida a organização','Inventário de fontes/testes e contratos adicionais; profundidade parcial. Pendências dos mapas agora registradas.','CPL-P25/RCA-P01'),
('6','Dados e recuperação','Parcial; bloqueios externos e coleta futura','177 históricos/CSV/piloto recuperados em DC; recebidos depois das decisões; sem oferta comercial suficiente.','CPL-P26/RCA-P06/RCA-P07'),
('7','Lógica/matemática/tempo','Parcial','Regressões de identidade/corte/preço/contabilidade corrigidas; clocks/features/modelos compartilhados ainda não demonstrados.','CPL-P22/RCA-P02/RCA-P03'),
('8','Modelagem/avaliação/pesquisa','Parcial','BE pré-especificado concluído no cenário; artefatos ARI corrigidos; inferência estatística/replay legados ainda limitados.','RCA-P04/RCA-P05/CPL-P26'),
('9','Execução e contabilidade','Parcial','BE reconciliado condicionalmente; livro manual corrigido em LGC. Oferta/aceite/custos reais não conhecidos.','CPL-P26/RCA-P10'),
('10','Arquitetura/engenharia/reprodução','Parcial','Python/.NET/Redis testados em escopos datados; gates RCA corrigidos. Feed demonstrativo, Compose e cobertura abertos.','RCA-P06/RCA-P07/RCA-P08/RCA-P09/CPL-P23'),
('11','Automações/contexto','Parcial/não verificável','Helpers DC íntegros; janela futura fixa; view só cartão, sem prova textual de estado ativo.','CPL-P24'),
('12','Fechamento e continuidade','Mandato ainda aberto','Nenhuma classificação global pronta; erros/pesquisa remanescentes não são fechados por contagem de testes.','CPL-P25/RCA-P01'),
('13','Entrega e guias','Checkpoint desta etapa','Matriz, mapa, dados, registros, reprodução, guias e pacote; integração/restauração no recibo RCA após commit.','RCA-P01/RCA-P11'),
]
original = [
('1','Missão','Não alcançada','CPL-P26'),('2','Autonomia técnica','Aplicada com fronteiras','RCA-P01'),
('3','Regras invioláveis','Preservadas no trabalho observado','RCA-P11'),('4','Prioridade','Reavaliada; gargalo de oferta comercial permanece','CPL-P26'),
('5','Reconhecimento','Atendido nesta etapa','RCA-P09'),('6','Pergunta da rodada','BE/DC mantida; nenhuma alternativa nova','CPL-P26'),
('7','Especificação prévia','BE congelado; RCA não mede performance','RCA-P04'),('8','Premissa crítica','Preço executável continua sem demonstração','CPL-P26'),
('9','Contrato de odds','Parcial; componentes puros e legados distintos','RCA-P06/CPL-P23'),('10','Caminho econômico','Cenário BE percorre conta; execução comercial bloqueada','RCA-P05/CPL-P26'),
('11','Contabilidade','Parcial; unidade/custos manuais não autenticados','RCA-P03/RCA-P10'),('12','Métricas econômicas','Reportadas no escopo BE; não atualizadas por nova avaliação','CPL-P26'),
('13','Validade estatística','Parcial; resultados condicionais não são validação independente','RCA-P04'),('14','Modelos','ARI corrigido; modelo BE reprovado sem retuning','RCA-P05'),
('15','APIs/recursos','Tentativas anteriores preservadas; zero nova consulta de dados','CPL-P26'),('16','Engenharia/isolamento','Parcial global; 49 testes RCA e pacote passam','RCA-P09/CPL-P25'),
('17','Integração','main local; sem push/implantação; recibo final RCA','RCA-P11'),('18','Critério de parada','BE encerrado; mandato integral continua','CPL-P25'),
('19','Contexto histórico','Reconciliado; não aplicado como estado atual','RCA-P01'),('20','Entrega obrigatória','Experimento BE histórico substancial; RCA é conferência/correção, não lucro novo','CPL-P26'),
]
dump(evidence / 'mandate-sections.json', {'consolidated':consolidated, 'original':original})
lines = ['# Conferência integral dos requisitos', '',
 'Conclusão: **o primeiro mandato não foi cumprido integralmente**. Esta matriz cobre todos os tópicos dos dois documentos; não transforma essa cobertura documental em revisão semântica integral do código.', '',
 'Mandatos em C:/BRASILEIRAO/INSTRUCOES/PROMPT_FINAL_REVISAO_INTEGRAL_2026-09-09.md e MANDATO_RECEBIDO_2026-09-09.txt. Evidências detalhadas e próximos critérios estão em [REGISTROS.json](REGISTROS.json).', '',
 '| Consolidado | Exigência | Estado | Conferência | Registros |', '| --- | --- | --- | --- | --- |']
lines += ['| '+' | '.join(row)+' |' for row in consolidated]
lines += ['', '| Original | Exigência | Estado | Registros |', '| --- | --- | --- | --- |']
lines += ['| '+' | '.join(row)+' |' for row in original]
write(docs / 'MATRIZ_MANDATO.md', '\n'.join(lines))

messages = json.loads((root / 'chat-messages.json').read_text(encoding='utf-8'))
chat_claims = []
for index, msg in enumerate(messages, 1):
    if msg['role'] == 'assistant' and msg['phase'] in ('final', 'final_answer'):
        chat_claims.append({'visible_index':index, 'source_line':msg['source_line'], 'timestamp':msg['timestamp'],
            'first_paragraph':msg['text'].strip().split('\n\n')[0]})
dump(evidence / 'chat-final-claims.json', chat_claims)
write(docs / 'HISTORICO.md', '''# Conciliação do chat e errata datada

Foram recuperados e relidos os 85 registros visíveis da fotografia do chat: 38.382 caracteres, incluindo três injeções de contexto do aplicativo e as mensagens iniciais desta conferência. A API retornou oito turnos, mas cinco vieram sem itens; o registro local exato da tarefa preencheu essa lacuna. O recibo contém hash, tamanho e caminho da fotografia. Não foram exportados raciocínio interno nem saídas de ferramentas. O texto visível integral fica em C:/BRASILEIRAO/work/reconciliation-2026-09-10/chat-messages.txt; não é necessário publicá-lo no Git.

| Afirmação anterior | Confronto com a evidência | Estado correto |
| --- | --- | --- |
| RI: “Executei a revisão no escopo permitido” e handoff “revisão RI concluída” | Inventário não demonstrava leitura semântica integral; havia bloqueadores e trabalho viável posterior | Formulação excessiva se interpretada como conclusão do primeiro prompt. RI foi uma rodada de correções, não encerramento da revisão integral. |
| IE: dependências/Redis/.NET recuperados | SDK e pacotes existem; integração sintética executada, artefatos de execução preservados | Confirmado nos ambientes e testes citados. Não inclui instalação operacional, Docker local ou feed real. |
| IE: 309 testes Python | 282 de um lote mais 27 Redis, conforme reconciliação posterior | Não apresentar como uma nova suíte homogênea de 309, nem somar de novo aos lotes posteriores. |
| BE: +4,6376u | Cenário com 226 carteiras de máximos anônimos e preenchimento hipotético | Conta condicional; simultaneidade, casas, aceitação e capacidade não demonstradas. |
| BE: modelo de gols perdeu 99,60u | Resultado congelado de regra fixa e banca limitada | Não retunar no mesmo universo para salvar a conclusão nem chamar o menos ruim de lucrativo. |
| Cobertura completa porque havia inventário/estática/testes | Base ARI tinha 457 fontes/testes: 115 semânticos, 283 estáticos/pontuais, 59 protegidos por contrato | Revisão semântica parcial. O inventário não cobre todas as configurações/documentos nem prova ausência de bugs. |
| CPL: startup corrigido | Falha nova ocorreu; CLO depois passou 127 testes .NET, mas não estabeleceu causa única da instabilidade | CPL-P21 continua em investigação. Passagens posteriores não apagam a falha. |
| CLO/LGC/ARI corrigiram tudo citado | Correções delimitadas têm regressões; os próprios mapas mantêm outras falhas de gates/persistência/replay | Agora os dois gates foram corrigidos na entrada; outras pendências foram incorporadas ao registro central. |
| Arquitetura com todos os componentes implica prontidão | Feed exemplo, Elo 1500, UNKNOWN, parâmetros demo e Compose não homologado persistem | Sistema global não pronto. Registro de domínio e interface não equivalem a implementação comercial. |
| Arquivos e fontes íntegros implicam dados suficientes/atualizados | Raw recebido depois do corte não prova disponibilidade histórica; 3 capturas = 1 jogo | Dados parciais; calendário completo, campos PIT e condições comerciais não estão universalmente validados. |
| Automação configurada significa ativa | View atual retorna apenas cartão; definição esperada não encontrada; sem recibo antes da janela futura | Atividade não verificável por esse retorno. Não criar duplicata nem antecipar captura. |
| Backup verificado recupera toda a máquina | Bundle/ZIP e árvore Git verificados; bancos operacionais não restaurados | Recuperação comprovada somente no escopo explicitado no recibo. |

As conclusões finais posteriores que diziam “mandato integral permanece aberto” são compatíveis com a evidência. Esta errata corrige a ambiguidade das formulações anteriores, preservando resultados, logs de falha, commits e documentos congelados. Todos os 29 problemas RI/IE/BE foram relacionados aos registros correntes; seu status histórico não foi reescrito. Registros de testes de rodadas distintas têm sobreposições e nunca devem ser somados como uma aprovação global nova.
''')

write(docs / 'MAPA_SISTEMA.md', '''# Estado real da arquitetura RCA

O detalhamento histórico de entradas/saídas/caminhos está no [mapa CLO](../closeout_2026-09-10/MAPA_SISTEMA.md); suas contagens e pendências datadas são substituídas pelo registro RCA. O caminho efetivo é CLI/Python, dependências Core/Ops, armazenamento legado, pesquisa isolada e laboratório Python/Redis/.NET. Não foi encontrado frontend web no inventário de fontes.

| Caminho | Estado e decisão | Impedimento restante |
| --- | --- | --- |
| Coleta/DB/Elo/xG/cache compartilhados → predict/display | Legado diagnóstico; correções CPL de consumo preservadas | RI-P11/CPL-P22: cache por contagem, associação aproximada e relógios/artefatos aprendidos não certificam PIT. Dependências protegidas impedem alteração indiscriminada. |
| Raw com recibo → decoder/anchor/PIT → abstenção | Consumidores puros têm validações sintéticas; manter | Preço decodificado não certifica disponibilidade comercial; curated/1 perde status/linha/período/revisões. RCA-P06. |
| Arquivo de escalações → residual_features | Parcial; manter fora da admissão completa | Sem envelope vazio/tombstone, corrupção ignorada e concorrência sem contrato. RCA-P07. |
| Artefato residual → probabilidade/intervalo → decisão shadow | Integridade numérica ARI corrigida; preservar | Hessiana condicional, procedência e incerteza econômica não autenticadas. |
| Gates A10/residual | Corrigir: contratos v2, 49 testes sintéticos finais | Não promovem serving/capital; PSR/DSR e universo recebido não autenticados. RCA-P02/03/04. |
| residual_walkforward → métricas | Exploratório; retirar da interpretação de carteira real | Stake da decisão não aplicada à banca; entrada/labels e clocks não integralmente validados. RCA-P05. |
| BE → oferta hipotética → reserva/conta/resultado | Experimento congelado; conservar | Máximos anônimos não formam prova de ofertas simultâneas executáveis. CPL-P26. |
| Livro manual → liquidação/banca | LGC corrigiu bloqueio de escritores e snapshot de bets; bruto/manual | Coordenação entre arquivos, unidade, moeda, custos e fatos comerciais limitados. RCA-P10. |
| Worker → Redis Functions → kernel → sinal | Protocolo exercitado em laboratório; operação comercial parcial | Elo 1500/1500, posições UNKNOWN, VORP/demo; fornecedor WebSocket não implementado. CPL-P23. |
| MarketOddsCache → MarketStateEngine | Demo não homologada; não iniciar feed genérico | URL example.com no C#, exchange.invalid no Compose; recibo local não é clock comercial; limite total de fragmentos ausente. CPL-P23. |
| LatencyAuditService → percentis/T4 | Retenção e CAS T4 testados anteriormente | SET de RecordAsync não recusa T3 anterior; RCA-P08. |
| Runtime/CI/pacote | Python/SDK/Redis portátil utilizáveis em laboratório; pacote offline passa | Docker/Compose e CI desta revisão não executados. Python 3.14 não reensaiado aqui; tipagem global exclui research. RCA-P09. |
| Backup → restauração Git | ZIP/bundle/hashes conferidos; restore Git separado | Não recupera automaticamente operação nem arquivos nunca recebidos. RCA-P11. |
| H14/H15/H9/A1 e agenda DC | Preservar contratos e estados | Sem avaliação, renovação, consulta de resultados ou mudança de janela. Atividade da agenda não comprovada. CPL-P24. |

Os 283 arquivos classificados como estáticos/pontuais não foram transformados em semanticamente revisados por repetir hashes. Correção de módulos centrais não aprova todos os consumidores. Implementar outro feed ou modificar a coleta compartilhada exige definir o contrato e o efeito nas fronteiras antes, sem inventar credenciais ou disponibilidades. Nenhuma implantação realizada.
''')
write(docs / 'MAPA_DADOS.md', '''# Dados, datas e fontes RCA

Não é correto afirmar que os dados, datas e fontes estejam todos atualizados, completos e validados. A checagem atual confirmou hashes/metadados específicos; os resultados e conteúdos econômicos permanecem congelados.

| Requisito / fonte | Local / universo | Estado atual para a finalidade |
| --- | --- | --- |
| Histórico Football-Data | work/data-completion-2026-09-09/public_sources/football_data_bra_origin_csv.csv | Hash atual igual ao congelado. BE usou 4.940 partidas de 2012–2024; o CSV inclui outros anos. Max é anônimo; não certifica preço executável. |
| Timelines OddsPapi | work/data-completion-2026-09-09/raw; 177 Jan–Jun/2026 | Integridade conferida em RI; não repetida nesta etapa. Todos recebidos depois dos cortes históricos. Não admissíveis como recibo da época. |
| Piloto prospectivo DC | prospective_pilot; três capturas de um fixture | Uma unidade de evento. Flag de coleta do agregador não é suspensão comercial da casa; sem aceite/limite pessoal. |
| Captura futura DC | helpers no mesmo work; decision 11/09/2026 23:00 UTC | Hashes atuais intactos. Às 19:17 UTC de 10/09, tentativa e recibo ausentes; janela futura. Não antecipada. Automação não verificável pelo texto retornado. |
| Publicação e recebimento | API-Football/Sportmonks/OddsPapi | Contratos sintéticos e algumas fontes oficiais conferidos; publicação desconhecida fica null. Não generalizar correção UTC para calendário completo ou API homologada. |
| Fonte/estado/linha/revisões | The Odds API decoder e curated/1 | Decoder preserva vazio/inválido; schema curated incompleto para closing/v2. RCA-P06. |
| Escalações e features históricas | lineup_archive, residual_features, legado xG/Elo | Arquivo de linhas não registra retirada/vazio; causalidade por feature/artefato ainda parcial. RCA-P07/CPL-P22. |
| Preços nominais simultâneos/aceite/custos | Fontes legítimas tentadas nas rodadas DC/RI/BE/CPL | Não recuperados em forma suficiente. Barreiras OddsPortal/OddsAgora, Betfair e API-Football documental registradas; nenhuma tentativa idêntica repetida sem condição nova. |
| Acervo migrado | C:/BRASILEIRAO/DADOS_PRESERVADOS e manifesto | Recebido e preservado; 12.423 entradas/9.477.623.208 bytes são contagens do recibo de extração, não nova leitura nesta etapa. Cinco snapshots não foram restaurados operacionalmente. |
| Coortes protegidas | Contratos H14/H15/H9/A1 | Não verificáveis empiricamente dentro das permissões atuais. Não usar como preenchimento de lacunas ou holdout. |

Datas de testes são sintéticas. Hashes provam igualdade dos bytes, não autenticidade, atualização, oferta ou aceitação. Não foram consultados resultados de 2026, calendário completo atual, APIs limitadas ou custos pessoais nesta etapa. Não afirmar ausência de dependências externas ou que todos os dados de outra máquina foram recebidos.

Fontes e tentativas oficiais datadas: [CPL](../completion_2026-09-10/MAPA_DADOS.md), [CLO](../closeout_2026-09-10/MAPA_DADOS.md), [DC](../data_completion_2026-09-09/RESULTADO.md), [BE](../economic_search_2026-09-10/RESULTADO.md). Recibos atuais: [metadados](evidence/data-metadata.json), [dependências](evidence/dependencies.json) e [extras](evidence/dependency-extras.json).
''')

write(docs / 'RESULTADO.md', f'''# Conferência do primeiro mandato, do chat e do projeto — RCA-20260910

**Não: nem todos os erros, lacunas de dados, dependências operacionais e problemas de arquitetura foram resolvidos. O primeiro mandato continua incompleto.** Esta etapa releu ambos os documentos e o histórico visível integral disponível, conferiu o estado atual e corrigiu mais dois gates. A [matriz](MATRIZ_MANDATO.md) cobre as 13 seções do consolidado e as 20 do original. A [errata do chat](HISTORICO.md) distingue afirmações corretas no seu escopo de formulações que exageravam a conclusão.

Base main/{start}. Registro central: 49 itens correntes, com 29 correspondências RI/IE/BE. Três itens RCA validados tratam organização da evidência e dois gates; os demais explicitam pendências antes dispersas. “Identificado” significa trabalho restante, não resolvido por documentação. Fonte/teste: {len(indexed)} arquivos, profundidades {depth}. A conferência atual comparou 396 hashes inalterados e os dois gates alterados; 59 arquivos protegidos somente por metadados. Isso não é revisão semântica nova de 396 arquivos.

| Dimensão | Conclusão |
| --- | --- |
| Técnica | **Não pronto globalmente.** Gates corrigidos, lint/formato/tipagem dos três arquivos e pacote passam; arquitetura comercial, integração Compose, inicialização e revisão de fontes ainda têm pendências. |
| Dados | **Parciais/insuficientes.** Há dados íntegros e correções temporais pontuais; faltam clocks/procedência/campos e condições comerciais. Não estão todas as datas/fontes universalmente atualizadas ou validadas. |
| Economia | **Lucro executável não mensurável.** BE conserva cenário positivo condicional e modelo de gols negativo. Capital false; nenhuma aposta, avaliação econômica nova ou promessa de lucro. |

Correções materiais: A10 agora recusa estrutura/números inválidos em vez de converter texto/bool ou aceitar infinito. Residual valida valores/configuração/identidade, retorna PENDING_DATA se há registros incompletos e recusa stake explícita não unitária. Ambos declaram procedência/evidência econômica não verificadas e capital desabilitado. Schema v2 altera o contrato de avaliação futura; relatórios, protocolos, resultados e artefatos congelados não foram recalculados.

Validação desta etapa: **42 falhas em 46 casos antes; 49 testes direcionados aprovados depois e na execução final, sem falhas/skips.** Não são 98 testes únicos. Lint, formato e Pyright passaram nos três arquivos alterados. Wheel/sdist construídos offline, instalação em target isolado e sete comandos de pacote passaram. Nenhuma suíte global foi executada. Os 95 LGC, 54 ARI e 275 Python/27 Redis/127 .NET CLO são lotes anteriores, com possíveis sobreposições, e não foram somados nem reapresentados como testes desta rodada.

Dependências: Python 3.13.12, Core 3.2.0, Ops 4.1.0 e SDK .NET 10.0.401 presentes no ambiente RI. As 23 exigências diretas runtime/providers/kernel/dev passam; 76 combinações de requisitos/transitivos/extras foram verificadas sem conflito, incluindo hiredis. Hatchling não está no venv de execução: 1.32.0 está no cache usado pelo build isolado, que passou offline. Isso não equivale a recriar todas as dependências do zero. Docker/Podman não encontrados no PATH nem como serviços esperados; nenhum Compose local/CI nova executado. Git, PowerShell, Windows e Codex são dependências externas inevitáveis.

Pendências principais: cache/causalidade/associação de eventos compartilhados (CPL-P22); feed genérico, Elo 1500 e UNKNOWN (CPL-P23); scheduler não verificável (CPL-P24); cobertura semântica parcial (CPL-P25); oferta/fills/custos (CPL-P26); estatística/replay/persistência/telemetria/infraestrutura/contabilidade e recuperação (RCA-P04..11). [Registro completo](REGISTROS.md) e [mapa de arquitetura](MAPA_SISTEMA.md).

Os 14 itens econômicos permanecem explícitos, sem criar novo experimento:

1. Pergunta: existem ofertas nominais simultâneas e condições de preencher as pernas do candidato BE?
2. Prioridade: preço e execução decidem se a conta condicional corresponde a oportunidade observável.
3. Hipótese/mecanismo: cobertura dos três desfechos com soma inversa favorável após fricções; simultaneidade/aceitação não comprovadas.
4. Experimento: BE histórico congelado; RCA conferiu evidências e corrigiu contratos, sem novo teste de performance.
5. Dados/fontes: CSV Football-Data, timelines e recibos DC, fontes oficiais CPL; mapa especifica períodos e insuficiências.
6. Disponibilidade: raw recebido agora não demonstra disponibilidade passada; recibo, publicação e decisão são clocks distintos.
7. Resultado: BE +4,6376u em 226 carteiras hipotéticas; modelo de gols −99,60u. Nesta rodada nenhuma aposta ou resultado financeiro novo; lucro real não mensurável.
8. Custos: BE usa fricções de cenário; custos pessoais, fills, limites, moeda e infraestrutura atribuível continuam desconhecidos. Zero chamadas autenticadas nesta etapa não significa custo total zero.
9. Riscos: preenchimento parcial, revisão/suspensão, identidade, correlação, escolha retrospectiva de máximos e múltiplas tentativas.
10. Limitações: sem ofertas nominais simultâneas suficientes, sem aceitação/capacidade, arquitetura parcial e cobertura incompleta.
11. Testes: 49 sintéticos finais de gates; qualidade e pacote offline. Nenhum desfecho protegido lido.
12. Evidência: software validado somente no escopo demonstrado; dados/economia insuficientes para execução comercial.
13. Decisão: manter investigação de preço nominal BE; modelo de gols sem prioridade; não retunar, abrir variante ou habilitar capital.
14. Próxima informação: oferta identificada com estados/clocks/revisões e condições verificáveis de preenchimento/custos. Captura DC fixa testa sua dupla, não toda a carteira de três pernas.

A descoberta que mais muda esta conferência é que havia falhas de admissão ainda executáveis nos gates, enquanto a revisão seguia parcial e alguns guias sugeriam conclusão. Isso refuta “arrumou tudo”. A hipótese que perdeu prioridade permanece salvar por tuning o modelo de gols reprovado. A informação que decide o avanço econômico continua sendo oferta nominal simultânea executável sob custos verificáveis.

Guias anteriores preservados por bytes em C:/BRASILEIRAO/work/reconciliation-2026-09-10/previous-guides e no Git da base. SHA, diff, pacote e restauração de código no recibo C:/BRASILEIRAO/AUDITORIA/CONCILIACAO_MANDATO_2026-09-10.json após integração. Nenhum push, implantação, recuperação operacional, compra ou mudança de agenda.
''')

next_prompt = '''# Continuação após RCA — mandato integral ainda aberto

Trabalhe em C:/BRASILEIRAO/brasileirao-predictor, sozinho, mantendo tudo em C:/BRASILEIRAO. Leia integralmente PROMPT_FINAL_REVISAO_INTEGRAL_2026-09-09.md e MANDATO_RECEBIDO_2026-09-09.txt em INSTRUCOES, depois docs/continuation/reconciliation_2026-09-10/RESULTADO.md, MATRIZ_MANDATO.md e REGISTROS.json. Verifique HEAD/worktree/alterações/concorrência antes de agir; não reinicie a auditoria com base em contagens antigas.

H14/H15/H9/A1 e dependências operacionais permanecem protegidos, sem resultados, avaliações, renovação, restarts ou mudanças de agenda. Use somente sintéticos isolados, sem bancos/Redis/ledgers operacionais. Nenhum capital, aposta, login, compra, bypass ou API limitada sem plano/quota/reserva. BE e relatórios históricos congelados; novo desempenho exige protocolo prévio.

RCA corrigiu contratos de entrada dos gates A10/residual e a organização dos guias, com 49 testes finais. Isso não concluiu o mandato. Não repetir testes inalterados nem contar 49+49 como 98 únicos.

Prioridades justificadas: verificar metadados da captura DC na janela previamente fixada, sem duplicar/alterar agenda; continuar a investigação da fonte nominal somente se houver ação autorizada nova; corrigir pendências independentes RCA-P05 (contratos/replay), RCA-P07 (persistência de envelopes em sucessor seguro), RCA-P08 (ordem de gravação de telemetria) e RCA-P06 (schema isolado), delimitando efeitos antes. Completude semântica CPL-P25 continua necessária; não basta estender relatórios. Evitar modificar dependências da coleta protegida. Escolher sequência por impacto e efeitos reais.

Registre regressão antes/depois por bug material; mantenha os dois registros centrais e matriz atualizados sem encerrar limitações por documentação. Compose, CI, validação estatística e recuperação operacional têm estados distintos. Responda prontidão técnica, admissibilidade de dados e evidência econômica separadamente; nunca declare lucro ou revisão integral concluída sem os critérios demonstrados.
'''
write(docs / 'PROXIMO_PROMPT.md', next_prompt)
write(base / 'INSTRUCOES/PROXIMO_PROMPT_APOS_CONCILIACAO_2026-09-10.md', next_prompt)
write(docs / 'REPRODUZIR.md', '''# Reproduzir a verificação RCA

Ambiente: C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe; Python 3.13.12. Trabalho: C:/BRASILEIRAO/work/reconciliation-2026-09-10. Helpers, seus inputs e logs são preservados no pacote de entrega. Não executar scripts de pesquisa histórica ou coortes para repetir estes testes.

O runner recebe um nome de saída novo, exclusivo dentro do work, seguido de test_reconciliation_gate_contracts.py e test_residual_gate.py. Exemplo em PowerShell:

```powershell
& C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv/Scripts/python.exe -X utf8 -I -B C:/BRASILEIRAO/work/reconciliation-2026-09-10/run_isolated.py reproducao-nova test_reconciliation_gate_contracts.py test_residual_gate.py
```

O teste test_existing_a10_report_is_formally_no_go não foi executado; não usar o allowlist histórico do helper como autorização para reavaliar relatório congelado. O runner bloqueia rede, subprocessos e dados operacionais; todas as fixtures ficam na saída exclusiva. Seu recibo lista tentativas bloqueadas quando existentes.

before/junit.xml preserva 42 falhas/4 passagens; after e final têm 49 passagens cada. O source Git da base mais o novo arquivo de regressões permite examinar a reprodução anterior; não resetar a main para isso. check_changed.py executou Ruff e Pyright explícitos fora da exclusão global de research. build_package.py construiu offline e instalou somente o wheel no target, usando dependências já presentes no venv RI; não afirma ambiente reinstalado do zero. Saídas desses helpers são exclusivas ou nomeadas: não sobrescrever as evidências finais ao repetir.

verify_current_evidence.py conferiu inventário, hashes da entrega anterior, requisitos/extras e metadados DC; não importa a aplicação nem lê placares. recover_chat.py extraiu somente mensagens visíveis da tarefa exata; o primeiro print encontrou limitação de encoding do console, mas os arquivos foram salvos e relidos com -X utf8. A fotografia do chat cresce depois da leitura, então seu hash não deve ser comparado como se o log ativo fosse imutável.

Integração: prepare_integration.py usa caminhos exatos, verifica bytes indexados e não altera ignores globais. backup_delivery.py cria bundle, restaura em bare isolado, compara HEAD/árvore/evidências e bytes do wheel/ZIP. Esse procedimento verifica recuperação de código e evidências, não bancos/serviços operacionais.
''')

current_rel = 'docs/continuation/reconciliation_2026-09-10'
write(repo / 'README.md', f'''# brasileirao-predictor

Sistema de previsão e pesquisa do Brasileirão, com CLI Python e laboratório Redis/.NET. **Revisão integral incompleta, sistema global não pronto e lucro executável não demonstrado.**

Estado corrente: RCA-20260910. [Resultado da conferência]({current_rel}/RESULTADO.md), [matriz do mandato]({current_rel}/MATRIZ_MANDATO.md), [registro central]({current_rel}/REGISTROS.md) e [arquitetura]({current_rel}/MAPA_SISTEMA.md).

RCA corrigiu entradas inválidas nos gates A10/residual e o descarte silencioso de registros incompletos. 49 testes direcionados, qualidade dos três arquivos e pacote offline passaram. Python/extras/SDK estão no ambiente isolado; Docker/Compose e feed comercial não homologados. Isso não aprova todos os módulos ou dados.

[Estado](docs/ESTADO_ATUAL.md), [dados](docs/DATA_MAP.md), [retomada](docs/continuation/RETOMADA.md), [índice](docs/INDICE_DOCUMENTACAO.md) e [reprodução]({current_rel}/REPRODUZIR.md). Trabalhe somente em C:/BRASILEIRAO. H14/H15/H9/A1 e estados operacionais permanecem protegidos; capital desabilitado.

Históricos e evidências estão em docs/continuation e no Git. Guias da base 6c85045 preservados em C:/BRASILEIRAO/work/reconciliation-2026-09-10/previous-guides; não são estado vigente.
''')
write(repo / 'HANDOFF.md', f'''# Handoff corrente — RCA-20260910

**O primeiro mandato não foi concluído integralmente.** Leia [resultado]({current_rel}/RESULTADO.md), [matriz]({current_rel}/MATRIZ_MANDATO.md), [histórico/errata]({current_rel}/HISTORICO.md) e [registro central]({current_rel}/REGISTROS.json).

Os dois gates têm contratos v2 corrigidos e 49 testes finais sintéticos; dependências runtime/extras e SDK presentes, build offline passa. Restam cobertura semântica, persistência/temporalidade/replay/telemetria, feed demonstrativo, Compose/CI, scheduler e dados comerciais insuficientes. Não transformar correções delimitadas em homologação global.

[Próximo prompt]({current_rel}/PROXIMO_PROMPT.md) e [dados](docs/DATA_MAP.md). Preservar H14/H15/H9/A1, estudo BE e janela DC; não executar operações protegidas. Todo trabalho em C:/BRASILEIRAO, solo. Reconfirmar estado real na retomada.

O handoff acumulado anterior está intacto no Git 6c850454418a1c7e878fdb6a461dea509571caec e em C:/BRASILEIRAO/work/reconciliation-2026-09-10/previous-guides/HANDOFF.md. Seus relatos “vigentes” e comandos são históricos e exigem reconciliação; não autorizam reavaliar coortes.
''')
write(repo / 'docs/ESTADO_ATUAL.md', f'''# Estado atual — RCA-20260910

**Técnica: não pronto globalmente. Dados: parciais/insuficientes. Economia: lucro executável não mensurável. Mandato integral: aberto.**

Fonte única de estado: [resultado](continuation/reconciliation_2026-09-10/RESULTADO.md), [registro](continuation/reconciliation_2026-09-10/REGISTROS.json), [matriz](continuation/reconciliation_2026-09-10/MATRIZ_MANDATO.md). Inventário: {len(indexed)} fontes/testes, {depth}. Arquivos de build/configuração são escopo adicional; não chamar a contagem de “todo projeto revisado”.

Nesta rodada: gates A10/residual corrigidos; 42 falhas antes, 49 casos finais aprovados, qualidade em três arquivos e pacote offline aprovado. Dependências diretas/transitivas/extras no venv RI sem conflitos; SDK .NET 10.0.401 presente. Não repetidos .NET/Redis/estudos congelados; Compose e CI da nova revisão não executados.

[Arquitetura](continuation/reconciliation_2026-09-10/MAPA_SISTEMA.md), [dados](DATA_MAP.md), [errata](continuation/reconciliation_2026-09-10/HISTORICO.md) e [retomada](continuation/RETOMADA.md). Recibo de integração e recuperação de código: C:/BRASILEIRAO/AUDITORIA/CONCILIACAO_MANDATO_2026-09-10.json. Histórico anterior preservado por bytes e Git; não mantido como outro estado vigente nesta página.
''')
write(repo / 'docs/continuation/RETOMADA.md', '''# Retomada vigente — RCA-20260910

Leia [próximo prompt](reconciliation_2026-09-10/PROXIMO_PROMPT.md), [resultado](reconciliation_2026-09-10/RESULTADO.md) e [matriz](reconciliation_2026-09-10/MATRIZ_MANDATO.md). A cobertura integral não foi concluída. Retome as ações concretas do registro; não recomece pela repetição dos testes aprovados ou apenas pela ampliação dos relatórios.

Checkout C:/BRASILEIRAO/brasileirao-predictor, main; confirmar HEAD/estado real e recibo C:/BRASILEIRAO/AUDITORIA/CONCILIACAO_MANDATO_2026-09-10.json. Work e helpers desta etapa: C:/BRASILEIRAO/work/reconciliation-2026-09-10. Capital false; H14/H15/H9/A1 e agenda DC preservados; solo.

Dados de mercado ainda insuficientes; BE é cenário congelado, não lucro executável. DC: corte fixo 11/09/2026 23:00 UTC. Não duplicar captura/agenda, antecipar janela ou consumir reserva. Estado ativo da automação não comprovado por retorno textual.
''')
write(repo / 'docs/DATA_MAP.md', '''# Mapa atual de dados — RCA-20260910

**Dados, datas e fontes não estão universalmente completos ou validados para a decisão econômica.** O [mapa por requisito](continuation/reconciliation_2026-09-10/MAPA_DADOS.md) informa períodos, finalidade, admissibilidade e lacunas. O [registro central](continuation/reconciliation_2026-09-10/REGISTROS.json) acompanha as ações.

| Área canônica | Conteúdo / limite |
| --- | --- |
| C:/BRASILEIRAO/brasileirao-predictor | Código e evidências versionadas; presença de data/ não prova banco operacional instalado. |
| C:/BRASILEIRAO/work/data-completion-2026-09-09 | Raw OddsPapi, CSV, piloto, recibos e helpers da captura futura. Contagens/recibos históricos em DC; metadados atuais em RCA. |
| C:/BRASILEIRAO/work/economic-search-2026-09-10 | Protocolo e experimento BE congelados. Máximos anônimos, sem certificado de execução. |
| C:/BRASILEIRAO/work/reconciliation-2026-09-10 | Histórico visível recuperado, verificação de dependências, testes sintéticos, pacote e recibos desta etapa. |
| C:/BRASILEIRAO/DADOS_PRESERVADOS | Acervo recebido e manifesto; cinco snapshots preservados, sem consultas de resultados ou restauração operacional. |
| C:/BRASILEIRAO/AUDITORIA, BACKUPS, ENTREGAS | Recibos, bundles e pacotes. Recuperação de Git distinta de operação. |
| C:/BRASILEIRAO/INSTRUCOES | Mandatos originais preservados e próximo prompt datado. |

Mapeamento de caminhos da máquina anterior e inventário de snapshots preservados em C:/BRASILEIRAO/work/reconciliation-2026-09-10/previous-guides/docs/DATA_MAP.md e no Git 6c85045. Não supor arquivo recebido apenas trocando prefixos. Não copiar configurações privadas para pesquisa/Git.

[DC](continuation/data_completion_2026-09-09/RESULTADO.md), [BE](continuation/economic_search_2026-09-10/RESULTADO.md), [fontes CPL](continuation/completion_2026-09-10/MAPA_DADOS.md). Os documentos são evidência datada, não provas de funcionamento atual. Hash não autentica fonte, disponibilidade, aceitação ou calendário.
''')
write(repo / 'docs/INDICE_DOCUMENTACAO.md', '''# Índice corrente — RCA-20260910

| Documento | Finalidade |
| --- | --- |
| [Resultado atual](continuation/reconciliation_2026-09-10/RESULTADO.md) | Resposta sobre completude, correções e três estados. |
| [Matriz dos mandatos](continuation/reconciliation_2026-09-10/MATRIZ_MANDATO.md) | Todas as 13+20 seções e pendências correspondentes. |
| [Registros centrais](continuation/reconciliation_2026-09-10/REGISTROS.json) | Alegações, problemas, status, limites e 29 correspondências históricas. |
| [Histórico e errata](continuation/reconciliation_2026-09-10/HISTORICO.md) | Confronto do chat com evidências. |
| [Sistema](continuation/reconciliation_2026-09-10/MAPA_SISTEMA.md) / [dados](continuation/reconciliation_2026-09-10/MAPA_DADOS.md) | Contratos, arquitetura, fontes e lacunas. |
| [Reproduzir](continuation/reconciliation_2026-09-10/REPRODUZIR.md) / [próximo prompt](continuation/reconciliation_2026-09-10/PROXIMO_PROMPT.md) | Ensaios seguros e continuação do trabalho restante. |
| [ARI](continuation/artifact_integrity_2026-09-10/RESULTADO.md) / [LGC](continuation/ledger_consistency_2026-09-10/RESULTADO.md) / [CLO](continuation/closeout_2026-09-10/RESULTADO.md) | Resultados históricos de artefatos, ledger e contratos. |
| [CPL](continuation/completion_2026-09-10/RESULTADO.md) / [BE](continuation/economic_search_2026-09-10/RESULTADO.md) / [IE](continuation/implementation_2026-09-10/RESULTADO.md) | Histórico de implementação e investigação econômica. |

O índice acumulado antigo foi preservado em C:/BRASILEIRAO/work/reconciliation-2026-09-10/previous-guides/docs/INDICE_DOCUMENTACAO.md e no Git da base. Contagens antigas de documentos são fotografias históricas. Não executar instruções históricas que contrariem os mandatos atuais.
''')
write(base / 'LEIA_PRIMEIRO.md', '''# BRASILEIRAO — ponto de entrada atual RCA-20260910

O primeiro mandato continua incompleto. Sistema global não pronto; dados parciais; lucro executável não demonstrado. Trabalho solo em C:/BRASILEIRAO, sem capital, alterações de coortes ou implantação.

Checkout: C:/BRASILEIRAO/brasileirao-predictor. Leia README.md, docs/ESTADO_ATUAL.md e docs/continuation/reconciliation_2026-09-10/RESULTADO.md nesse checkout. A matriz confronta integralmente os dois mandatos com evidências e pendências. Próximo prompt: C:/BRASILEIRAO/INSTRUCOES/PROXIMO_PROMPT_APOS_CONCILIACAO_2026-09-10.md.

RCA corrigiu mais dois gates e consolidou guias/pendências: 49 testes direcionados e pacote offline aprovados. Isso não equivale a revisar todos os arquivos ou homologar toda a arquitetura. Mandatos originais em INSTRUCOES preservados. Dados recebidos em DADOS_PRESERVADOS, ambientes/evidências em work, entregas em ENTREGAS, backups em BACKUPS e recibos em AUDITORIA.

Guia anterior preservado em C:/BRASILEIRAO/work/reconciliation-2026-09-10/previous-guides/LEIA_PRIMEIRO_ROOT.md. Recibo desta integração/restauração de código: C:/BRASILEIRAO/AUDITORIA/CONCILIACAO_MANDATO_2026-09-10.json. H14/H15/H9/A1, observadores e captura futura DC permanecem protegidos pelos respectivos contratos.
''')
dump(evidence / 'manifest.json', {p.relative_to(docs).as_posix():digest(p) for p in sorted(evidence.rglob('*')) if p.is_file()})
print(json.dumps({'inventory':len(indexed),'depth':depth,'issues':len(registry['issues']),
    'open_issues':[(r['id'],r['status']) for r in registry['issues'] if r['status'] != 'validado'],
    'historical_links':len(historical),'mandate_complete':False}, ensure_ascii=False))
