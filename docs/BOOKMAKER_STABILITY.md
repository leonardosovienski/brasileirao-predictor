# Estabilidade pré-registrada de bookmaker

Antes de escolher a casa única de H3/H5, o ledger sanitizado exige pelo menos
três smokes em uma janela mínima de 24 horas, presença em 80% dos smokes,
cobertura de O/U 2.5 em pelo menos 50% dos eventos e lag máximo de 15 minutos.
Os critérios estão congelados em `src/data/bookmaker_stability.py`.

Exchanges (`matchbook`, `betfair`, `smarkets`) são rejeitadas nesta coorte: sua
semântica de preço/liquidação não é assumida equivalente à de sportsbook.
O comando `python scripts/record_odds_smoke.py --region eu` só anexa metadados
sanitizados a `data/odds_source_smokes.jsonl`; não cria picks. O relatório é
`python scripts/record_odds_smoke.py --report`.
