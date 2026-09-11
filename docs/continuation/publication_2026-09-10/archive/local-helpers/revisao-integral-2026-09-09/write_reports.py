"""Render the central dated review records; preserve frozen prior reports."""
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('C:/BRASILEIRAO/brasileirao-predictor')
DEST = REPO / 'docs/continuation/integral_review_2026-09-09'
DEST.mkdir(parents=True, exist_ok=True)

def write(name, text):
    (DEST / name).write_text(text.strip() + '\n', encoding='utf-8')

def records(text, keys):
    return [dict(zip(keys, line.strip().split('|'), strict=True)) for line in text.strip().splitlines()]

claims = records('''
A01|O ambiente mínimo instalado representa a aplicação completa.|Guias ER/README em ac22c56, 09/09|Instalação local|Importar dependências fixadas e construir Python/.NET.|RI instalou 59 dependências, construiu wheel/sdist e .NET; Redis/Compose não executados.|refutada|Não confundir ambiente mínimo, instalação de pesquisa e operação; P01/P12.
A02|177/177 arquivos completos bastam para admitir execução histórica.|DC e interpretação a testar, 09/09|177 timelines Jan–Jun/2026|Hashes, schema, identidade, clocks de recebimento da época e condições comerciais.|177 hashes/bytes conferidos; todos os recibos são posteriores às decisões; 154 mudanças antigas e 23 pares incompletos.|refutada|Integridade confirmada, conclusão de execução impedida; P02.
A03|Mudança antiga prova preço indisponível; flag de agregador prova suspensão na casa.|Vocabulário histórico PF/DC, revisto ER|Semântica OddsPapi vigente consultada em RI|Contrato primário de cada timestamp/flag.|changedAt é mudança registrada; bookmakerChangedAt opcional; bookmakerIsActive é coleta do agregador. Nenhum prova disponibilidade contínua ou aceite.|refutada|Não inverter indevidamente os significados; P02.
A04|Hash e fixtureId bastam para a identidade e estado do preço recebido.|audit_capture/audit_followup em ac22c56|Captura independente congelada|Adversariais de participantes, competição, pais/filhos e JSON.|8 regressões falharam antes; nova versão rejeita participantes trocados, JSON ambíguo, clocks ausentes e estado contraditório.|refutada|Correção validada; observação ainda não é execução; P03/P04.
A05|O auditor não pode sobrescrever uma conclusão concorrente.|audit_followup em ac22c56|Publicação offline|Concorrente que publica entre a checagem inicial e o commit.|Regressão falhou antes; hard link atômico de temporário único preserva a conclusão concorrente.|refutada|Idempotência corrigida e testada no NTFS local; P05.
A06|TemporalPolicy não permite treinar com um jogo simultâneo sem horário.|temporal-groups/v1|Replay não protegido|Dia parcialmente sem kickoff, incluindo conversão UTC.|2 regressões falharam antes; v2 agrupa todo o dia UTC quando há horário desconhecido.|refutada|Nova semântica recebe nova versão/fingerprint; P06.
A07|Backtest de eventos respeita treino temporal e um alvo por partida.|backtest_event em ac22c56; auditoria P2/P3/P7 anterior|Cards/corners legado|Dia de fronteira e várias linhas de preço do mesmo jogo.|Split por linha incluía alvos do primeiro dia de teste e multiplicava alvos no fit; regressões antes/depois preservadas.|refutada|v2 separa dias e deduplica treino; P07.
A08|Uma probabilidade ausente pode usar 0,5 e qualquer linha pode ser liquidada.|backtest_event em ac22c56|Mercados de contagem|Linha inteira, chave ausente e odds inválidas.|Inteiro podia perder no empate; fallback inventava probabilidade. v2 abstém nesses casos e registra razão.|refutada|Não declara push/asiáticos implementados; P08.
A09|Remover margem das mesmas odds cria EV positivo.|Premissa matemática explicitamente posta à prova no mandato|Normalização proporcional com S>1|Derivação algébrica e testes analíticos.|q_i=(1/o_i)/S implica q_i*o_i-1=1/S-1<0; price_hurdle e scanner verificam exclusão da oferta.|refutada|Referência independente necessária; não significa probabilidade verdadeira; P02.
A10|A conta condicional DC de 2025 é -9,24u.|DC closing-01, 09/09|380 jogos, 32 escolhas congeladas, custo 2%, banca100|Reproduzir escolhas e reconciliar com cálculo independente.|CSV/hash e 380 pares dirigidos únicos; escolhas idênticas; 100-32-0,64+23,40=90,76.|confirmada no escopo|Reprodução aritmética, sem nova validação econômica; P02/P14.
A11|O simulador disponível implementa o Brasileirão.|Nome do projeto versus simulator.py legado|monte_carlo; configuração liga|Invocar liga sem tocar banco.|Implementa grupos/mata-mata da Copa. A rejeição vinha após abrir banco; agora recusa antes.|refutada|Liga fora do caminho ativo; P09.
A12|Importar helpers numéricos não escreve no banco/pasta operacional.|backtest_event importado em testes|Import do módulo|Guard de escrita fora da pasta sintética.|2 testes detectaram tentativa de criar log em data; setup_logging passou à entrada explícita do script.|refutada|Efeito colateral corrigido, import validado; P10.
A13|Previsão exibida equivale a oferta identificada e executável.|predict.py/display.py, CLI herdada|Serving legado e cache|Vincular fixture, mando, bookmaker, estados e clocks.|_market_probs permite aproximação de data; display chama sem data; cache e odds não têm contrato do scanner estrito.|não verificada|Serving retirado da interpretação de oportunidade; dependência compartilhada preservada; P11.
A14|Worker e Compose já conectam uma casa real e provam execução.|Contratos/runtime e apresentação geral|.NET/Redis/WS|Feed real documentado, estado, clocks, capacidade e aceite.|69 testes passam; 41 dependem de Redis/processo separado. WS usa placeholder e contrato genérico; UtcNow é clock de parsing.|refutada|Infraestrutura parcial; sem feed comercial/execução; P12.
A15|CI verde da base comprova todos os novos caminhos locais.|CI ac22c56|Run 34419406215|SHA correspondente e distinção de host/escopo.|Run remoto confirmado success da base; RI tem checks locais e exclusões declaradas.|refutada|Não atribuir CI da base ao commit novo; P13.
A16|O acompanhamento continua ativo e executará a captura no horário.|Cópia TOML histórica / CONTINUIDADE DC|Automação completar-dados-do-brasileir-o|Estado atual do aplicativo e recibo futuro.|Consulta view retorna cartão sem estado legível ao modelo; não há tentativa followup em RI. Cópia documental não confirma agenda ativa.|não verificável com os dados/permissões atuais|Não duplicar nem forçar; janela permanece congelada; P15.
A17|O backup da pasta garante recuperação operacional integral.|Consolidação/migração de 09/09|Pacote recebido, Git e sistemas externos|Restauro verificável e dependências externas.|Recibo da migração é histórico, conteúdo protegido não reaberto. Novo bundle Git terá verificação em repositório bare; serviços/dados privados não restaurados.|parcialmente confirmada|Preservação recebida não garante máquina antiga inteira; P16.
A18|Mais sofisticação de modelo resolve o gargalo econômico atual.|Alternativa de pesquisa RI|xG/Poisson/NB/calibradores|Features PIT, comparação temporal independente e preços/custos admitidos.|Kernels têm testes sintéticos, mas disponibilidade/capacidade não recuperadas. Ajustar outro modelo não cria esses campos.|hipótese não verificada|Despriorizar nova busca de modelo; P02/P14.
A19|H14/H15/H9/A1 podem ser usados para preencher a revisão.|Interpretação ampla rejeitada pelo mandato|Coortes protegidas|Autorização específica inexistente.|Somente metadados/contratos permitidos; resultados e avaliadores excluídos.|não verificável com os dados/permissões atuais|Limite obrigatório de cobertura, sem aprovação implícita; P17.
''', ['id','claim','origin','scope','required','found','conclusion','impact'])
# Keep the mandated vocabulary exact.
for claim in claims:
    if claim['conclusion'] == 'hipótese não verificada':
        claim['conclusion'] = 'não verificada'

