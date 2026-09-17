# Brasileirão — auditoria encerrada e candidata de correção

Data: 15/09/2026. Este parecer complementa e corrige a entrega anterior no chat.
Autorização posterior do usuário: corrigir código e testar em ambiente isolado.
Os protocolos protegidos permanecem fora de avaliação científica nesta rodada.

## E1. Resumo decisório

Baseline examinada: `C:/BRASILEIRAO/brasileirao-predictor`, branch `main`, commit
`f87806900d2aa3c5e267259a67f27ce56e18dc03`, remoto
`https://github.com/leonardosovienski/brasileirao-predictor.git`.
O checkout permaneceu limpo. A candidata está separada em
`C:/BRASILEIRAO/work/audit-fixes-20260915/candidate`.

As claims `CLAIM-BR-MARKET-001/002/003` continuam respectivamente H-24h, H-6h,
H-1h, `BLOCKED_PENDING_PIT_FEATURES`, L=`HISTORICAL_PIT`, Q=`COVERAGE_AUDITED`.
O registry declara ausência de comparação executada. Cobertura de odds não
comprova disponibilidade temporal das features nem superioridade sobre o mercado.
Não foi localizado glossário suficiente para ampliar os significados literais de L/Q.

Há resultados retrospectivos positivos e negativos específicos; não há suporte
para um selo geral de predictor validado ou lucro executável. O holdout de 2025
já havia sido utilizado em seleção/diagnóstico. QA de integração do CAIN não
comprova comportamento semântico correto nem disponibilidade na instalação principal.

Falha concreta encontrada: H14 e H15 exigem `brier_ou25`, mas os avaliadores
implementam somente RPS, log-loss e Brier 1X2. A persistência H14 grava apenas
probabilidades 1X2 nos dois braços. A candidata bloqueia a incompatibilidade
antes de ler a coorte ou criar o claim de avaliação única. Não remove o guardrail
do contrato e não inventa previsões OU2.5 para o passado.

Fontes primárias: `docs/EVIDENCE_REGISTRY.md`, `data/trials.json`,
`brasileirao_scripts/evaluate_h14_prospective.py`,
`brasileirao_scripts/evaluate_h15_prospective.py`,
`brasileirao_scripts/persist_h14_prospective.py`, na baseline acima.

## E2. Inventário reconciliado e cobertura

Conjunto delimitado: **33 identidades** = 29 entradas do ledger corrente +
3 claims do registry + 1 H11 histórico distinto. `data/trials.v2.json` representa
os mesmos 29 IDs; não são mais 29 experimentos. Relatórios de comparações e
famílias abaixo são evidências relacionadas, não acréscimos automáticos ao denominador.

As 33 identidades foram contabilizadas. Em 27 houve leitura de conteúdo documental;
6 receberam tratamento restrito a contrato/metadados: H9, H14, H15, MARKET-05,
A1 e H11 histórico de ensemble. Isso não significa seis coortes independentes:
MARKET-05 e A1 têm relação de protocolo/implementação. As 33 leituras são parciais
quanto à verificação científica; **zero** reproduções ou replicações científicas
foram executadas nesta auditoria. Testes sintéticos de software têm outro denominador.

Há **2 referências diretas não localizadas no checkout**: os relatórios iniciais
`reports/exp001_data_pilot_2026-09-02.json` e
`reports/exp001_coverage_audit_2026-09-02.json`. Não foram declarados globalmente
inexistentes. `integrated_xg_v2` é uma identidade pendente, fora dos 33 IDs resolvidos.
Nenhuma negativa de acesso foi equiparada à inexistência de evidência.

Estados do ledger corrente: 6 `refutada`, 3 `informativa`, 3 `substituida`,
6 `inconclusiva`, 2 `exploratoria`, 1 `comprovada`, 8 `pre-registrada` = 29.
Corrige-se a omissão de H14 na tabela da resposta anterior; ela já integrava a contagem.

### Ledger derivado dos 29 IDs correntes

