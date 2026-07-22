# PAST_ATTEMPT_LEDGER — H3/H5

| ID | Hipótese/tentativa | Implementação | Dados | Resultado | Evidência | Estado atual |
|---|---|---|---|---|---|---|
| PA-01 | H1 OU2.5 walk-forward | abertura vs fechamento | Sofascore 2024–2025 | fechamento ROI -7,8%, PSR 0,14 | `docs/RELATORIO_BACKTEST_2026-07-10.md` | REFUTED |
| PA-02 | H3 shadow OU2.5 | odds correntes pré-evento | Sofascore 2026 | registros atuais sem contrato completo | `scripts/evaluate_shadow_cohort.py` | STILL_ACTIVE |
| PA-03 | H5 ensemble xG shadow | população paralela H3 | Sofascore 2026 | sem coorte elegível completa ainda | `data/trials.json` | STILL_ACTIVE |
| PA-04 | Backfill API-Football | fixtures históricas | API opt-in | sem odds/bookmaker/timestamps PIT | `src/data/historical_expansion.py` | FAILED |
| PA-05 | Backfill Sportmonks | odds históricas | sem token/auditoria | não verificado | `docs/HISTORICAL_SOURCE_REGISTER.md` | NOT_VERIFIED |
| PA-06 | Curated PIT isolado | raw + curated + evaluation | dados de teste | contrato implementado e testado | `src/data/pit_backfill.py` | WORKED |
| PA-07 | Shadow evaluator estrito | classificação e hash | JSONL atual | 8 `LEGACY_INCOMPLETE`, 0 elegíveis | `scripts/evaluate_shadow_cohort.py` | STILL_ACTIVE |

Registros legados nunca aumentam o Quality Gate. H3/H5 só podem ser avaliadas
com 100 picks prospectivos elegíveis e liquidados, sem alterar o modelo.