problems = records('''
P01|A01|Ambiente incompleto em comparação ao código declarado.|engenharia / alta|Core/Ops só no lock e SDK10 ausente.|Downloads oficiais e isolamento.|Instalar extras fixados em venv RI; SDK10 portátil; wheel/sdist e smoke.|Logs instalação/build, package-smoke e dotnet-build-03.|validado
P02|A02,A03,A09|Histórico não estabelece oferta executável em T-60.|dados/economia / crítica|Recibos atuais, sem capacidade/aceite; mudouAt não é recebeuAt.|Fonte com coleta temporal e condições comerciais; não recuperáveis por hash.|Conferir 177, contratos primários e alternativa The Odds API; preservar dados e não abrir novos candidatos.|Só fecha para lucro com dados temporais e condições de execução verificáveis.|bloqueado
P03|A04|Identidade/estado contraditório podiam admitir observação.|correção / crítica|Apenas fixtureId; pregame podia contradizer início/fim e hasOdds.|Catálogo congelado anterior às odds, módulo de pesquisa independente.|Exigir IDs inteiros de participantes/competição e todos os estados; checar changedAt e updatedAt.|8 falhas anteriores; final-corrections passa.|validado
P04|A04|JSON duplicado ou não finito apagava conflito no parse.|correção / crítica|json.loads normal retém última chave; aceita NaN.|Parser da auditoria offline.|strict_json_loads rejeita chaves duplicadas, NaN/Infinity e overflow float em raw e recibo.|Casos de corpo e recibo ambíguos rejeitados.|validado
P05|A05|Publicação final podia substituir auditoria concorrente.|concorrência / alta|Path.replace após exists tinha corrida.|Filesystem com link atômico; NTFS testado.|Temporário UUID e os.link que falha se destino existe; remover só próprio temporário.|concurrency-before falha; teste passa após mudança.|validado
P06|A06|Agrupamento misto permitia leakage dentro do mesmo dia.|temporal / crítica|Data isolada ordenada antes do kickoff conhecido.|Consumidores research/temporal_replay, fora da coleta protegida.|temporal-groups/v2 colapsa dia UTC parcialmente incompleto; rejeita v1 relabelado.|2 casos antes falham; temporal-after 7 passam.|validado
P07|A07|Split por linhas e treino repetido por odds enviesavam replay.|temporal/modelagem / crítica|80% das linhas, não eventos; mesmo dia nos dois lados.|Backtest legado de eventos; sem execução de dados protegidos.|v2 usa eventos únicos, dia integral fora do treino e rejeita alvos/identidade conflitantes.|4 regressões antes + casos adicionais; final-corrections.|validado
P08|A08|Fallback 0,5, linha inteira e odds inválidas podiam gerar conta falsa.|matemática/contabilidade / alta|Probabilidade inventada, igualdade tratada como derrota, odds sem domínio.|Somente linhas meia-unidade implementadas.|Abstenção explícita sem probabilidade válida, linha suportada ou odds finitas >1.|Testes de inteiro, ausência, NaN, infinito, bool e odds <=1.|validado
P09|A11|Simulador de Copa abria banco antes de recusar liga.|domínio/efeito colateral / alta|Validação tardia no monte_carlo.|Não existe motor de classificação do Brasileirão neste caminho.|Recusar configuração de liga antes de db.connect; retirar simulação de liga das capacidades atuais.|domain-before falha; final-corrections passa.|validado
P10|A12|Import criava log operacional.|isolamento / alta|setup_logging(ROOT/data) no topo do módulo.|Backtest de eventos, importado por ensaios.|Inicializar log só na execução explícita; testes continuam sem dados operacionais.|2 falhas iniciais de escrita eliminadas; test_audit_fixes passa.|validado
P11|A13|Serving usa associação aproximada de odds/cache sem admissão estrita.|arquitetura/dados / crítica|display chama _market_probs sem data, helper aproxima jogo.|predict/display/config/modelos são compartilhados; mudança poderia afetar coleta vedada.|Marcar serving como legado e não admissível para decisão; scanner isolado permanece caminho de pesquisa.|Só fecha com separação segura de consumidor e contrato fixture+clocks; sem alterar coleta protegida.|bloqueado
P12|A01,A14|Integração local real Redis/Compose e feed comercial ausentes.|integração / crítica|Docker não encontrado no PATH nem local padrão; 41 testes .NET pulados.|Runtime descartável Redis identificado por run_id e fornecedor legítimo.|Recuperar SDK/build; manter .NET parcial; não apontar testes a serviços existentes nem inventar adaptador.|Build+69 testes não fecham integração; requer host isolado e dados admitidos.|bloqueado
P13|A15|Relatos de CI/lint confundem escopos.|validação / média|CI só da base; ruff . inclui cópias históricas fora da CI.|Base Git, escopo CI e relatórios de execução.|CI da base confirmado; Ruff CI passou, format390, tipagem explícita; 805 achados globais preservados fora do escopo ativo.|Recibos com versões, escopos e ausência de aprovação global.|validado
P14|A10,A18|Métricas condicionais e testes podem ser promovidos indevidamente a lucro.|economia / crítica|Closing sem clock e referência comprometida; 3 snapshots=1 evento.|Capacidade, custos, unidade monetária e avaliação futura independente.|Conta decimal reproduzida; abstenções preservadas; nenhuma otimização/novo holdout.|Somente fecha com validação futura pré-especificada e custos próprios verificáveis.|bloqueado
P15|A16|Estado atual da agenda não é comprovado pelo TOML histórico.|operação / alta|view sem estado modelável; nenhuma tentativa followup.|Aplicativo ligado e scheduler; tarefa anterior.|Não duplicar nem mudar agenda; conferir estado pelo aplicativo antes da janela e manter auditor corrigido.|Recibo da execução na janela ou motivo explícito de não execução.|bloqueado
P16|A17|Recuperação de dados operacionais e máquina antiga não comprovada nesta rodada.|preservação / alta|Manifesto recebido tem escopo limitado; dados protegidos não podem ser abertos.|Pacote recebido, computador antigo, autorização específica para operação.|Preservar; verificar recuperação Git separadamente; explicitar instalação externa e limites.|Bundle/clone bare/fsck no recibo final; não é restauro de bancos/serviços.|bloqueado
P17|A19|Cobertura de coortes/avaliadores protegidos vedada.|permissões / crítica|Mandato proíbe ler resultados e executar avaliadores.|Autorização não concedida.|Somente metadados/documentação permitida; excluir conteúdos, avaliações e dependências operacionais de mudanças.|Preservação do diff; nenhuma conclusão empírica dessas coortes.|bloqueado
''', ['id','claims','problem','severity','cause','dependencies','action','closure','status'])