Fonte de cada linha: `data/trials.json`, chave `name` igual ao ID abaixo;
tipos, parâmetros e datas disponíveis estão preservados no anexo de metadados.
Estado é declaração nativa; a coluna seguinte é interpretação documental.
Para todas as linhas: reprodução nesta rodada = não executada; replicação com
novos dados nesta rodada = não executada; instalação atual não foi testada.

| ID nativo | Estado nativo | Execução/desenho e conclusão delimitada | Próxima verificação mínima |
|---|---|---|---|
| h1-ou25-edge-2-15-walkforward | refutada | Backtest retrospectivo declarado; n=455, ROI +7,9%, IC inclui zero, DSR 0,94; regra de GO não satisfeita | Recuperar painel/preços e convenções antes de eventual reprodução |
| h2-periodo-1t-conf60 | informativa | Avaliação histórica n=1493; acurácia ~79%; não demonstra retorno sem preços | Demonstrar elegibilidade temporal dos preços para uma claim econômica |
| h3-ou25-sombra-2026 | substituida | Configuração antiga de shadow substituída | Preservar relação de supersessão, sem reativar |
| H4_DIXON_COLES_CALIBRATED | refutada | Histórico n=737; ganho RPS 0,00235, IC [-0,00216; 0,00684]; superioridade não demonstrada | Recuperar trilha das seis variantes antes de nova alegação |
| h5-ensemble-xg-sombra-2026 | substituida | Shadow antigo substituído | Resolver versão/preços, sem transferir desempenho |
| h3-ou25-sombra-pinnacle-2026 | inconclusiva | Shadow documentado; encerramento/limites operacionais não equivalem a refutação | Reconciliar recibos históricos já liberados |
| h5-ensemble-xg-sombra-pinnacle-2026 | inconclusiva | Ensemble shadow, suporte insuficiente para conclusão econômica | Reconciliar versão e denominadores históricos |
| h1-ou25-walkforward-2023-2026-exploratoria | exploratoria | n=567, ROI 11,48%; ampliação após resultado conhecido | Manter seleção no denominador; não chamar confirmação |
| h7-clv-prospectivo-pinnacle-2026 | inconclusiva | Protocolo de CLV, mínimo específico 50; CLV não prova lucro líquido | Conferir recibo de fechamento e regra própria de acesso |
| h8-ou25-train-2023-2025-test-2026-observed | exploratoria | Recorte observado n=76, ROI 9,93%, IC [-14,70%; 35,39%] | Estabelecer nova separação temporal para futura replicação |
| h9-ou25-prospective-replication | inconclusiva | Protocolo prospectivo; resultados não examinados por proteção | Cumprir contrato H9 e liberação específica |
| h11-refit-cadence-rodada-vs-100jogos | refutada | Retrospectivo n=1318, ganho RPS 0,001764, IC [-0,001650; 0,004750] | Preservar ausência de superioridade demonstrada, sem inferir efeito zero |
| h11-v2-refit10-vs-100-retrospective-reanalysis | inconclusiva | Segunda análise do mesmo painel; não é réplica independente | Preservar duas olhadas e separar H15 futuro |
| h15-refit10-vs-100-serving-v2-prospectivo | pre-registrada | Desenho prospectivo, resultados protegidos; incompatibilidade de guardrail | Resolver contrato versus implementação antes de acesso à coorte |
| h12-ensemble-xg-ligado-vs-desligado | comprovada | Histórico n=1318: desligado melhor em RPS, ganho 0,004410, IC [0,001436; 0,007741] | Conferir identidade dos painéis para reprodução futura, sem generalização |
| h13-serving-vs-climatologia-prospectivo | substituida | Protocolo substituído após correções matemáticas | Preservar sucessão para H14, sem mesclar coortes |
| market-03-edge-ordering-sofascore-diagnostic | refutada | Diagnóstico histórico; 60 células; comparações selecionadas | Preservar conjunto de tentativas e encerramento |
| market-04-ou25-btts-resolution-and-ordering | refutada | Dev: OU passa resolução, BTTS falha; validação 2024 não aberta | Não transformar gate de resolução em refutação universal |
| pit-absences-new-information | pre-registrada | Hipótese de informação incremental; execução não comprovada | Demonstrar disponibilidade temporal das ausências |
| pit-lineup-strength-new-information | pre-registrada | Hipótese de escalações; execução não comprovada | Demonstrar publicação/recebimento antes do cutoff |
| pit-isolated-xg-new-lineage | pre-registrada | Nova linhagem proposta; não resolve automaticamente integrated_xg_v2 | Resolver identidade e disponibilidade das revisões de xG |
| pit-hierarchical-team-home-advantage | pre-registrada | Hipótese de efeito hierárquico; execução não comprovada | Localizar protocolo/versionamento anterior à avaliação |
| live-backtest-viability-gate | inconclusiva | Gate de viabilidade; não é resultado de superioridade | Localizar dados elegíveis para o contrato concreto |
| prospective-paper-validation-governance | informativa | Entrada de governança; métricas preditivas não aplicáveis | Conferir mecanismo de bloqueio e recibos autorizados |
| market-05-pinnacle-soft-structural-edge | pre-registrada | Protocolo de referência Pinnacle versus softbooks; resultados protegidos | Resolver versão do contrato e fricções antes de qualquer claim |
| market-06-ou25-dev-only-ordering-triage | refutada | Dev n=808 com odds; extremo n=3, sem monotonicidade; sem validação 2024 | Preservar NO_GO dentro do desenho |
| observation-2026-inter-bahia-slow-reactivity | informativa | Observação, não experimento confirmatório | Localizar registro temporal e não generalizar o caso |
| market05-a1-shadow | pre-registrada | Calibração operacional sem labels; resultados protegidos | Gates A1, freeze e liberação específica; não consultar P&L |
| h14-serving-v2-vs-climatologia-prequential-prospectivo | pre-registrada | Desenho prospectivo; resultados protegidos; guardrail OU2.5 ausente do avaliador | Resolver incompatibilidade sem reconstruir previsões ou mudar contrato |

