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
