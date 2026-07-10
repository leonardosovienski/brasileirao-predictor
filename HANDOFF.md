# HANDOFF.md — brasileirao-predictor

> ## 🟢 CRIAÇÃO DO DOMÍNIO (2026-07-10)
>
> **Projeto criado a partir do wc-predictor-v2 pós-Copa.** Backup limpo
> (sem .venv/__pycache__/.pytest_cache/worktrees/caches de coleta), repo git
> NOVO (histórico da Copa fica no wc-predictor-v2 original, intocado).
> Vendor no **predictor_core v1.1.0** — `sync_core --check` reporta os 4
> consumidores em sincronia, incluindo este.
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