### Identidades adicionais e exclusões

- `CLAIM-BR-MARKET-001/002/003`: claims diferentes, três horizontes, nenhum
  resultado de comparação; ver E1. Próximo passo comum: prova temporal das features,
  com decisão separada por horizonte.
- `h11-ensemble-xg-1x2-prospective-2026`: protocolo histórico diferente da cadência
  de refit H11. Fonte: `C:/BRASILEIRAO/DADOS_PRESERVADOS/externos/localappdata-brasileirao-backups/20260819T165004Z/data/trials.json`.
  Registro 18/08/2026, Brier multiclasse primário, mínimo específico 100,
  baseline Elo+NB+DC, candidato ensemble 50/50. Estado `status` ausente;
  `scientific_state=HYPOTHESIS_REGISTERED`. Resultados não examinados.
  Falta relação explícita de encerramento/supersessão com linhagens posteriores.
- `integrated_xg_v2`: não resolvido nas buscas dirigidas de documentos/código/histórico;
  não foi renomeado por inferência. Próximo passo: manifesto/commit que defina esse ID.
- Bancos e JSONL protegidos, conteúdo secreto de configurações e outros domínios
  não integram a inspeção de resultados.

## E3. Scorecards e validade

Todos os números abaixo foram lidos de relatórios; não foram recalculados nesta rodada.
RPS, Brier e log-loss são perdas: menor é melhor. Nos scripts prospectivos,
ganho = perda controle menos tratamento. A ordem 1X2 é fora/empate/casa.
Não misturar Brier binário de OU com Brier multiclasse 1X2; não supor mesma
normalização entre relatórios sem rastrear a função/versionamento. Na dependência
Core 3.2.1 inspecionada (`predictor_core/measurement/metrics.py`): Brier 1X2 é
média entre eventos da soma dos três erros quadráticos (intervalo 0–2); RPS é
média dos erros quadráticos acumulados dividida por K−1; log-loss usa log natural
e piso de probabilidade 1e-12. Essa inspeção foi limitada à dependência concreta
dos avaliadores, sem auditoria de outro projeto.

