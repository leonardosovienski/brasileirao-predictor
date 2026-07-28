# HANDOFF.md — brasileirao-predictor

> ## CHECKPOINT OPERACIONAL (2026-07-25)
>
> Checkpoint somente-leitura: nenhum dado criado, nenhum backfill, nenhum trial
> novo, nenhum threshold tocado, nenhuma integração externa.
>
> **Git/vendor.** `main` em `fb97521`, worktree limpo; worktree de checkpoint
> `claude/brasileirao-predictor-checkpoint-9b7d61` no mesmo HEAD. Vendor
> `predictor_core 1.3.3-ga-20260723` (`CORE_MANIFEST.json` aggregate
> `0cfd8ecbd3e45538`, sync `2026-07-23T06:27:14Z`); heartbeats declaram
> `core_provenance.status = VENDOR_VERSION_DECLARED`. Tools `1.3.4` (`ab3bd46`).
> `data/trials.json` = `5863CAD3…03998B` — confere no repo principal e no worktree.
>
> **Jobs (Task Scheduler, 3/3 `Ready` e habilitados, último resultado `0`).**
> `brasileirao-archival-collection`: `SUCCEEDED` exit 0, fim `2026-07-25T06:30:03Z`
> (1,56 s), próxima 26/07 03:30 local. `brasileirao-sombra-manha`: `SUCCEEDED`
> exit 0, fim `2026-07-24T14:16:05Z` (422 s), próxima 25/07 10:00 local.
> `brasileirao-sombra-noite`: `SUCCEEDED` exit 0, fim `2026-07-25T02:07:16Z`
> (434 s), próxima 25/07 23:00 local. Locks adquiridos sem reclaim nos três.
>
> **Runtime externo.** O archival grava heartbeat/log/events fora do repositório,
> em `%LOCALAPPDATA%\predictor-tools\runtime\brasileirao-predictor\brasileirao-archival-collection\`;
> as sombras gravam em `data/runtime/operations/` (ignorado pelo git). As cópias
> em `logs/operations/*archival-collection*` estão congeladas em 23/07 com
> `FAILED`: são artefato morto do caminho anterior, não falha viva. O
> `predictor-gate-monitor` vigia apenas as duas sombras — o job archival ainda
> não está na lista de tasks monitoradas.
>
> **Archival COLLECTION_ONLY** (`collection-brasileirao-20260723-core-9d352654`,
> `collection-only/1`): 202 eventos no arquivo, 190 `SNAPSHOT_RECORDED`, **12
> `COMPLETE`/terminais**, todos os demais estados em 0. `events_seen=197` e
> `transitions_written=0` nas três últimas execuções — idempotência confirmada,
> sem regressão de lifecycle. `collection_only_archive.py` só faz `SELECT` em
> `sofascore_matches` e escreve exclusivamente em
> `data/collection_only/brasileirao_events.jsonl`: **nada dessa coleta entra em
> `matches.db`, trials, gates, H3 ou H5**.
>
> **Gate estrito: `MATURED_ELIGIBLE = 0/100` nas DUAS linhas.**
> `scripts/evaluate_shadow_cohort.py` (a autoridade do gate, `min_sample=100`,
> `capital_enabled: false`) classifica **os 8 picks da H3 e os 3 da H5 como
> `LEGACY_INCOMPLETE`** — nenhum tem `pick_id`, `bookmaker`, `predicted_at`,
> `kickoff_at`, `odds_captured_at` nem `provenance_hash` do contrato
> `PICK_REQUIRED`. `PROSPECTIVE_ELIGIBLE = 0`, `closing_coverage = 0.0`,
> `dataset_hash = e3b0c442…` (conjunto vazio) e veredito `INCONCLUSIVE` em ambas.
> A coorte prospectiva ainda **não começou a contar**; os 11 registros nunca
> contarão. O relatório `shadow-report/v2` do monitor conta registro bruto
> (4 maturados na H3) e por isso NÃO deve ser lido como progresso de gate.
>
> **H3** (`h3-ou25-sombra-2026`): 8 picks legados, 4 liquidados, 4 abertos.
> Diagnóstico operacional apenas: ROI bruto +60% (PnL +2,4 u), CLV médio −5,50%
> com IC95 bootstrap (seed 13) [−6,37%; −4,94%], **4/4 CLV negativos**, ROI IC95
> [−47,5%; +125%]. CLV negativo em 100% da amostra é coerente com a
> abertura-fantasma da H1.
>
> **H5** (`h5-ensemble-xg-sombra-2026`): 3 picks legados, 2 liquidados, 1 aberto
> (Grêmio × Fluminense, 26/07, under @1,95). Linha separada da H3, mesmo gate
> congelado de 100 `MATURED_ELIGIBLE`.
>
> **Estabilidade de bookmaker: `BOOKMAKER_RECOMMENDATION_READY`.** Com 7 smokes
> (o 7º na execução das 10:00 de 25/07), o ledger sanitizado recomenda
> **`betsson`**: presença 100%, cobertura O/U 2.5 de 98,35%, lag máximo 71 s
> (limite 900 s), 238 cotações válidas. Alternativas aprovadas: `nordicbet`,
> `onexbet`, `unibet_nl`, `unibet_se`, `gtbets`, `pmu_fr`, `williamhill`,
> `coolbet`. `pinnacle`, `betanysports`, `betonlineag`, `codere_it` e
> `tipico_de` ficam em `BOOKMAKER_INSUFFICIENT_COVERAGE`; `matchbook` é
> `BOOKMAKER_REJECTED` por ser exchange. O pré-requisito de estabilidade da
> escolha da casa única está, portanto, **cumprido** — falta apenas congelar
> `BRASILEIRAO_BOOKMAKER`, decisão do operador.
>
> **Mudou desde o último checkpoint.** (1) Lifecycle archival corrigido
> (`4388cb9`): a transição inválida `EVENT_STARTED -> VALIDATED` sumiu e o job
> saiu de `FAILED` (23/07) para `SUCCEEDED` (24/07 e 25/07); funil
> `EVENT_STARTED 3 → 0`, `COMPLETE 7 → 12`, `SNAPSHOT_RECORDED 192 → 190`.
> (2) Heartbeats saíram do worktree (`e90c33e`, `fb97521`), com artefatos de
> runtime destrackeados. (3) Uma liquidação nova em cada linha, do mesmo jogo
> (Botafogo × Vitória, 23/07, 0-0, under @2,10, +1,10 u, CLV −6,76%): H3 3 → 4,
> H5 1 → 2. (4) 6º smoke de estabilidade de bookmaker (15 casas, 392 cotações,
> `picks_persisted: 0`).
>
> **Bloqueio único: `BRASILEIRAO_BOOKMAKER` ausente** — bloqueio de decisão de
> configuração, não bug nem infra. `scripts/sombra.py --capture` falha fechado e
> `[capture]` fecha com `0 pick(s) novos` em toda execução desde 21/07. Com o
> ledger em `BOOKMAKER_RECOMMENDATION_READY`, o bloqueio deixou de ser "falta
> evidência" e passou a ser "falta congelar a casa": enquanto não for congelada,
> o contador segue em 0/100 e nenhum pick elegível nasce.
>
> **Distância até capital.** Nenhum caminho de execução financeira existe:
> `data/bets.jsonl` e `data/bankroll.jsonl` estão vazios (0 byte), stake é
> `sombra-0u`, custos são `not_applicable_shadow_no_execution` e o avaliador
> devolve `capital_enabled: false` fixo. Ordem obrigatória: congelar bookmaker →
> 100 `MATURED_ELIGIBLE` a partir do zero → critério pré-registrado (CLV médio
> IC95 bootstrap cluster por jogo > 0 **E** ROI IC_lower > −2%) → só então
> discutir capital. Ao ritmo histórico (~0,7 pick/dia da coorte legada), 100
> liquidados cai perto de dezembro/2026, depois do fim da janela pré-registrada
> (30/09/2026) — a janela provavelmente expira antes do N, e estendê-la é
> tentativa N+1.
>
> **Próximo evento objetivo:** `brasileirao-sombra-noite` em 25/07 23:00 local
> (a execução das 10:00 já ocorreu e produziu o 7º smoke). **H1 segue
> `HYPOTHESIS_REFUTED`** (abertura-fantasma, bloco de 2026-07-17), H3 e H5
> seguem separadas e com gate congelado em 100 `MATURED_ELIGIBLE`.

> ## BACKFILL PIT ISOLADO (2026-07-21)
>
> `src/data/pit_backfill.py` implementa raw imutável com manifesto/hash, curated
> SQLite separado, resolução versionada de entidades, clocks PIT, closing line
> formal, walk-forward e quality gate com bootstrap agrupado. Testes hostis
> cobrem adulteração, ambiguidade, cotação pós-kickoff e lookahead. Nenhum
> registro é escrito em `matches.db`; o gate permanece sem capital automático.
> Ver `docs/BACKFILL_POINT_IN_TIME.md`, `docs/CLOSING_LINE.md`,
> `docs/PAST_ATTEMPT_LEDGER.md` e `docs/HISTORICAL_SOURCE_REGISTER.md`.

> A coorte H3/H5 iniciada em 2026-07-22 exige contrato estrito e bookmaker
> auditável. Os 8 registros anteriores são `LEGACY_INCOMPLETE`; não contam.
> `scripts/sombra.py` bloqueia a persistência prospectiva quando o bookmaker não
> for fornecido, e o settle exige closing pré-kickoff.

> ## FECHAMENTO DAS RESSALVAS TÉCNICAS (2026-07-20)
>
> O ledger H3/H5 passou a registrar prospectivamente `predicted_at`,
> `kickoff_at` UTC, turno da captura, fonte, odd capturada, abertura separada,
> fechamento bruto e par de fechamento. Custos da sombra são explicitamente
> `not_applicable_shadow_no_execution`, 0u: não há execução financeira. O
> relatório `shadow-report/v2` mede cobertura desses campos e mantém registros
> anteriores como legados, sem backfill retrospectivo.
>
> O `startTimestamp` do Sofascore agora é persistido em `kickoff_at`; os três
> scripts de pesquisa antes apontados pelo CI usam Elo `ratings_asof`, eliminando
> o lookahead conhecido. Backup/restore local implementado em
> `src.backup_restore`: snapshot online SQLite, manifesto SHA-256, verificação de
> adulteração, `integrity_check` e restore somente em raiz nova. Roundtrip real
> verificado em `C:\Claude-projetos\Claude\backups\brasileirao-20260720T1430Z`
> e raiz restaurada homônima, com **1.165 partidas** e integridade `ok`.
> As tarefas manhã/noite agora têm `RestartCount=3`, intervalo `PT15M`,
> `StartWhenAvailable=True` e mantêm `IgnoreNew`, fechando a perda de janela por
> falha transitória sem permitir execuções concorrentes.
>
> Validação: **325 passed, 1 warning sintético conhecido; CI 5/5 sem dívida
> temporal**. Nenhuma regra de seleção, threshold, hiperparâmetro, stake ou
> settlement econômico mudou. Única pendência inevitável: passagem do tempo
> até 100 picks H3 liquidados; hoje são 2/100.

> ## AUDITORIA FINAL LOCAL (2026-07-20)
>
> Revisão independente do estado atual, sem mudança científica ou econômica.
> Suíte completa: **320 passed, 1 warning conhecido**; `scripts/ci_check.py`:
> **5/5**; suíte suportada de `tools/`: **139 passed, 1 skipped**; manifest do
> core e auditoria byte a byte: **44/44 idênticos**. O SQLite operacional
> passou `integrity_check` e `quick_check`, com 1.165 partidas, 8.297 linhas
> de odds e 80.375 snapshots; não foram encontrados eventos/partidas
> duplicados, placares negativos, HT > FT ou odds não finitas/não positivas.
> Nove linhas de mercado são parciais, condição já coberta por descarte claro
> do mercado incompleto (`test_mercado_parcial_pula_o_mercado_nao_o_jogo`).
>
> B3b/B4 seguem protegidos pelos testes de confronto repetido por data e
> idempotência por `bet_id`. A H3 tem **7 picks, 2 maturados e 5 abertos**:
> ROI bruto +17,5%, CLV médio −5,025%, Brier/RPS 0,269568 e log loss 0,732336.
> Esses números são apenas diagnóstico operacional: o gate de 100 liquidados
> permanece fechado e o resultado econômico é **INCONCLUSIVO**. Nenhum bug
> novo inequívoco foi reproduzido; nenhum código, parâmetro ou artefato
> operacional foi alterado. Veredito: **PASS LOCAL COM AMOSTRA AINDA
> INSUFICIENTE**.

> ## 🔵 AUDITORIA HOSTIL DE ROBUSTEZ — RODADA 2 (2026-07-18/19)
>
> Rodada dedicada a este domínio (branch `claude/brasileirao-predictor-audit-11f575`).
> B3b/B4 (settlement com `match_date` + idempotência por `bet_id`, `e54a55d`)
> **reconfirmados no código e nos testes que os protegem**
> (`test_settle_confronto_repetido_exige_match_date_para_desambiguar`,
> `test_settle_idempotente_sobrevive_a_reordenacao_do_arquivo`). Vendor
> byte-idêntico (44/44), `sync_core --check` OK, CI 5/5.
>
> **5 correções de robustez reais** (commit `ba0bd7d`, nenhuma científica):
> (1) `shin_probabilities` rejeita odds 0/negativa/NaN/Inf/None com ValueError
> claro; (2) `_market_probs` ignora linhas-placeholder do Sofascore
> (1X2=1.0/1.0/1.0 — 4 reais na base viravam p=⅓ fabricado); (3) `sombra.settle`
> ganhou dedupe intra-execução (pick duplicado não liquida 2×), CLV só com
> fechamento válido (nunca NaN no ledger) e recusa de linha O/U inteira (push
> não implementado); (4) `record_result` rejeita placar negativo; (5) comentário
> do `config.yaml` reconciliado com a flag `ensemble_xg` ligada. Suíte
> **302 → 320 verdes** (+18 hostis: Shin degenerado, liquidação duplicada,
> banco truncado, concorrência WAL, etc. — `tests/test_hostil_2026_07_18.py`).
>
> **Sombra (2026-07-19)**: H3 = 4 picks / 2 liquidados (ROI +17,5%, CLV médio
> −5,03%); H5 = 2 picks / 1 liquidado (CLV −6,87%). CLV negativo em 3/3 —
> coerente com a abertura-fantasma, mas amostra irrisória: **nenhuma conclusão
> antes de 100 liquidados** (marco congelado no trials.json). Achado
> operacional: run noturno de 2026-07-18 02:00Z morreu com exit 0xC000013A
> (processo interrompido — shutdown/logoff), heartbeat ficou `STARTED` e o
> lock ficou órfão; o runner sabe recuperar lock órfão (precedente de
> 2026-07-16) — observar o próximo run noturno.

> ## ADENDO ECOSSISTEMA (2026-07-18)
>
> Vendor de `predictor_core` byte-idêntico ao canônico (`sync_core.py --check`,
> `tools/vendor_byte_audit.py`), sincronizado em `5276f65`. Suíte: **302
> passed**. Settlement teve 2 bugs financeiros reais corrigidos numa rodada
> anterior (`e54a55d`: `match_date` para desambiguar confrontos repetidos;
> idempotência por `bet_id` em vez de posição de arquivo) — ver
> `FINAL_FORENSIC_REVIEW.md`. Auditoria hostil adicional 2026-07-18 (goal
> model com histórico vazio/degenerado, odds inválidas, placar negativo):
> nenhum bug novo encontrado. Sem incidente de segurança próprio. Pendências
> reais: `PENDENCIAS_ABERTAS.md` (SCI-5 amostra do shadow mode, DEBT-3
> `brier` duplicado em scripts scratch — nenhuma bloqueante). Documento
> canônico do ecossistema: `../ECOSYSTEM_HANDOFF.md`.
>
> ## 🔴 ABERTURA-FANTASMA CONFIRMADA — O SINAL DA H1 ERA ARTEFATO (2026-07-17)
>
> Auditoria da fonte + falsificação executada (adendos 2026-07-17 em
> `docs/RELATORIO_BACKTEST_2026-07-10.md`): o `initialFractionalValue` do
> Sofascore é abertura-template (favorece OVER em ~64% vs ~14% no
> fechamento; 60% dos pares ficam mais perto do fechamento INVERTIDO;
> parser inocentado). **Backtest refeito a preço de fechamento
> (`scripts/backtest_close.py`): OU2.5 vira ROI −7,8%, PSR 0,14** — o
> +7,9%/CLV +19,55% da H1 morava inteiramente na abertura fictícia.
> Coerente com o forward 2026 (ROI −22% a odds correntes).
>
> Consequências: (1) "ampliar N da H1" perdeu a motivação; (2) nunca mais
> julgar edge por backtest em abertura — só populações de sombra a odds
> CORRENTES com timestamp (H3 baseline, H5 ensemble) decidem GO; (3) zero
> aposta real continua sendo a única postura defensável.

> ## 🟢 FLAG LIGADA + H5 PRÉ-REGISTRADA (2026-07-17, mesmo dia)
>
> **`ensemble_xg.enabled: true`** — o serving (predict/prever/display) agora
> blenda com o atk/def-xG; toda predição blended sai carimbada
> `model: ensemble_xg` no predictions.jsonl. Após o merge, rodar
> `python -m src.cron_update_models` no repo principal para criar o cache
> (sem ele o serving degrada para baseline com aviso, nunca cai).
>
> **H5 pré-registrada**: `h5-ensemble-xg-sombra-2026` no trials.json
> (`scripts/registrar_h5.py` — script separado do governanca.py de
> propósito: re-rodar o governanca apagaria o sharpe 0.0722 observado da
> H1). Funil idêntico ao da H3 (OU2.5, edge 2–15%, sombra 0u), só muda a
> fonte da probabilidade. Decisão com n≥100 liquidados: CLV IC95 > 0 ∧
> ROI IC_lower > −2%. **A H3 segue baseline puro por construção**
> (sombra.py chama model.predict_match direto, imune à flag); a H5 roda em
> PARALELO nos mesmos jogos via `sombra_h5_*.jsonl` — o agendador diário
> (cron → settle → capture → report) cobre as duas sem mudança. Mudar
> blend/hiperparâmetros do ensemble é tentativa N+1. Suíte **298 verdes**,
> CI 5/5.

> ## 🟢 ENSEMBLE ATK/DEF-xG INTEGRADO AO SERVING, ATRÁS DE FLAG (2026-07-17)
>
> A simulação walk-forward 2025+2026 (`docs/SIMULACAO_2025_2026.md`)
> diagnosticou o modelo como calibrado-mas-sem-resolução e validou o
> **ensemble 50/50 baseline × atk/def estimado em xG**: dBrier 1X2 −0,0073,
> IC95 [−0,0122, −0,0019], significativo em cada ano isolado, OU2.5
> preservado. Acerto 1X2: 50,3% → 52,1%.
>
> **Integração**: `src/xg_model.py` (fit em 2 etapas: forças em
> 0,85·xG+0,15·gols, α/ρ nos gols reais; hiperparâmetros congelados pela
> validação 2024-H2) + cache `xg_model_parameters` (JSON, escrito pelo
> `cron_update_models` quando ligado) + hook único `maybe_blend` nos 3
> caminhos de serving (predict.show, display.compute, prever.py). Predição
> blended é carimbada `model: ensemble_xg` no predictions.jsonl.
>
> **`ensemble_xg.enabled: false` por padrão** — H1/H3 foram medidas com o
> baseline puro; ligar em produção exige pré-registro novo (governança).
> Flag OFF = serving byte a byte idêntico (testado). Suíte **293 verdes**,
> CI 5/5. Falha do ensemble degrada para baseline com aviso, nunca derruba.

> ## 🔵 AUDITORIA DE INTEGRAÇÃO COM O CORE v1.3.0 (2026-07-12)
>
> **Sincronização 100%**: vendor em **predictor_core v1.3.0-ga-20260711**
> (aggregate `3445e37f43c458cc`, sync 2026-07-12), byte a byte idêntico ao
> core canônico — drift zero. Consumo real: `contracts`, `testing`,
> `measurement`, `obs`; os 7 módulos não importados (kernel/rating, ledger,
> data, etc.) são omissões intencionais do roadmap (agosto/2026).
>
> **Duas duplicações identificadas — dívida de manutenção para a próxima
> janela de código** (não urgente em modo de observação):
> 1. Shin de-vig: `src/math_utils.shin_probabilities` (12 arquivos usam) vs
>    `core.measurement.calibration.shin_devig` (0 usam). A local devolve
>    `(probs, z, overround)` — interface mais rica; convergir quando o core
>    expor o equivalente.
> 2. Bootstrap: `src/bootstrap.py` reimplementa percentile bootstrap em vez
>    de compor sobre `core.measurement.bootstrap.bootstrap_ci` (que outros
>    scripts do repo já usam) — duas fontes de IC95% no projeto.
>
> Pendência W2 herdada do wc (bet_id no livro): **já fechada** — bet_log.py
> sincronizado com o fix de 2026-07-11 do wc-predictor-v2 + test_bet_id.py.
> Brasileirão em **modo de observação** (sombra automática; próxima marca:
> reexecutar varredura forward com N=40 —
> `docs/RELATORIO_FORWARD_18JOGOS_2026-07-12.md`).

> ## 🔴 BACKTEST CONCLUÍDO — VEREDITO NO-GO (2026-07-10, mesmo dia)
>
> Ciclo completo executado: coleta (1.165 eventos, 2024+2025+2026 parcial) →
> espelho (937 jogos + 228 fixtures) → cache (a=0.199 b=0.708 α=0.0006
> ρ=0.014) → harness PASSOU → H1/H2 pré-registradas → walk-forward (4 blocos
> de 19 rodadas, 1.673 apostas no funil).
>
> **H1 (OU2.5): NO-GO.** n=455, ROI +7,9%, **CLV open +19,55%**, PSR 0,94 —
> mas IC95 do pnl [−0,022, +0,172] cruza zero e DSR 0,94 < 0,95. Sinal de
> preço forte, conversão em lucro ainda sem significância. **Zero aposta
> real.** Investigação: ingerir 2023 (season_id 48982) e rodar 2026 em modo
> SOMBRA para ampliar N; NÃO variar configuração (N+1 deflaciona).
> **H2 (picks 1T ≥60%): VALIDADA informativa** — n=1.493, acerto 79,0% vs
> confiança 79,8%. **1X2 reproduziu a Copa: ROI −15,4%, CLV −6% — nunca.**
> Sharpes observados gravados no trials.json (denominador imortal).
>
> Detalhes e plano da retomada (16-17/07 jogos atrasados; rodada cheia
> 21/07): `docs/RELATORIO_BACKTEST_2026-07-10.md`. Suíte **241 verdes**,
> CI 5/5. odds_shop --from-file validado com snapshot de teste.

> ## 🟢 CRIAÇÃO DO DOMÍNIO (2026-07-10)
>
> **Projeto criado a partir do wc-predictor-v2 pós-Copa.** Backup limpo
> (sem .venv/__pycache__/.pytest_cache/worktrees/caches de coleta), repo git
> NOVO (histórico da Copa fica no wc-predictor-v2 original, intocado).
> Vendor no **predictor_core v1.1.0** — `sync_core --check` reporta os 4
> consumidores em sincronia, incluindo este. *(Superado: v1.3.0 desde
> 2026-07-11 — ver auditoria 2026-07-12 no topo.)*
>
> **Limpeza da Copa (PASSO 1.2)**: bets/bankroll/predictions/period_predictions
> zerados (arquivos mantidos); `results.jsonl` da Copa preservado como
> `results_wc2026_historico.jsonl` e um novo vazio criado; artefatos derivados
> (backtest_bets.csv, live_decisions.csv, bootstrap_cache.json, wc.log)
> removidos; `matches.db` manteve o SCHEMA e perdeu os DADOS do domínio Copa —
> decisão consciente: manter os ~49k jogos de seleções contaminaria a
> calibração do Poisson (o fit filtra por DATA, não por torneio) e o Elo de
> clubes não compartilha times com seleções. Base do Brasileirão nasce limpa.
>
> **Adaptações de domínio**: telemetria/logger `wc` → `brasileirao`
> (obs/ingest/predict/status/backtest/prever); constantes da Copa viraram
> config (`league`, `tournament_name`; display._tournament_avg e
> simulator.derive_groups agora leem config); smoke do CI usa
> Flamengo × Palmeiras; odds_shop com sport key configurável
> (`soccer_brazil_campeonato` — CONFIRMAR no /v4/sports com chave real).
> Simulador de bracket NÃO se aplica a pontos corridos (encerra com aviso).
>
> **Dados**: Sofascore ut_id **325**, seasons 2024=**58766**, 2025=**72034**,
> 2026=**87678** (descobertos via `--seasons 325` em 2026-07-10; a season
> "20/21" na lista é a temporada COVID — assinatura de que 325 é o Brasileirão).
> `matches` é alimentada por `scripts/sync_matches_from_sofascore.py`
> (upsert idempotente, tournament="Brasileirão Série A", neutral=0). **NÃO
> rodar `python -m src.ingest`** (repovoaria a base com seleções do martj42).
>
> **Governança (ordem obrigatória)**: `scripts/governanca.py` roda o harness
> de controle positivo (edge sintético: ataque do mandante ×1,3 no funil O/U
> real; ruído: jitter ±3pp pagando vig) → emite o atestado → pré-registra
> **H1** (OU2.5, edge 2–15%, walk-forward) e **H2** (picks 1T conf ≥60%,
> informativa) em `data/trials.json`. Só então
> `scripts/backtest_walkforward.py` (blocos de 19 rodadas, params
> recalibrados por bloco, Elo forward, bootstrap por cluster de jogo, DSR
> descontado pelo registro) produz o **GO/NO-GO**: PSR ≥ 0,80 ∧ IC_lower > 0 ∧
> DSR ≥ 0,95. **Nenhuma aposta real antes de GO.**
>
> Pendências herdadas do wc: W2 (bet_id uuid no livro), generalização do
> Ledger no core (agosto/2026 — até lá o bet_log é por domínio).

## O que é o projeto

Sistema CLI em Python que prevê resultados do Brasileirão Série A e opera
apostas de valor com governança anti-data-snooping. Roda 100% local
(Python + SQLite, sem cloud). Idioma do projeto: português.

Máquina do Leo: Windows, em `C:\Claude-projetos\Claude\brasileirao-predictor`,
atrás de proxy corporativo Volvo com inspeção TLS (resolvido em
`src/sofascore.py` via CA bundle do Windows). A coleta do Sofascore roda na
máquina do Leo (o sandbox de CI não alcança o Sofascore).

## Mapa rápido

- Motor: `src/ratings.py` (Elo+decay) → `src/model.py` (NB+Dixon-Coles, MLE)
  → `src/predict.py`/`src/display.py` (serving) — genérico, zero mudança.
- Coleta: `src/ingest_sofascore.py` (config-driven) →
  `scripts/sync_matches_from_sofascore.py` → `src/cron_update_models.py`.
- Pesquisa: `scripts/backtest_walkforward.py` (read-only, P12).
- Governança: `scripts/governanca.py` + vendor `measurement/trials.py`
  (TrialRegistry, DSR) + `testing/harness.py` (controle positivo).
- Operação: `scripts/odds_shop.py`, `src/bet_log.py`, `src/settle.py`.
- CI: `scripts/ci_check.py` (pytest + 4 barreiras estáticas/smoke).