registry = {'review':'RI-20260909','base':'ac22c56c3318623e07a722f34d44dc6cd877ea37',
            'dated_at':datetime.now(UTC).isoformat(),'claims':claims,'problems':problems}
write('REGISTROS.json', json.dumps(registry, ensure_ascii=False, indent=2))

def table(rows, labels):
    keys = list(labels)
    return '\n'.join(['| ' + ' | '.join(labels.values()) + ' |', '| ' + ' | '.join('---' for _ in keys) + ' |'] +
                     ['| ' + ' | '.join(str(row[key]).replace('|',' / ').replace('\n',' ') for key in keys) + ' |' for row in rows])

write('ALEGACOES.md', '# Matriz central de alegações — RI-20260909\n\nGerada de [REGISTROS.json](REGISTROS.json). Conclusões referem-se ao escopo/versão indicado; “refutada” descreve a premissa anterior, mesmo quando o defeito já foi corrigido. Evidências compactas em [tests.json](evidence/tests.json) e nos mapas.\n\n' + table(claims, dict(zip(claims[0], ['ID','Alegação/premissa','Origem/data','Escopo/versão','Evidência exigida','Evidência encontrada','Conclusão','Impacto'], strict=True))))
write('PROBLEMAS.md', '# Registro central de problemas — RI-20260909\n\nGerado de [REGISTROS.json](REGISTROS.json), com referências à [matriz](ALEGACOES.md). Bloqueado indica requisito externo ou restrição atual, não um problema resolvido por documentação. O projeto permanece globalmente não pronto.\n\n' + table(problems, dict(zip(problems[0], ['ID','Alegações','Problema','Tipo/gravidade','Evidência/causa','Dependências','Correção/ação','Teste de fechamento','Status'], strict=True))))

