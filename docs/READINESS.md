# Readiness audit

Status: `READY_WITH_EXTERNAL_BLOCKER`.

## Gates homologados

- Python 3.13: 413 testes aprovados (1 deselecionado), zero falhas; mais 1 teste de integração Redis real na execução final (414 no total, verificado em CI).
- .NET 10: build Release com warnings como erro, 0 warnings; 30 testes aprovados, zero falhas e zero skips.
- Ruff: `ruff check src scripts tests` e `ruff format --check src scripts tests` verdes, sem ignores amplos.
- Pyright: runtime homologado e fronteiras públicas verdes; pesquisa permanece explicitamente fora do escopo tipado.
- Goldens: 85 testes de Dixon–Coles, Elo, xG, pricing/stakes e matemática preservados.
- Compose: três imagens construídas com wheelhouse temporário validado por SHA-256; Redis, kernel e Worker saudáveis.
- E2E: smoke versionado 3/3, Python → Redis → C# observado, TTL e correlação validados.
- Resiliência: idempotência, replay, timeout/widening, reconexão após perda do Redis e graceful shutdown validados.
- Bancos: Sports DB e Market DB usam paths absolutos distintos; Worker e kernel recebem volumes read-only.

## Cobertura branch-aware

O relatório completo, sem exclusões silenciosas, está em `docs/COVERAGE.md`.

- runtime homologado Python: 81,25%;
- kernel e integração Redis: 81,49%;
- providers homologados: 83,47%;
- Worker .NET: 85,15% linhas e 80,92% branches.

Pesquisa, migração e legado continuam reportados na cobertura global, mas não são promovidos ao runtime homologado.
Nenhum script ou dado legado foi removido.

## Contrato e dependências compartilhadas

O protocolo `brasileirao.redis/1` é validado em Python e C#, incluindo versão desconhecida, identificador ausente,
payload inválido, correlação e serialização. `predictor_core 2.3.0` e `predictor_ops 3.1.0` são carregados de
`site-packages`; os hashes canônicos permanecem em `constraints/shared-wheels.sha256`. O teste operacional de
`predictor_ops` verifica que os pipes próprios de `Popen` são fechados.

## Bloqueadores externos (resolvidos)

1. publicação estável das wheels canônicas em URLs acessíveis ao CI/BuildKit — resolvido: `v2.3.0`/`v3.1.0` publicadas como GitHub Release assets, consumidas com sucesso pela CI atual;
2. geração e versionamento de lockfile portátil a partir desse registry estável — resolvido: `uv.lock` versiona URL + hash sha256 de ambas as wheels.

Os dois artefatos externos que bloqueavam a classificação `READY` já existem; a ressalva `WITH_EXTERNAL_BLOCKER` no topo deste documento refere-se ao estado histórico anterior a essa publicação, não ao estado corrente.

## Governança de pesquisa (GOV-P0, Roadmap Técnico Consolidado v1.0-final)

`scripts/benchmark_predictor.py` é o painel canônico único de medição
preditiva walk-forward (RPS primário; Brier 1X2/OU2.5, log-loss, ECE,
calibration slope, resolution e sharpness como guardrails; accuracy/coverage
como diagnóstico — nunca métrica de promoção). Skill score implementado hoje
só contra `climatology`; `elo_baseline`, `current_v3` e `market_no_vig`
exigem rodar outros previsores sobre a mesma base e ainda não estão
plugados — chamá-los falha alto (`choices=["climatology"]` no CLI), não
silencia. `scripts/run_h4_sweep.py` teve a lacuna de `pipeline_fingerprint`
corrigida (mesma classe de bug já corrigida em `h10_fadiga_walkforward.py`).

**Atualização 2026-08-20 — checklist GOV-P0/OPS-P0 fechado no operador:**

1. `data/trials.harness_attestation.json` renovado (`controle positivo OK`,
   `passed_at=2026-08-20T00:42:38Z`) — rodado via script isolado
   (`scripts/_attest_only.py`, descartado depois de usado) contra o
   `matches.db` real do operador, sem tocar em `data/trials.json`.
2. `scripts/install_windows_scheduler.ps1` rodado — as 7 tasks
   (`brasileirao-market-research`, `-prospective-readiness`, `-h9-emit`,
   `-h9-closing`, `-h9-settle`, `-h9-backup`, `-h9-missed-window`) estão
   `Ready` no Agendador de Tarefas do operador.
3. `config.yaml` ganhou `season_id` de 2021-2023 (treino/burn-in exigido
   pelo Roadmap §3) — coleta real dessas temporadas é ação separada do
   operador (`python -m src.ingest_sofascore`).