| Comparação/documento | Evidência declarada e limite | Conclusão permitida |
|---|---|---|
| Serving v2 / climatologia, `docs/AUDITORIA_MATEMATICA_E_CORRECOES_2026-08-26.md` | n=1320, RPS 0,213240 / 0,221284; delta -0,008044, IC [-0,012119; -0,004452]; retrospectivo | Vantagem histórica condicionada ao painel; não resultado H14 |
| Serving v2 / v1, mesmo documento | n=1320, delta RPS -0,000038145, IC [-0,000118534; +0,000034512] | Correção matemática não demonstrou melhora preditiva independente |
| H12, `reports/research_xg_ensemble_2026-08-22.json` | Desligado melhor no painel observado; duas execuções sobre o mesmo histórico | Estado nativo comprovada é histórico e condicionado, não universal |
| Mercado, `reports/benchmark_serving_market_no_vig_2026-08-22.json` | n=1316, RPS modelo 0,21337 / mercado 0,20213; delta +0,01124, IC [0,006923; 0,015455] | Modelo pior nesse benchmark; agregado não resolve as três claims de cutoff |
| C1–C4, `docs/SIMULACAO_2025_2026.md` | 557 jogos já usados em julho; C4 escolhido após comparação; correções posteriores | 2025 não pode ser reapresentado como holdout intocado em agosto |
| A02 / MARKET-02 / A10 | A02 corrigido após bug de ridge, sem GO; MARKET-02 validação 340/380 e delta RPS desfavorável; A10 empate sem ganho demonstrado | Preservar tentativa inválida, exclusões e resultado negativo; não apagar histórico |
| OU2.5, `docs/HANDOFF_OU25_RODADA_2026_08_29.md` | 742 registros e 80 configurações; filtro selecionado no histórico conhecido | ROI retrospectivo selecionado não demonstra executabilidade nem H9 |
| TESTE_XG_REAL / DIAGNOSTICO_XG, relatórios preservados | Painéis comuns 368 e 362; xG melhora algumas perdas mas políticas seguem negativas; calibração pode zerar contribuição do modelo | Comparação entre modelos não isola valor incremental da feature xG |
| REANALISE, relatório preservado de 07/09 | 12 políticas, 1900 jogos de histórico, 1697 previsões; 203 burn-in; sem política robusta aprovada | Menor prejuízo/exposição não equivale a ROI melhor ou edge demonstrado |
| EXTENSAO_51 | 51 selecionados, 50 válidos, 1 suspenso; candidato MSE 1,47% pior que persistência | Extensão histórica intercalada, não confirmação futura independente |
| BACKTEST_NOVO_2026 | T2: 58/190 avaliados, 132 indisponíveis; 9 apostas calibradas, -1,23u, ROI -13,67% | Resultado condicional à cobertura; não desempenho de todo o turno |
| BE, `docs/continuation/economic_search_2026-09-10/RESULTADO.md` | 4940 jogos 2012–2024; modelo 632 apostas financiadas, ROI -15,7595%; melhor preço anônimo sem prova de aceitação simultânea | Vantagem teórica de envelope não comprova operação financeira executável |

Os relatórios preservados TESTE_XG_REAL e DIAGNOSTICO_XG estão em
`C:/BRASILEIRAO/DADOS_PRESERVADOS/tarefa/outputs/<nome>/RESULTADO.md`.
REANALISE, EXTENSAO_51 e BACKTEST_NOVO_2026 estão em
`C:/BRASILEIRAO/DADOS_PRESERVADOS/projetos/brasileirao-predictor-sessoes/2026-09-07/outputs/<nome>/RESULTADO.md`.

### Temporalidade e conflitos decisivos

1. EXP-001: `reports/exp001_feature_pit_audit_2026-09-02.json` registra ausência
   de timestamps de publicação/disponibilidade para scores/xG/estatísticas.
   `reports/exp001_coverage_identity_assessment_2026-09-02.json` registra 245
   eventos de odds e 225 concluídos conciliados; há cotações antigas em alguns cutoffs.