write('MAPA_SISTEMA.md', '''
# Mapa real do sistema e decisões — RI-20260909

Base ac22c56, mais correções datadas RI. O inventário inicial cobre 421 arquivos de código: 365 receberam inventário estático de AST/imports/funções/efeitos; 56 foram limitados a metadados por proteção ou proximidade operacional. Isso não é certificação linha a linha. A leitura semântica concentrou-se nos caminhos abaixo e foi confrontada com regressões e 105 arquivos de testes inicialmente selecionados. [Inventário](evidence/inventory-summary.json), [execuções](evidence/tests.json), [alegações](ALEGACOES.md), [problemas](PROBLEMAS.md).

| Subsistema / caminhos no repo | Finalidade, entradas → saídas; dependências / consumidores | Estado real, verificação e decisão |
| --- | --- | --- |
| ingest.py, providers/, scripts de aquisição DC | Fontes externas → fixtures/odds/estatísticas; HTTP, schemas, SQLite; alimenta pesquisa e runtime | Código presente; dados reais só do escopo DC autorizado. Testes sintéticos de parsing/contratos. Manter ingestão operacional parada; corrigir admissão independente, sem ativar coletores. P02/P03. |
| db.py e migrations versionadas | Schemas/índices e operações sobre tabelas; sqlite3; consumidores ingest, features, predict | Migrations/consultas cobertas em bancos sintéticos. Nenhum DB operacional aberto/restaurado. read_only necessário para pesquisa; efeitos de criação não são inócuos. P10/P16. |
| Identidade, promotions, calendários e aliases | IDs/clubes/mando/datas → entidades normalizadas; rosters públicos e catálogos | CSV2025:20 clubes,38 jogos por clube,380 pares dirigidos únicos. Não valida toda regra CBF, adiamentos ou aliases de todas as fontes. Captura fixa agora exige IDs de participantes/competição. P03. |
| model.py, model_params.py, optimize.py, event_models.py | Alvos de gols/contagens, ratings e parâmetros → lambdas/distribuições; numpy/scipy/Core | Poisson/NB e correção DC, massa/normalização e domínio testados sinteticamente. Inspeção de média/variância, integração DC e convergência. Manter kernels; sem novo fit de dados protegidos ou afirmação de vantagem. P14. |
| ratings.py, adapters/feature_builder.py | Resultados anteriores e estatísticas → Elo/features; SQLite; modelos/serving | Ordenação por data e blocos evita mesmo dia em rotas examinadas. Faltam published_at/ingested_at por feature no legado: causalidade de calendário não é disponibilidade histórica demonstrada. Não reconfigurar dependências compartilhadas. P11/P17. |
| xg_model.py / ensemble_xg | xG/goals e cache → blend opcional; display/predict | Desligado por configuração. Comentário sobre fallback “sem viés” não demonstrado; cache/fit não estabelecem PIT completo. Manter desabilitado; não ajustar outro modelo para suprir preço faltante. A18/P11. |
| research/dynamic_xg.py e módulos de avaliação/calibração | Matches com disponibilidade, treinamento/calibração separados → modelos e métricas | Experimental; testes sintéticos e leitura do contrato temporal; nova avaliação econômica não executada. Não reciclar dados vistos como holdout. Nenhuma conclusão quantitativa de coortes. P14/P17. |
| temporal_policy.py, research/temporal_replay.py | Kickoff/date → grupos e fingerprint → replay | v2 corrigida: dia UTC inteiro se qualquer horário faltar, versão antiga não reutilizada sob nova semântica. Alternativa de inventar meia-noite rejeitada. Duas regressões antes/depois. P06. |
| backtest_event.py | Stats finais como labels, Elo histórico e linhas open/close → replay cards/corners | v2 corrigida para treino por evento/dia, conflito explícito e abstenção por linha/probabilidade/odds. Não prova quando abertura existiu, custos, aceitação ou capital conjunto. Nenhum saldo novo gerado. P07/P08/P10. |
| research/price_strength/quotes.py | Cotações identificadas e clocks → referência independente, candidato ou abstenção | Manter scanner isolado: exclui ofertante, exige conjunto completo, último estado conhecido, idade/skew, domínio e identidade. “Sem margem” é estimativa. O scanner produz candidatos, não apostas aceitas. A09/P02. |
| historical_admission.py, live_capture_admission.py, auditor DC | Raw+recibos+identidade fixa → rejeição/observação API | Parser estrito, identidade e flags corrigidos. Histórico sem recibo da época não vira prospectivo. Um flag de coletor não prova status comercial. P02–P05. |
| closing_scenario.py, price_hurdle.py | Universo/choices congelados + labels2025 → ledger simulado/conta Decimal | Contabilidade conferida por segundo cálculo. Principal/retorno/custo separados, pendentes retêm capital; só 1X2 vitória/derrota. Manter como cenário e teste, sem mecanismo financeiro. P14. |
| predict.py, display.py, CLI | Config/cache/modelos e associação aproximada de odds → texto/JSON | Ajuda do wheel funciona; texto ainda tem herança de seleções internacionais. display usa helper de odds sem data. Não há frontend web separado. Retirar esse serving do caminho de decisão econômica; não alterar dependência da operação protegida. P11. |
| simulator.py | Grupos e mata-mata de Copa → Monte Carlo do torneio legado | Não implementa classificação de liga. Recusa liga antes de abrir DB. Não criar simulador sem efeito sobre a decisão econômica desta rodada. P09. |
| kernel_daemon.py, kernel runtime/protocolos | Redis de snapshots/jobs → inferência e respostas; Core/Numba, .NET | Contratos/erros/concorrência cobertos por mocks e dados sintéticos. Socketpair local de asyncio permitido no harness; rede externa continua bloqueada. Sem Redis real nesta rodada. P12. |
| dotnet/LineupWorker e contratos JSON | WebSocket genérico/Redis → cache/sinais/observabilidade | SDK10.0.401 instalado localmente; restore/build Release com warnaserror;69 passam,41 pulados. Timestamp UtcNow de parsing não é publicação da casa. Placeholder exchange.invalid e subscrição dependente do fornecedor. Infraestrutura parcial e feed desconectado. P12. |
| compose.yaml, Dockerfiles e .github/workflows/ci.yml | Imagens e configuração → kernel/Redis/worker; Docker, GitHub Actions | CI da base confirmada; Docker ausente no host. Sem compose up, sem modificar serviços existentes. Integração em runtime descartável é dependência aberta, não disfarçada por mocks. P12/P13. |
| pyproject.toml, uv.lock, constraints, ecosystem_plugin | Dependências fixadas e plugin → wheel/sdist/CLI | Todos extras instalados em novo venv; hashes Core/Ops do lock; build e smoke do wheel. Metadados do plugin não comprovam prontidão econômica. Sistemas Windows/Git/Codex permanecem dependências externas. P01/P13. |
| Testes, segurança e logs | Fixtures sintéticas → JUnit, lint/tipagem; pytest/guard | 1.291 casos únicos com último resultado aprovado e1skip, somando execuções delimitadas; não é suite única integral. Lint CI passa, cópias históricas fora da CI têm805 achados preservados. Sem segredos, DB/Redis operacionais ou avaliadores protegidos. P10/P13/P17. |
| Automação independente DC | Agenda do aplicativo → helper de captura → auditor offline | Auditor corrigido ativado por hash; coletor e agenda sem alteração; estado atual da agenda não exposto ao modelo. Nenhuma tentativa na janela ainda. Não duplicar. P15. |
| H14/H15/H9/A1 e dependências adjacentes | Coortes, contratos, agendas, claims e avaliadores | Somente metadados/contratos permitidos. Proibido consultar resultados intermediários ou executar avaliações; nenhuma homologação científica/operacional desses caminhos. P17. |
| Migração e backups | Pacotes recebidos, manifestos e Git → preservação/recuperação | Integridade dos novos insumos reconferida; migração protegida mantida pelo recibo anterior. Recuperação Git em bare isolado no fechamento; não é restauração operacional. P16. |

As razões históricas de cada arquitetura não estão todas registradas. As decisões desta revisão são explícitas: manter kernels e scanner verificáveis; corrigir rejeição, agrupamento e replay; limitar serving/simulador às capacidades reais; postergar novo modelo; não substituir dados indisponíveis por imputações comerciais. A facilidade de implementar um adaptador não é evidência de que exista uma fonte de execução admissível.
''')