**Ainda pendente**: congelamento de `reports/benchmark_baseline_v3_<date>.json`
— `scripts/benchmark_predictor.py` já foi validado contra dados reais (2026,
225 jogos previstos em walk-forward; turno 1 e turno 2 estatisticamente
equivalentes, sem edge significativo ainda sobre climatologia), mas o
resultado não foi salvo como baseline formal. Um bug real foi achado e
corrigido no processo: `--period` cortava o histórico de treino antes do
walk-forward, matando o burn-in ao pedir um recorte recente do calendário.

Nenhuma trial de `RESEARCH-01..08` ou `MARKET-01..04` foi aberta ainda —
falta só o congelamento do baseline acima pro checklist do Roadmap (§12)
estar 100% ✓.

**Atualização 2026-08-21 — baseline v3 congelado e pré-requisito do RESEARCH-01A:**

O baseline foi congelado em `reports/benchmark_baseline_v3_2026-08-20.json`
(commit `951761b`, n=1923 previsões walk-forward 2021-2026, RPS=0.2125,
accuracy 1X2=48,9% — DIAGNOSTIC_ONLY). Com isso o checklist §12 do Roadmap
fecha, MENOS um item que a própria abertura do RESEARCH-01A revelou.

**Guarda de bloco de kickoff (bug real, corrigido antes do experimento).**
A ABC `PrequentialEvaluator` do core fatia por ÍNDICE: `train_step` recebe
`observations[:i]`, que é estritamente-anterior na ORDEM DA LISTA, não no
RELÓGIO. Duas coisas se somavam nisso:

1. `benchmark_predictor.py` lia `matches.date` (data SEM hora) e ordenava por
   ela, então a ordem dentro de uma rodada ficava ao sabor do SQLite;
2. rodada de futebol tem jogos SIMULTÂNEOS, então o enésimo jogo de um bloco
   treinava com resultados que ainda não tinham apitado.

Isso é leakage, e ele CRESCE conforme o refit fica mais frequente — que é
exatamente a variável manipulada pelo RESEARCH-01A. Uma implementação ingênua
do experimento teria medido leakage em vez de cadência, e o braço TREATMENT
ganharia de graça: **falso GO**.

Correções (Regra 3 — corrigir o mecanismo, não mascarar no filtro):

* `benchmark_predictor.py` passou a ler o kickoff REAL de
  `sofascore_matches.kickoff_at` (dado que já existia na base e estava sendo
  descartado) e a ordenar por ele. Sem hora, cai para meia-noite UTC e a
  rodada inteira vira um bloco — leitura honesta de um dado ausente. O
  relatório carrega `kickoff_coverage` dizendo quantos jogos caíram no
  fallback.
* `src/evaluator.py` ganhou fit PREGUIÇOSO: `train_step` só enfileira o
  histórico; o ajuste acontece no `predict_step`, que conhece o kickoff do
  alvo e trunca o histórico em `kickoff < alvo`. A guarda vale nos DOIS
  braços do experimento e independe da cadência. `block_guard` no relatório
  reporta quanto foi descartado.
* `PredictionPoint.predicted_at` agora é estritamente ANTERIOR ao
  `matures_at` (o contrato do core só exigia `>=`).

**Consequência para o baseline:** `benchmark_baseline_v3_2026-08-20.json` foi
medido ANTES dessa correção, com a ordenação por data-sem-hora. Ele não serve
como régua para o RESEARCH-01A e precisa ser regerado como **v4** na máquina
do operador, com a guarda ativa, antes de qualquer comparação de trial.

**Pré-registro.** `scripts/research_01a_refit_cadence.py` registra a trial
`h11-refit-cadence-rodada-vs-100jogos` com `status="pre-registrada"` ANTES de
rodar os braços (`--pre-register-only` faz só isso), e depois atualiza a
MESMA entrada com o resultado — reexecutar com os mesmos `params` atualiza,
mudar `params` é trial nova, por construção do registro do core. O holdout de
2025 é recusado por padrão (Regra 7); `--period` default termina em
2024-12-31.

**Nota sobre o roadmap:** o texto do RESEARCH-01A descreve o CONTROL como
"refit na virada do mês". O código nunca fez isso — `RETRAIN_EVERY` conta
JOGOS (100), não dias; ~100 jogos ≈ 10 rodadas ≈ um mês por coincidência de
cadência do campeonato. O experimento manipula a variável que existe de fato:
`retrain_every` 100 (CONTROL) vs 10 (TREATMENT, ~1 bloco de rodada).

**Auditoria 2026-08-21 — correções no painel canônico e no H₀:**

Revisão do repositório em `main` (91bb24b) apontou nove itens; sete foram
corrigidos aqui. Os dois restantes são decisão de arquitetura, registrados
abaixo como pendências abertas.

*Corrigidos:*

