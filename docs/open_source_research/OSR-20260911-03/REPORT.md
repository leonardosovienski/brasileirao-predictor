# Brasileirão Predictor — encerramento da iniciativa offline

**Agora há um caminho executável de pesquisa para admitir mercados 1X2, produzir diagnósticos probabilísticos, explicar recusas e comparar execuções com proveniência.** O suporte adaptativo NB/DC também ficou 2.31 vezes mais rápido no microbenchmark delimitado, com a mesma distribuição e erros controlados no domínio aprovado. Nada foi ativado no runtime.

| Capacidade | Referência | Antes | Implementado | Evidência / uso | Limite |
|---|---|---|---|---|---|
| Mercado conjunto até diagnóstico probabilístico | R001,R010,R011,R014,R048 | A rodada 02 admitia uma seleção por chamada. odds_shop já verifica mercados completos para exibição, mas não implementa este cutoff histórico com recibo e encadeamento até scoring. | Um consumidor admite o snapshot completo, valida odds, retira margem, ordena 1/X/2, conserva recusas e mede scoring apenas em fixtures sintéticas admitidas. | T1 — research/use.py; evidence/market-tests.json | Dados sintéticos de desenvolvimento; clocks declarados não autenticados. Snapshot comum exige contrato de provedor. Sem dados reais, ranking econômico ou N05. |
| Comparação rastreável de execuções offline | R049,R004,R059 | Writer nativo já guardava hashes e falhas. Faltava, no fluxo da rodada 02, um consumidor para comparar o mesmo universo e explicar mudanças de admissão/probabilidade. | Um comando cria duas execuções imutáveis, compara política/universo/hashes e gera relatório por partida; corrupção, sobrescrita e painéis incompatíveis são recusados. | T2 — research/use.py; evidence/receipt-tests.json | Comparador restrito a este schema de diagnóstico, não catálogo universal de estudos. Mudança observada não atribui causalidade; hashes não autenticam fonte. |
| Cauda NB/DC com menor custo e condicionamento explícito | R001,R002 | O candidato 02 recalculava fatores e PMFs de baixo placar em cada probe; alpha restrito a [0.01,2]. | Parâmetros invariantes calculados uma vez, alpha estendido a [1e-4,3], falha de suporte explícita e consumidor com diagnóstico DNB. | T3 — research/use.py; evidence/goals-tests.json | As médias dos chamadores não têm limite superior global. Três casos atingiram limite de suporte. Orçamento operacional de latência UNKNOWN; diagnóstico condicionado não promete 1e-6. |

## A. O que eles fazem e nos falta

Ferramentas maduras organizam dados, filtros, configurações e evidência em um fluxo reutilizável. O projeto já tinha writers, contratos temporais, modelos e preços; a rodada 02 ainda deixava a composição entre eles a cargo de chamadas separadas. Completamos esse caminho estreito. Cache de fonte não substitui história versionada. Mercado completo para exibição não equivale à admissão histórica no cutoff.

Scouting com vídeo, eventos/tracking, outras distribuições e automação de experimentos são capacidades externas pertinentes a tarefas específicas; não são faltas obrigatórias deste predictor. Dados de contexto/xG temporalmente admissíveis continuam um gap material; descanso/viagem/técnico já existem e não foram duplicados. [Matriz de cobertura](CAPABILITY_MATRIX.md) e [comparação externa](SURVEY.md).

## B. O que aproveitamos do ecossistema

Antes, o pesquisador precisava compor a admissão de seleções, odds/scoring e relatórios da rodada 02. Agora `use.py` realiza a composição e publica recibos/diagnóstico. A demonstração é [este relatório gerado pelo consumidor](evidence/use-20260911T063408091434Z/COMPARACAO.md). A melhoria é rastreabilidade e contrato conjunto, não ganho preditivo.