write('MAPA_DADOS.md', '''
# Dados, campos e recuperação — RI-20260909

Cada localização abaixo é relativa a `C:/BRASILEIRAO/work`, salvo indicação. Recibos: [resumo](evidence/data-summary.json), [identidade](evidence/frozen-identity.json), [fontes](evidence/public-source-receipts.json). Nenhum desfecho de 2026 foi interpretado ou unido a preços nesta rodada.

| Conjunto/finalidade | Origem, versão/local/período e granularidade | Campos, chaves, unidades e transformação | Estado/validação/limite |
| --- | --- | --- | --- |
| 177 históricos, comparação causal T−60 | OddsPapi, raw DC Jan–Jun2026; universo.json, acquisition.json e transport_repair.json | Fixture/bookmaker/market101/outcome e createdAt; odds decimais; último estado da timeline até corte | 177/177 SHA256+bytes conferidos:623.271.596 bytes. Recibos todos posteriores à decisão.154 com última mudança antiga,23 pares incompletos. Íntegros, insuficientes/inadmissíveis para execução histórica; não interpretar idade da mudança como recibo. |
| CSV público e conta congelada 2025 | Football-Data; data-completion-2026-09-09/public_sources/football_data_bra_origin_csv.csv | Season filtrada2025 ANTES de ler labels; data+home+away;1X2 e placares; odds decimais |380 linhas,20 clubes,38 jogos por clube,380 pares dirigidos,0duplicação.222 preços individuais inválidos/ausentes,126 sem diferença dentro do filtro,32 escolhas idênticas. Sem clock decisório e referência com aviso histórico de desatualização. |
| Catálogo do fixture fixo | DC prospective_pilot/calendar.json e selected_fixture.json; prévio às odds | fixtureId id1000032566887012, participant1Id1982, participant2Id1967, sportId10, tournamentId325, seasonId137706 | Mando e competição congelados conferidos; nomes Coritiba FC PR / CA Paranaense PR. Hash do catálogo/seleção no recibo RI. Não selecionado novo evento. |
| Piloto, observação de estado API | DC prospective_pilot;3 respostas do mesmo fixture | requested_at, received_at, hasOdds/statusId, trueStart/End, pais/filhos, changedAt e bookmakerChangedAt |3 capturas=1evento independente;0pares API admitidos,0execuções. Recibos observam chegada à API/collector; não aceite da casa. |
| Captura futura já congelada | DC followup e followup_audit;11/09/2026 | decisão23:00Z, kickoff12/09 00:00Z; Pinnacle/bet365.bet.br; recebido até120s antes da decisão | Dependente de coleta futura; nenhuma tentativa presente na verificação RI. Janela/reserva/quota fixas; hash auditor corrigido, coletor inalterado. Não consultar resultado do jogo. |
| Features, ratings, xG e inferência | Schemas/código versionados; DB operacional e snapshots preservados | data/kickoff/availability, clubes, alvos, xG, ratings, cache/model version | Contratos e síntese testados; bancos reais não abertos. Imputação de xG por gols é proxy, não xG observado. Publicação/revisões históricas por campo não validadas. |
| Migração e coortes protegidas | C:/BRASILEIRAO/DADOS_PRESERVADOS;recibo de migração09/09 |12.423 entradas+manifesto,9.477.623.208 bytes segundo recibo anterior;5snapshots SQLite | Preservação documental/metadados; sem nova consulta de tabelas ou resultados. Conteúdo não autorizado não serve à recuperação da pesquisa RI. |
| Contratos oficiais recuperados | RI/public-sources;receipts.json, horáriosUTC e SHA256 | OddsPapi atual/histórico/mercados, The Odds API histórico; HTML bruto local |4 contratos HTTP200; duas tentativas Football-Data HTTP503. Fonte alternativa consultada, sem conta/pagamento/APIkey. Não há clocks comerciais novos recuperados. |
| Dependências/build | RI/venv,dotnet-sdk,dotnet-work,dist,tools | Lock+hashes, Python3.13.12;Core3.2.0/Ops4.1.0;SDK10.0.401;Node copiado do runtime disponível | Instalação nova verificada, artefatos de build e testes isolados. Windows/Git/Codex/serviços externos não cabem na garantia da pasta. |

Hashes estáveis dos insumos: universo `6264b2a1b795928fdf0dc6476e311535a42fbc96c12caf5cf881777b7779caba`; CSV `ba3e9ea79ab4091b117a901f3914940cea07f1fe06de0deb57af5076f664ccb6`. O reparo de transporte DC foi usado apenas para completar a tentativa inicialmente falha; as duas tentativas permanecem preservadas. A primeira execução do auditor RI interrompeu nessa distinção e foi corrigida, sem sobrescrever evidência de tentativa.

A aquisição legítima desta revisão fez seis GETs diretos de fontes de dados/contratos, dos quais quatro tiveram HTTP200 e dois503. GitHub CI e metadados .NET somam duas consultas de engenharia, além de downloads de dependências oficiais. Consultas web oficiais complementaram a leitura. Não houve API autenticada de odds, consumo da reserva20, novo cadastro, compra, aposta ou inferência de custo pessoal zero.

O [contrato OddsPapi](https://oddspapi.io/us/docs/get-odds) distingue atividade de coleta, suspensão, estado de mercado e mudança registrada. O [histórico](https://oddspapi.io/us/docs/get-historical-odds) não transforma recebimento atual em recibo da época. A [alternativa The Odds API](https://the-odds-api.com/liveapi/guides/v4/#historical-odds) foi consultada; acesso histórico comercial não pode ser contratado sob este mandato. Mesmo uma nova timeline não provaria capacidade pessoal ou aceite. Portanto P02/P14 exigem observações prospectivas e condições próprias verificáveis; uma nova captura poderá informar cobertura de estado, sem provar rentabilidade.
''')