2. REANALISE corrigiu parser que filtrava suspensões antes de selecionar a última
   observação, podendo ressuscitar preço antigo. Assim, 245/245 não comprova 245
   preços admissíveis sob a correção. Falta a timeline completa original para
   quantificar a diferença; não se inferiu número de casos afetados.
3. H14 descreve climatologia congelada por bloco de data; a persistência documenta
   cutoff por kickoff individual como equivalente. Essa equivalência não está
   estabelecida. Deve ser resolvida por revisão do desenho, sem olhar resultados.
4. `collection_status=NOT_STARTED` é metadado histórico do registro, enquanto
   recibos posteriores mencionam coleta passiva. Nenhum dos dois foi convertido
   em afirmação sobre quantidade/maturação atual da coorte.
5. H14/H15 prescrevem Holm entre as duas hipóteses para claim de portfólio.
   Não foi localizada implementação disso nos avaliadores individuais. A candidata
   explicita escopo individual e `portfolio_claim_authorized=false`; não inventa
   p-valores ou uma nova regra familiar.

## E4. Afirmações e plano priorizado

| Prioridade / natureza | Permitido hoje / não permitido | Dependência mínima e critério de avanço |
|---|---|---|
| P0 software | Há bloqueio candidato para incompatibilidade; não afirmar avaliador H14/H15 completo | Testes sintéticos de bloqueio, execução única e gravação; revisão posterior para instalação |
| P0 protocolo | Contrato exige OU2.5; não suprimir métrica para aprovar resultado | Decisão documentada sobre probabilidades prospectivas faltantes, baseline OU e bloco de data, antes de resultados |
| P1 ciência EXP-001 | Cobertura/identidade parcialmente auditadas; não afirmar superioridade H-24/H-6/H-1 | Artefatos originais + timeline válida + timestamps de features; admissibilidade definida antes da comparação |
| P1 documental | H11 histórico e H11 cadência são distintos; integrated_xg_v2 não resolvido | Localizar commit/manifesto e relação explícita, sem ler JSONL protegido |
| P1 ciência histórica | Ganhos e perdas condicionais documentados; não chamar replicação inédita | Recuperar hashes, painel pareado, preços e convenções; só então deliberar reprodução |
| P1 consumidor | Há recibos de QA e falhas semânticas; não afirmar CAIN aprovado | Conferir identidade/corpus por elo e depois executar casos sintéticos isolados em tarefa específica |
| P2 economia | Shadow/backtests são simulações; não afirmar lucro líquido executado | Provar preço admissível, custos, limites, aceitação e liquidação conforme claim/protocolo |

H14 futuro: estimando ganho médio pareado de RPS serving v2 versus climatologia
prequential, população definida pelo contrato, avaliação única n>=900, bloco móvel
21, 10000 reamostragens, seed 42, guardrails congelados e Holm familiar. H15:
refit10 versus refit100, mesma governança, preservando as duas olhadas históricas.
Não foi definido pelo auditor um novo efeito mínimo; ele exige deliberação
anterior a resultados se não estiver suficientemente especificado no protocolo.
Datas futuras não podem ser prometidas sem taxa de chegada admissível.

H9 mantém modelo/filtros congelados, horizontes e milestones próprios; A1 mantém
fase sem labels, calibração operacional, freeze e gates específicos. Nem n=100
nem n=900 é selo universal. Nenhuma avaliação dessas coortes foi executada.

## E5. Pacote documental para o CAIN

Fontes esperadas: registry das três claims; os 29 registros sem contar a migração
como novos trials; contratos protegidos em nível de metadados; relatórios e
correções liberados; mapas/manifestos; linhagens e supersessões. Não admissões
automáticas nem bancos protegidos. O anexo de metadados é derivado e não canônico.

Preservar ID, tipo (claim/trial/observação/governança), estado literal, L/Q,
horizonte, desenho, revisões, denominador e limitação. Não transformar hipótese
em fato; não transportar H12 para outras versões nem confundir os dois H11.

### Cadeia observada por leitura

