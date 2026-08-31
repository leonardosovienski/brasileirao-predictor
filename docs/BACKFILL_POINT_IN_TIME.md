# Backfill point-in-time

O backfill histórico é deliberadamente isolado de `matches.db`.

- **Raw:** bytes imutáveis, manifesto, SHA-256, fonte, licença, cobertura e status de quarentena.
- **Curated:** SQLite próprio com partidas, odds, aliases e hashes de proveniência; cada linha conserva `ingested_at`, `odds_captured_at` e `kickoff_at`.
- **Evaluation:** somente registros disponíveis no instante da previsão (`ingested_at <= predicted_at`) e com partida futura naquele instante.

Entity resolution usa aliases explícitos e versões de mapeamento. Colisões ou nomes ambíguos são rejeitados; não há escolha heurística silenciosa. O walk-forward exige fronteiras cronológicas estritas e a qualidade usa bootstrap agrupado por partida/cluster. O gate devolve `INSUFFICIENT_SAMPLE` abaixo do mínimo e nunca habilita capital automaticamente.

O módulo implementado é `brasileirao_predictor/data/pit_backfill.py`, com testes hostis em `tests/test_pit_backfill.py`. A implementação local valida o contrato e a segurança temporal; ela não inventa uma amostra histórica nem considera uma fonte sem odds PIT economicamente elegível.