1. **`src/elo_baseline.py` não tinha guarda de bloco de kickoff** — e sofria a
   forma MÁXIMA do problema, porque reajusta a cada passo (`retrain_every`
   default = 1): toda previsão de um bloco simultâneo treinava com o resultado
   dos jogos vizinhos. Como este é o H₀ contra o qual o Dixon-Coles precisa
   provar valor, o leakage INFLAVA o baseline e faria o modelo parecer pior do
   que é — o espelho exato do risco corrigido em `src/evaluator.py` na PR #25.
   Mesma correção: fit preguiçoso truncado em `kickoff < alvo`.
2. **`data/trials.json` não era validado por nenhum teste**, apesar de o core
   instruir explicitamente ("a suíte do consumidor deve falhar se o trials.json
   real não conformar"). É o denominador do DSR — sem validação ele podia
   derivar do schema em silêncio e o desconto anti-p-hacking parava de valer.
   `tests/test_trials_registry_schema.py` fecha isso.
3. **`delta_ci95` era sempre `null` no bloco `metrics`**, inclusive na métrica
   PRIMÁRIA, embora o IC já estivesse calculado e fosse usado no bloco
   `skill_scores`. O Roadmap §6 exige o campo justamente no exemplo da
   primária. Agora RPS, Brier 1X2 e log-loss carregam IC do delta.
4. **Bootstrap do painel era `iid`**, enquanto `h10_fadiga_walkforward.py` e o
   RESEARCH-01A usam bloco móvel. Jogos vizinhos no tempo têm erro
   correlacionado; iid estreita o IC e SUPERESTIMA significância — inaceitável
   no instrumento que decide promoção de trial. Trocado por bloco móvel
   (`block_length=21`), e o esquema agora aparece no relatório.
5. **`calibration_slope` era OLS não-ponderado sobre 10 médias de bin** — um bin
   com 3 jogos tinha a mesma alavancagem de um com 400. Agora é ponderado por
   `n`, então ruído de cauda não veta trial boa nem mascara degradação no miolo.
6. **`--baseline` era argumento morto** (`args.baseline` não era lido) e a
   docstring prometia um `NotImplementedError` inexistente. Agora o valor chega
   em `run()` e baseline não plugado falha alto de verdade.
7. **`sync_matches_from_sofascore.py` não filtrava por competição**: o SELECT
   varria `sofascore_matches` inteira e carimbava `tournament_name` em tudo.
   Inofensivo hoje (só Série A na config), mas o RESEARCH-05 pede histórico de
   Série B para prior de promovido — no dia que entrasse, seria espelhado como
   Série A. Filtra por `cfg['sofascore']['competitions']`.

Além disso, `benchmark_predictor.py` e o RESEARCH-01A passaram a emitir
progresso a cada 200 previsões: com refit por rodada a execução leva horas, e
silêncio total é indistinguível de travamento.

**IMPACTO NA RÉGUA:** os itens 4 e 5 mudam números já medidos.
`reports/benchmark_baseline_v4_2026-08-21.json` foi gerado com bootstrap iid e
slope não-ponderado; o RPS e os deltas não mudam, mas os **intervalos de
confiança e o `calibration_slope` mudam**. O v4 precisa ser regerado antes de
servir de régua para comparar qualquer trial.

*Pendências abertas (decisão de arquitetura, não corrigidas aqui):*

* ~~**O painel canônico não mede o modelo que serve.**~~ **RESOLVIDO em
  2026-08-21** — ver "Alinhamento painel × serving" abaixo.
* **Jogo adiado deixa linha órfã em `matches`.** A PK é `(date, home_team,
  away_team)` e `sofascore_matches` tem `event_id`; adiamento muda a data, a
  linha nova entra e a antiga fica (o upsert não deleta), virando fixture
  fantasma. Não afeta o benchmark (que filtra `home_score IS NOT NULL`), mas
  afeta listagem de fixtures e o pipeline H9. Resolver exige migração de
  schema (`event_id` em `matches`), fora do escopo desta auditoria.


**Alinhamento painel × serving (2026-08-21):**

`src/serving_evaluator.py` (`ServingStackEvaluator`) reconstrói a pilha de
produção dentro do laço walk-forward, e `scripts/benchmark_predictor.py` ganhou
`--engine {dixon_coles,serving}` para escolher o que medir.

*Por que não bastava ler o cache do cron.* `src/cron_update_models.py` ajusta
Elo, `fit_goal_model` e as forças atk/def-xG com TODOS os jogos disputados da
janela do banco. Em produção isso é honesto — o cron roda "agora", e agora só
existe passado. Num backtest seria vazamento massivo: o mesmo cache serviria
para prever 2021 e 2024, dando ao modelo de 2021 o conhecimento de 2024. Por
isso a pilha é REAJUSTADA a cada refit sobre o histórico truncado, com os dois
cortes do cron (`elo.window_years` e `model.calibration_window_years`)
aplicados RELATIVOS ao último jogo do histórico, não à data de hoje — é isso
que dá paridade train/serve num replay.

*Paridade, não reimplementação.* Todas as etapas chamam as MESMAS funções do
serving (`ratings.compute_ratings`, `model.fit_goal_model`,
`model.predict_match`, `xg_model.fit/predict/blend`). Nada é reescrito: uma
cópia divergiria com o tempo e o painel voltaria a medir outra coisa.
`tests/test_serving_evaluator.py` fixa isso comparando a previsão do avaliador
com a pilha recomposta à mão.

*xG dentro de `result`.* O `_load_observations` passou a carregar
`tournament`, `neutral` e o xG das partidas. O xG vai ANINHADO em `result`
pelo mesmo motivo dos gols: a ABC do core remove só o `target_key` antes do
`predict_step`, então campo de desfecho no nível de cima chegaria à previsão
do próprio jogo. Aninhado, alimenta o ajuste a partir do histórico e fica
invisível na hora de prever.

*Duas diferenças deliberadas em relação ao serving:*

1. **Time estreante não derruba a avaliação.** `src/predict.py` faz
   `sys.exit` em time desconhecido; num replay histórico isso mataria a
   execução inteira por causa de um promovido. Aqui ele entra com
   `elo.initial_rating` — mesmo shrinkage neutro que o `xg_model.predict` já
   aplica a time sem histórico.
2. **Falha de ajuste do xG é CONTADA.** `xg_model.maybe_blend` degrada em
   silêncio para o baseline no serving (correto: serving não pode cair). No
   painel isso mediria o baseline achando que mede o ensemble, então
   `block_guard.xg_fit_failures` reporta quantas vezes aconteceu.

**`dixon_coles` segue sendo o motor DEFAULT** — trocar de repente invalidaria
as medições já feitas contra ele, inclusive a trial `h11` em curso. O
`serving` é opt-in até o operador decidir migrar a régua, e o relatório carrega
`engine` e `serves_production_model` para que nenhuma comparação misture os
dois sem perceber.


**Controle negativo do pipeline (2026-08-21):**

`scripts/permutation_test.py` fecha a metade que faltava da validação do
instrumento. `attest_pipeline_power` já provava o controle POSITIVO — a régua
detecta sinal sintético. Faltava o oposto, sobre dados REAIS: a régua rejeita
ruído quando roda sobre a base, o carregamento e a ordenação DESTE projeto?

O teste embaralha os `result` entre as partidas e roda o mesmo walk-forward.
Cada `result` viaja inteiro (home_goals e away_goals juntos, na ordem
original), então as marginais da liga — e com elas a climatologia — ficam
idênticas; o que se destrói é só a associação time↔desfecho. Sobra exatamente
um sinal: as marginais globais, que é o que a climatologia captura. Logo o
skill score contra climatologia tem que colapsar para zero.

Se o modelo AINDA bater a climatologia com IC95 acima de zero em dados sem
sinal, não existe modelo bom — existe vazamento. O script sai com código 2
nesse caso.

**Por que isso valia o custo:** todos os vazamentos achados na auditoria deste
dia teriam aparecido aqui — guarda de bloco ausente no Dixon-Coles e no Elo,
ordenação por data-sem-hora dentro da rodada, xG do jogo previsto no nível
errado do dict. Nenhum quebrava teste unitário; todos inflavam a métrica em
silêncio.

O holdout de 2025 é recusado por padrão também aqui: um controle negativo
consome a amostra virgem tanto quanto um experimento.

**Pendências que seguem abertas — dependem de decisão ou de informação do
operador, não de implementação:**

1. **Custo do walk-forward.** `fit_dixon_coles_parameters` (src/dixon_coles.py)
   avalia o objetivo num laço Python que constrói uma `DixonColesMatrix`
   inteira POR JOGO e POR AVALIAÇÃO, e o `minimize` roda sem gradiente
   analítico — o scipy faz diferenças finitas sobre ~52 parâmetros, ou seja
   ~53 avaliações por passo do gradiente. É a causa das ~4h30 de uma execução
   com refit por rodada. Vetorizar em numpy ou fornecer o jacobiano daria
   ganho de ordem(ns) de grandeza, MAS qualquer mudança na numérica pode mover
   resultados já congelados — precisa de decisão explícita e de re-congelar as
   réguas depois.
2. **Baseline `market_no_vig`.** O Roadmap §6 pede, e é o teste de teto: se o
   modelo não bate o fechamento sem vig, não há edge econômico. Depende da
   cobertura de odds históricas na base do operador, que não é verificável a
   partir do repositório.
3. **Linha órfã de jogo adiado.** PK de `matches` é
   `(date, home_team, away_team)`; adiamento muda a data, a linha nova entra e
   a antiga fica. Resolver exige migração de schema (`event_id` em `matches`)
   sobre a base viva do operador — não é mudança para fazer às cegas.