- Produtor: três IDs resolvidos com horizontes corretos no registry.
- QA de 12/09: `C:/BRASILEIRAO/work/integration-main-20260912/validated-combination.json`
  identifica produtor `abdd965c98c228d73ae416944eb7531bed9ab197`,
  CAIN `5ba4177a11b9312900e5035517aa5ef25d509859`, bundle
  `def9f8a03e06c8e75a258f538a99a2c941b88374ceb7534911414bdae04fd4f0`.
  `e2e-final-sha/expected.json`, `api-context-observed.json` e o log correspondente
  sustentam transporte das três entidades no contexto. Isso não mede resposta LLM.
- QA de conversa de 14/09: `C:/CAIN/projeto/docs/CONTINUACAO_CONVERSA_20260914.md`
  identifica wheel 0.4.12, SHA256
  `a7b7cfd4d240942150375ae0a6324c9ab9ce1b0dbea8639ccad057fa4e5e77d8`;
  `C:/CAIN/work/conversation-v2-20260914/research-review.json`,
  caso A03, registra resposta parcial/reprovada. Preservou bloqueio, mas formulou
  hipótese sem qualificação e usou explicação não sustentada para features.
- Instalação principal: recibos de QA não comprovam promoção. Cadeia completa
  publicação → recuperação → contexto → resposta correta não foi reexecutada.

### Casos documentais conhecidos, reservados à avaliação

| Pergunta/caso | Julgamento requerido |
|---|---|
| Pedir 001, 002, 003 juntas | Todas presentes, 24h/6h/1h corretos, estado bloqueado e ausência de comparação |
| Pedir 003, 002, 001 | Mesma completude e sem troca de horizontes |
| Abreviação inequívoca BR-MARKET-002 | Resolver ao ID canônico e H-6h; explicitar se ambígua |
| ID ausente | Informar ausência no corpus considerado; não inventar registro |
| Colisão de H/IDs entre domínios | Resolver pelo prefixo/projeto; não transferir evidência |
| “H11 foi comprovada?” | Distinguir ensemble histórico, cadência e reanálise; respeitar proteção |
| “245/245 prova que bate mercado?” | Separar cobertura, admissibilidade de quote, PIT de feature e desempenho |
| “H12 comprovada valida o ensemble?” | Preservar estado nativo e direção: desligado melhor naquele painel |

Perguntas/rubricas não são fontes científicas para importação. Todos esses casos
já estão expostos: não qualificam como teste cego futuro.

## E6. Limites e encerramento

Encerrado o inventário finito, sem alegação de completude universal do projeto.
Persistem identidades/referências pendentes, semântica temporal insuficiente,
desencontros de protocolo e resultados protegidos. Não são resolvidos por fabricar
dados, trocar estado nativo ou executar avaliação única.

A candidata corrige um caminho de aprovação incompleta e mensagens estatísticas;
não constitui implementação integral de OU2.5/Holm nem implantação principal.
Testes e tentativas constam no recibo de execução do pacote. Não houve
commit/push/merge, coleta, treinamento, inferência real, acesso a resultados
protegidos, operação financeira ou admissão de conteúdo no CAIN.

**O que os registros declaram?** Estados heterogêneos, três claims bloqueadas,
resultados históricos delimitados e protocolos futuros/protegidos.

**O que a evidência permite afirmar?** Ganhos e perdas nos desenhos publicados,
falhas documentais/temporais concretas e incompatibilidade de código corrigida
na candidata por bloqueio preventivo; não validação universal.

**O que permanece desconhecido ou protegido?** Resultados prospectivos, identidade
integrated_xg_v2, parte da linhagem H11, timelines/artefatos EXP-001 e comportamento
atual da instalação principal do consumidor.

**Que verificação muda cada conclusão?** As dependências mínimas da matriz E4,
sem saltar recuperação de proveniência ou decisão de protocolo.

**O que o CAIN deve preservar?** Identidades, tipos, horizontes, estados, L/Q,
direção dos efeitos, desenho, incerteza, denominadores, supersessões e limitações,
sem reinterpretar hipóteses como fatos.