write('RESULTADO.md', '''
# Revisão integral no escopo permitido — RI-20260909

**Projeto globalmente não pronto; preços executáveis e lucro líquido futuro não demonstrados.** A revisão do escopo permitido foi executada com correções, recuperação de ambiente/contratos, reprodução da conta congelada e validação delimitada. A conclusão da revisão não encerra os bloqueadores externos nem realiza o objetivo econômico. Base inicial `main/ac22c56c3318623e07a722f34d44dc6cd877ea37`, remoto main conferido nessa mesma base antes da integração. Trabalho solo, todo material final sob `C:/BRASILEIRAO`.

Registros centrais: [alegações](ALEGACOES.md), [problemas](PROBLEMAS.md), [mapa do sistema](MAPA_SISTEMA.md), [mapa de dados](MAPA_DADOS.md), [protocolo anterior ao desempenho](PROTOCOLO.md), [reprodução](REPRODUZIR.md). Os resumos derivam de [REGISTROS.json](REGISTROS.json); problemas bloqueados não são apresentados como solucionados.

## O que mudou e por quê

Foram demonstrados antes da correção:8 casos de admissão incorreta,2 de agrupamento temporal,1 de publicação concorrente,1 de abertura indevida do banco pelo simulador e4 de backtest de eventos. A suíte ampla também detectou2 tentativas de log operacional durante import. Corrigiram-se identidade/flags/clocks, parsing JSON, publicação atômica, dias parcialmente sem kickoff, treino por evento/dia e abstenção em linhas/probabilidades/odds inválidas. O simulador legado passa a recusar liga antes de abrir DB; importar backtest_event não cria log.

O auditor offline independente corrigido foi copiado para seu caminho ativo com backup e hash idêntico ao código testado. O coletor, fixture, casas, decisão, quota/reserva e agenda não foram alterados. H14/H15/H9/A1 e dependências capazes de alterar coleta ficaram preservados; nenhuma execução de avaliadores, join com seus desfechos, renovação de claims ou consulta aos bancos operacionais.

Recuperou-se um ambiente completo de pesquisa Python, sem modificar o ambiente mínimo da captura, e o SDK.NET10 portátil. Restore/build .NET e pacote Python passaram. Nenhum serviço de produção, Redis ou Compose foi iniciado. O build não converte um adaptador genérico de WebSocket em integração comercial.

## Rodada econômica: os 14 itens

1. **Pergunta.** A cadeia atual sustenta comparação causal entre oferta Bet365 e referência Pinnacle, ou ainda admite falsos positivos de identidade, estado e conta?
2. **Prioridade.** Resolver a validade da medição muda a decisão antes de buscar outro modelo. Mais dados com o mesmo clock inadequado não completam a prova.
3. **Hipótese/mecanismo.** Diferença de preços entre casas independentes, com ofertante excluído da referência proporcional, poderia motivar investigação. q sem margem é estimativa; das mesmas odds resulta EV=1/S−1, negativo quando S>1.
4. **Experimento.** Protocolo RI registrado antes do cálculo:177 timelines já recebidas,380 jogos2025 com escolhas DC congeladas,3 capturas de1evento e ensaios adversariais. Não houve tuning, novo candidato, escolha retrospectiva de janela/casa ou uso de dados vistos como holdout.
5. **Dados/fontes.** Todos177 hashes conferidos;CSV íntegro com380partidas únicas e20clubes. Contratos OddsPapi e The Odds API recebidos;duasURLs Football-Data retornaram503. Evidência e denominadores em MAPA_DADOS.
6. **Disponibilidade temporal.** Os177 recibos são posteriores às decisões históricas;154 alterações antigas não provam indisponibilidade,23 pares estavam incompletos. Closing2025 não contém instante decisório demonstrado. Piloto com recibo real não prova aceite/capacidade.
7. **Resultado.** Zero execuções admitidas;0pares API nas3capturas. Reproduziu-se exatamente o cenário conhecido:380jogos,32apostas condicionais e348abstenções.222 sem preços individuais válidos,126 sem diferença no filtro. Banca100u,stakes32u,custo0,64u,retornos com principal23,40u,saldo90,76u,perda−9,24u. ROI condicional sobre stakes−28,875%;retorno condicional sobre banca−9,24%. Nenhuma dessas taxas é ROI executável. Exposição máxima diária simulada3u,0principal pendente,0aporte. Janela das escolhas16/08 a04/12/2025;horas de capital preso não disponíveis.
8. **Custos.**2% do stake é hipótese já congelada, não tarifa pessoal. A margem está embutida nas odds; não foi debitada duas vezes. Capacidade, moeda, imposto pessoal,slippage,recusa,preenchimento parcial,infraestrutura e manutenção continuam desconhecidos. Nenhuma compra ou execução financeira nesta rodada.
9. **Riscos.**32escolhas concentradas por mês:8agosto,10setembro,13outubro,1dezembro;mesmas equipes e dias trazem dependência.3snapshots não são3eventos independentes. Fonte com referência comprometida e multiplicidade histórica de pesquisas impedem atribuir o saldo a um teste independente.
10. **Limitações.**Reprodução confirma integridade e aritmética, não valida causalidade nem sustentabilidade. Sem dados admissíveis, intervalo de lucro executável não é estimável; não se fabrica significância ou probabilidade de sucesso a partir desses números. Falha503 não prova ausência de oportunidade.
11. **Testes.**105arquivos selecionados inicialmente. Primeiro lote:1.139passaram,131falharam,1skip. Desses131,129 provinham do limite do harness(126socketpair,3arquivos públicos explicitamente permitidos),2 revelaram log indevido. Após correções:171passaram na reconferência;68nas correções finais. Consolidando últimos resultados por caso:1.291aprovados,1skip,sem falha remanescente no conjunto escolhido.4testes verificaram que asyncio local funciona e rede/SQLite/escrita externa continuam bloqueados. Não é uma execução integral da suíte. .NET:69passaram,41skip. Ruff no escopo CI passou;390arquivos formatados. Tipagem e pacote têm recibos separados.
12. **Estado da evidência.**Aritmética condicional confirmada; hipótese de lucro executável não mensurável com esses insumos. Premissa de suficiência dos dados/admissões anteriores refutada. Testes são evidência de software.
13. **Decisão.**Encerrar este experimento após refutar a premissa de suficiência e concluir correções necessárias, dentro do orçamento. Manter abstenção financeira; não procurar variante positiva. Novo modelo perde prioridade. A recuperação prospectiva deve manter o protocolo já congelado e a separação entre observação, capacidade, custos e validação.
14. **Próxima informação decisiva.**O recibo dentro da janela fixa, com identidade e estado de ambas as casas admitidos pelo auditor corrigido. Ele decide se há cobertura de observação para continuar. Para avançar à validação econômica, ainda serão necessários preços prospectivos independentes e condições de capacidade/custo verificáveis; uma captura não basta.

## Três estados finais separados

| Dimensão | Estado e escopo | Evidência e limite |
| --- | --- | --- |
| Prontidão técnica | **Pronto no escopo dos módulos corrigidos e testes isolados; projeto globalmente não pronto.** | Python/build/smoke e.NETbuild verificados. Redis/Compose real,feed comercial,serving com identidade/clocks e operação protegida sem aprovação. P11/P12/P17. |
| Admissibilidade dos dados | **Admissíveis para integridade, contratos e reprodução aritmética2025; insuficientes/inadmissíveis para inferir execução em T−60 ou lucro futuro.** |177/177 íntegros,380partidas,3capturas/1evento. Sem recibos históricos da época,capacidade/custos;nenhuma admissão executável. P02/P14. |
| Evidência econômica | **Lucro executável não mensurável; evidência insuficiente.** |−9,24u apenas no cenário conhecido. Premissa de dados já suficientes refutada. Nenhum critério cumprido para liberar capital ou declarar rentabilidade. |

A descoberta que mais mudou a decisão foi que **um recibo íntegro ainda podia admitir identidade ou estado contraditório**: corrigir essa barreira veio antes de coletar/ajustar mais. A hipótese que perdeu prioridade foi **substituir já a referência por novo modelo xG**. A próxima informação que muda a decisão é **a observação válida dentro da janela congelada**, seguida das condições comerciais faltantes.

## Cobertura, bloqueios e preservação

Os mapas cobrem os subsistemas permitidos, com profundidade declarada e leitura semântica dirigida às dependências reais. Os421arquivos inventariados não equivalem a421arquivos homologados.56ficaram em metadados por proteção/proximidade. Bancos operacionais,coortes,Redis real,serviços e conteúdo privado não foram examinados. A revisão não conclui que essas áreas estejam corretas.

P02/P14 exigem informação comercial e temporal ausente após tentativas legítimas. P12 exige runtime descartável e fornecedor documentado. P15 exige estado atual do aplicativo/recibo de execução; a cópia TOML não basta e nenhuma agenda nova foi criada. P11/P17 têm limite de alteração imposto pela preservação das dependências da coleta. P16 distingue backup Git testado de recuperação operacional proibida/não realizada. Detalhes e critérios para destravar estão no registro central.

Os históricos PF/DC/ER,raws,negativos,protocolos e tentativas foram preservados. Guias atuais foram atualizados por novo checkpoint; resultados congelados não foram reescritos. Hashes,comandos,diff,commit,backup e igualdade das entregas constam dos recibos em `C:/BRASILEIRAO/AUDITORIA/REVISAO_INTEGRAL_2026-09-09.json` e no diretório RI. Uma primeira tentativa de Pyright solicitou versão latest e criou cache externo; foi interrompida, os diretórios novos foram movidos para RI e a validação repetida com a versão fixa e Node copiado. O resultado usado é o de versão fixa, não o ensaio interrompido.
''')

