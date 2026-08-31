# Hiperparâmetros e constantes mágicas — registro de auditoria (2026-07-02)

Constantes fixadas sem validação empírica registrada no repositório. Nenhuma
bloqueia a operação; todas merecem análise de sensibilidade **pós-Copa** (a
coleta ao vivo tem prioridade até ~19/07/2026).

| Constante | Valor | Local | Observação |
|---|---|---|---|
| `margin_multiplier` | 1.0 / 1.5 / 1.75+(d−3)/8 | `brasileirao_predictor/ratings.py:18-24` | Difere do World Football Elo padrão; sem fonte |
| K-factors por torneio | 60/50/40/30/20 | `config.yaml` | Plausíveis; sem grid-search documentado |
| `window_years` | 6 | `config.yaml` | Corte duro do Elo |
| `form_half_life_years` | 4.0 | `config.yaml` | Decay por INATIVIDADE (regressão à média), não decay de resultados antigos |
| `calibration_window_years` | 4 | `config.yaml` | Janela do MLE |
| `home_advantage` | 100 | `config.yaml` | Padrão da literatura, não validado nesta base |
| Janela de edge | 2%–15% | `config.yaml` | "Sweet spot validado" — validação não localizada no repo |
| Tolerância de data no casamento | ≤ 3 dias | `brasileirao_predictor/backtest.py` (`_find_odds`) | Pode casar jogo errado em confrontos repetidos em <3 dias |
| `INCENTIVE_CUT` | 0.35 | `brasileirao_predictor/simulator.py` | Fator "Gijón"; sem fonte |
| `RED_RATE` | 0.22 | `brasileirao_predictor/simulator.py` | Vermelhos/time/jogo; sem fonte |
| `RED_LAMBDA_PENALTY` | 0.45 | `brasileirao_predictor/simulator.py` | Queda de λ com um a menos; sem fonte |
| Pênaltis = logística Elo | — | `brasileirao_predictor/simulator.py` (`_knockout_winner`) | Sem prorrogação modelada |
| x0 do θ_xg / bounds | 0.5 / (−5,5) | `brasileirao_predictor/model.py` | Arbitrário |
| τ de Dixon-Coles sobre NB | — | `brasileirao_predictor/model.py` | Aproximação: τ foi derivado para Poisson; renormalização da grade compensa |
| Sem downweight temporal (φ) no MLE | — | `brasileirao_predictor/model.py` | Difere do artigo DC original; recência só via janela dura |
| Shin: brentq falha ⇒ z=0 | — | `brasileirao_predictor/math_utils.py` | Degrada para normalização proporcional em silêncio |
| `dd <= 3` + bracket sorteado | — | `brasileirao_predictor/simulator.py` | Mata-mata não usa o chaveamento oficial FIFA (declarado) |

## Revisão dos scripts de pesquisa (2026-07-02, pendência resolvida)

Os 17 scripts de `brasileirao_scripts/` (investigação causal: auditoria, calibrações, Maher,
confound, zebra, walk-forward etc.) **usam o pipeline correto**: `hist` vem de
`ratings.compute_ratings` (contrato `(diff, hs, as)`, forward-only), nenhum
consulta `match_statistics` (imunes ao bug do período) e nenhum usa
`current_elo`. As conclusões de `docs/CONCLUSOES.md`/`CAUSA_RAIZ.md` **não**
carregam os bugs P1/P2/P3 da Fase 2.

Exceções (scripts da v3 embrionária — corrigir ANTES de usar em qualquer
conclusão):
- `brasileirao_predictor/research/vorp_ridge.py` — `elo_diff` lido de `current_elo` (lookahead;
  usar `ratings_asof`).
- `brasileirao_predictor/research/survival_test.py:172` — `db.load_elo` (idem).

## Notas da auditoria
- Warnings de convergência/bound-pinning do MLE foram adicionados em
  `brasileirao_predictor/model.py` (P10) — parâmetro cravado em bound agora avisa em voz alta.
- O bootstrap de significância usa **cluster por jogo** (`ci_mean_cluster` em
  `brasileirao_predictor/bootstrap.py`) — apostas do mesmo jogo são correlacionadas; o IC i.i.d.
  anterior era estreito demais.
- A validação de `initialFractionalValue` como abertura real se apoia em
  apenas ~26 eventos com snapshot pré-jogo (`odds_snapshots.pre_match=1`).
  Revalidar com os snapshots acumulados pelo cron da Copa.
