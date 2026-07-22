# PAST_ATTEMPT_LEDGER — backfill point-in-time

| ID | Tentativa | Dados | Resultado | Evidência | Motivo | Estado |
|---|---|---|---|---|---|---|
| PA-01 | Backtest walk-forward H1/H2 | Sofascore 2024–2025 | H1 NO-GO; H2 informativa | `docs/RELATORIO_BACKTEST_2026-07-10.md` | abertura-template e IC do P&L cruzando zero | encerrada, não repetir |
| PA-02 | Sombra H3/H5 prospectiva | Sofascore 2026 | 2 maturados de 100; inconclusivo | `data/sombra_*.jsonl`, `scripts/report_shadow_mode.py` | amostra ainda curta | ativa |
| PA-03 | Backfill API-Football 2022–2024 | fixtures sem odds temporais | cobertura de placares, inelegível para ROI/CLV | `src/data/api_football_provider.py`, `src/data/historical_expansion.py` | não há bookmaker/captured_at/closing reconstruível | quarantined |
| PA-04 | Backfill Sportmonks | catálogo opt-in | não executado sem token e sem validação de odds | `src/data/sportmonks_provider.py` | fonte não comprovada para economic evaluation | pending discovery |
| PA-05 | Curated PIT isolado | store raw + curated | contrato implementado e testado; não promove dados ao vivo | `src/data/pit_backfill.py`, `tests/test_pit_backfill.py` | preserva origem e temporalidade | PASS LOCAL |

Nenhuma tentativa histórica aumenta o Quality Gate por contagem. A promoção
para o pipeline vivo exigiria uma fonte aceita com preços observados no tempo,
revisão de aliases e um TrialRegistry explícito.