write('REPRODUZIR.md', '''
# Reprodução e evidência — RI-20260909

Raiz de execução `C:/BRASILEIRAO/work/revisao-integral-2026-09-09`; repo `C:/BRASILEIRAO/brasileirao-predictor`. O recibo final identifica commit e hashes. Windows/Git/Codex/rede para baixar dependências são externos à pasta; venv não é pacote portável sem reinstalação. Todos os comandos abaixo têm escopo isolado, exceto o acesso a fontes públicas explícitas. Não executar avaliadores protegidos ou restaurar DB operacional.

## Instalação realizada

Python3.13.12. `uv sync --all-extras --frozen --no-install-project` com `UV_PROJECT_ENVIRONMENT` apontando ao venv RI, `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`, TEMP/TMP em RI e interpretador explicitamente indicado.59dependências do lock;Core3.2.0 eOps4.1.0 com hashes fixados. [Versões](evidence/environment.json).

SDK.NET10.0.401 baixado do endereço oficial obtido em releases.json, SHA512 conferido antes de extrair em RI. `prepare_dotnet.py` criou cópia de código/contratos públicos em dotnet-work. `run_dotnet.ps1` usa NuGet.Config isolado, perfil/cache/TEMP em RI, restore locked, build Release --warnaserror e testes. Primeiras tentativas falharam por variáveis Windows necessárias removidas; a terceira manteve somente caminhos do sistema necessários e passou. Não iniciou worker/Redis;41testes de integração explicitamente pulados. [SDK](evidence/dotnet-sdk.json).

## Ensaios e reprodução dos dados

`run_isolated.py` deve receber um nome NOVO de saída seguido de arquivos de testes explícitos. Ele remove credenciais do ambiente, bloqueia rede/subprocessos/SQLite externo e escreve apenas nessa saída. Permite apenas socketpair de loopback criado pelo próprio stdlib e dois arquivos públicos exatos usados por testes existentes. O cliente nativo curl_cffi tem transporte real bloqueado. O harness não é um sandbox contra código hostil arbitrário: é uma barreira de efeitos para testes previamente inspecionados.

Lote amplo: lista congelada `baseline-test-selection.json`,105arquivos. Reconferência: `test_audit_fixes.py test_calibration_gate.py test_kernel_protocol.py test_kernel_runtime.py test_kernel_v2_runtime.py test_promotions_dataset.py test_integral_review_domain.py test_integral_review_admission.py`. Rodada final68: `test_audit_fixes.py test_integral_review_event_backtest.py test_live_capture_admission.py test_followup_capture_contract.py test_integral_review_admission.py test_integral_review_domain.py test_temporal_policy.py test_temporal_replay.py`. JUnit e tentativas mantidos em pastas distintas. [Contagens por rodada e IDs únicos](evidence/tests.json).

`audit_data.py` verifica somente a allowlist DC,hashes,universo,clocks,catálogos e o CSV filtrado2025. Nunca abre DB ou desfechos2026. Não rerodar sem motivo: saída existente é protegida por criação exclusiva. `data-audit-02` é a execução bem-sucedida após reconhecer o reparo de transporte já registrado em DC. Não é uma nova validação econômica. [Conta compacta](evidence/closing-summary.json).

`recover_public.py` foi executado uma vez por URL. Raw/recibos locais em public-sources. Não repetir downloads de odds,consultas autenticadas ou lotes íntegros; não reutilizar esse script como autorização futura automática.

## Checks de engenharia

Ruff0.16.6: `ruff check brasileirao_predictor brasileirao_scripts tests`; `ruff format --check` nos mesmos diretórios:390arquivos. A expansão `ruff check .` encontrou805questões em cópias/documentação/scripts históricos fora da CI; log preservado,sem reformatar resultados congelados. O executor audit_followup alterado recebe check próprio. Não tratar esse resultado como lint global limpo.

Pyright1.1.411 fixo: executar `tools/node.exe venv/Lib/site-packages/pyright/dist/index.js --pythonpath venv/Scripts/python.exe` no repo. O projeto exclui research da análise padrão; por isso há também `--project RI/pyrightconfig.json` cobrindo os três módulos puros de price_strength e o auditor alterado. Não usar PYRIGHT_PYTHON_FORCE_VERSION=latest. A tentativa inicial está preservada e não compõe aprovação.

`uv build --out-dir RI/dist` criou sdist e wheel. `package_smoke.py` extrai wheel em nova pasta sem .env/SQLite,confere import a partir dele e executa apenas `brasileirao-predict --help`,sem rede/DB. Não demonstra previsões com dados reais. O CLI ainda contém texto legado de seleções internacionais; serving não é oferta executável.

CI remoto da **base** ac22c56: [run34419406215](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34419406215), success confirmado via API pública. Não atribuir esse CI às alterações RI. CI integral envolve avaliadores e serviços fora do escopo desta rodada; os checks usados para integrar RI são os isolados declarados.

## Ativação e recuperação

Só o auditor offline da captura independente foi atualizado no caminho ativo,após testes e checagem de ausência de execução concorrente. Versão anterior em RI/previous-active. Coletor SHA256 `31de8315c687cc596ae3fb9aebd221701e9f6df690903248c15dfb9b84b33d88`, inalterado. [Ativação](evidence/activation.json). O manifesto de reprodução atual recebe o novo hash e guarda referência ao anterior.

No fechamento, criar bundle Git com nome novo em `C:/BRASILEIRAO/BACKUPS`,verificar,clonar em bare novo sob RI e executar fsck. Não criar checkout operacional,importar tarefas ou abrir bancos. A entrega em ENTREGAS é conferida por hashes contra o diretório de revisão. Esses atos comprovam recuperação do Git e cópia de artefatos,sem afirmar recuperação completa de serviços/dados privados.
''')