Antes, o writer nativo guardava artefatos mas esse fluxo não tinha comparação por fixture. Agora aponta mudanças de entrada, status e probabilidade, e recusa comparação com outro universo/política. A ideia de organizar runs/artefatos foi aproveitada de MLflow por extensão nativa, sem dependência nova. Antes, cada probe NB/DC repetia trabalho invariante; agora esse trabalho ocorre uma vez. O benefício de custo foi medido contra 02, não contra toda produção.

[Como executar e testes](EXPERIMENTS.md). Código utilizável em pesquisa sintética, não importado pelo runtime. Não há novo modelo treinado ou nova fonte ingerida.

## C. O que não devemos copiar

Não instalar outro servidor de tracking só para comparar estes arquivos; não copiar cache mutável como evidência PIT, scraping com contorno, parâmetros estrangeiros, heurísticas de tipster ou complexidade estatística sem dados. Não transformar fechamento em T−60. Não usar a tolerância da grade como tolerância de todo mercado condicionado: neste teste, o erro condicionado chegou a 4.44e-05. Rejeições são específicas ao uso/implementação, não refutação universal do método.

## D. O que devemos preservar

Preservar NB/DC/Elo, convenções de pagamentos/caixa anteriormente verificadas e contratos de curadoria/versionamento. O writer nativo foi reutilizado e seus caminhos de falha exercitados. odds_shop já possuía controle de completude para sua finalidade; não declaramos essa capacidade ausente. Preservar versões históricas e protocolos protegidos. **NO_VERIFIED_ADVANTAGE** para superioridade preditiva ou econômica geral.

## E. Combinações úteis e pendências reais

Foi executada a cadeia snapshot → admissão conjunta → odds → margem → vetor 1/X/2 → scoring/recusas → recibo → comparação. Foi executada a cadeia parâmetros NB/DC → suporte → massa/mercados → diagnóstico de condicionamento/falha. Cada cadeia tem consumidor explícito, casos válidos e limites.

N05-A não está elegível: falta manifesto real, decisão de sobreposição com BE e evidência temporal por produto/campo. **Recebimento pessoal não é requisito universal de avaliação preditiva; é parte do contrato específico preparado em 02.** Uma emenda para informação disponível na fonte foi preparada separadamente, sem autoaprovação. Aceite pessoal de apostas não bloqueia A. R051 é histórico plausível condicionado; os produtos de fechamento/janela curta examinados não habilitam o backfill requerido. [Gates exatos, fontes, emenda e backlog finito](DECISIONS.md).

## Decisão de encerramento

| Dimensão | Estado |
|---|---|
| ENGINEERING_STATUS | INTEGRATED_RESEARCH_ONLY_SCOPED |
| DATA_ADMISSIBILITY | SYNTHETIC_INPUTS_ONLY; REAL_N05_NOT_ADMITTED |
| PREDICTIVE_EVIDENCE | NOT_EVALUATED_THIS_RUN |
| ECONOMIC_EVIDENCE | NOT_EVALUATED_THIS_RUN |

Encerramos os três alvos offline elegíveis com implementação, demonstração e testes. K06/K07/K09/K11 ficam adiados por dados/justificativa incremental; K05 preservado no domínio anterior; N05 bloqueado, sem nova fase automática. A cobertura externa acumulada é suficiente para esta carteira, não uma auditoria universal de todo ecossistema. Nenhuma alegação de lucro ou previsão melhor.

SHA e rodadas anteriores preservados; [baseline](BASELINE.md), [registro único](registry.json), [validação da entrega](evidence/delivery_validation.json). Não executados: fitting, estudos protegidos, dados reais, integração operacional, CI global, apostas, serviços e automações.

Para reconsiderar N05, a única intervenção solicitada é o pacote delimitado em DECISIONS: Leonardo encaminha manifesto sem desfechos, provas de clocks/versionamento do fornecedor e decisão BE/N05 sobre a emenda e permissões. Não basta pedir genericamente “mais dados” ou trocar o identificador do estudo.