write('PROXIMO_PROMPT.md', '''
# Continuação após a revisão RI-20260909

Trabalhe sozinho em C:/BRASILEIRAO/brasileirao-predictor, mantendo novos arquivos em C:/BRASILEIRAO. Leia integralmente o mandato original em C:/BRASILEIRAO/INSTRUCOES/MANDATO_RECEBIDO_2026-09-09.txt e o prompt consolidado original, depois docs/ESTADO_ATUAL.md, esta revisão RI (RESULTADO,REGISTROS,MAPAS,REPRODUZIR) e a continuidade DC. Não reinicie a revisão como se não tivesse ocorrido.

Confira HEAD/branch/remote/diff,horário e concorrência. O recibo C:/BRASILEIRAO/AUDITORIA/REVISAO_INTEGRAL_2026-09-09.json identifica a integração/backup. Não reverta alterações de outra sessão. As correções RI estão validadas no escopo isolado; o projeto continua não pronto, com lucro executável não mensurável. Não buscar nova variante positiva nem chamar reprodução2025 de holdout.

Prioridade: acompanhar a única captura já congelada na tarefa anterior01a08756-2962-7c43-9773-c790cc81329d,automação completar-dados-do-brasileir-o. A RI não confirmou o estado legível da agenda ativa e não a duplicou. Antes de qualquer ação,conferir aplicativo e recibos. Não criar outra automação ou importar agendas históricas.

Fixture id1000032566887012,Pinnacle/bet365.bet.br,decisão11/09/2026 23:00UTC,kickoff12/09 00:00UTC. Preservar protocoloDC: janela de início22:55–22:59:15UTC,captura-alvo22:58:30UTC,reserva20,plano gratuito,quota,idempotência,máximo1consulta de odds. Se chegar fora da janela,não reconstruir disponibilidade nem consultar desfecho. Antes da janela,não consumir API. Os helpers ficam em C:/BRASILEIRAO/work/data-completion-2026-09-09; conferir hashes do auditor RI e coletor congelado antes de usar. Não renovar claims/atestados de coortes.

Auditar a captura em processo separado,sem credenciais,aplicando JSON estrito,hash+recibo,participantes/competição,clocks/estado e horário congelado. Não admitir execução: mesmo observação API válida precisa de capacidade,custos e validação futura. Preservar rejeições e tentativas. Se não houver observação válida,registrar o requisito e a falha sem otimizar fixture/casa/janela. Ao terminar a captura auditada,ou após12/09,reavaliar acompanhamento existente e pausá-lo se não restar ação útil autorizada.

Para resolver P11/P12 antes de ativar aplicativo: ambiente Redis/Compose descartável,contrato real do fornecedor e consumidor com identidade/clocks estritos são requisitos. Não apontar testes aos serviços existentes ou bancos protegidos. Alteração de dependência que possa mudar a coleta H14/H15/H9/A1 permanece vedada. Novas features/modelos só merecem experimento após justificar como mudam uma decisão com dados admissíveis.

Preserve integralmente H14/H15/H9/A1,resultados,observadores,artefatos,agendas,avaliadores e dependências compartilhadas. Só metadados/contratos explicitamente permitidos. Sem apostas,movimentação financeira,depósito,login/cadastro de apostas,pagamento,contorno de limites ou compra de dados. Atualize registros e guias atuais por novo checkpoint; não reescreva resultados congelados. Distinga sempre prontidão técnica,admissibilidade e evidência econômica.
''')

for filename in ['CHECKPOINT_INICIAL.md','PROTOCOLO.md']:
    write(filename, (ROOT / filename).read_text(encoding='utf-8'))
activation = json.loads((ROOT / 'activation-receipt.json').read_text(encoding='utf-8-sig'))
write('evidence/activation.json', json.dumps(activation, ensure_ascii=False, indent=2))
print(json.dumps({'claims':len(claims),'problems':len(problems),'destination':str(DEST)},ensure_ascii=False))
