# Relatório de Validação Forward — Brasileirão 2026 (iniciado 2026-07-12)

## Contexto

Teste forward (fora da amostra de calibração) sobre os primeiros 18 jogos
disputados do Brasileirão 2026, para checar consistência com o backtest
walk-forward de 1.165 jogos (`docs/RELATORIO_BACKTEST_2026-07-10.md`), cujo
único mercado com edge validado é **OU 2.5** (ROI +7,9%, CLV +19,6%).

## Metodologia

Mesma do backtest: Elo forward (só vê o passado, `window_years=6`,
`form_half_life_years=4.0`), Poisson/Dixon-Coles calibrado apenas com jogos
anteriores a 2026-01-28 (sem contaminação da temporada 2026 no treino),
odds de fechamento devigadas por Shin (`src.math_utils.shin_probabilities`).
Regra de compra idêntica ao backtest: só entra se `2% <= EV <= 15%`
(`cfg["backtest"]`).

Scripts (todos aceitam N de jogos como argumento posicional, default 18):
- [scripts/predict_first18_2026.py](../scripts/predict_first18_2026.py) `[N]` — 1X2 puro (hit-rate bruto)
- [scripts/predict_first18_ou_dc.py](../scripts/predict_first18_ou_dc.py) `[N]` — OU2.5 e DC (hit-rate bruto)
- [scripts/predict_walkforward_ev.py](../scripts/predict_walkforward_ev.py) `[N]` — EV/P&L simulado
- [scripts/predict_first18_teams.py](../scripts/predict_first18_teams.py) `[N]` — quebra por time (gols esperados vs reais, Brier por time)

## Resultados — N=18 (2026-07-12)

### 1X2 puro (hit-rate, sem EV)
9/18 → 7/18 acertos após corrigir bug de double-counting de home advantage (38,9%). Confirma o viés estrutural já documentado: o modelo nunca prevê empate (P(empate) nunca é a maior das três), então perde todos os 6 empates reais da amostra. Consistente com os 26,2% do backtest de 1.165 jogos.

### OU 2.5 e DC (hit-rate bruto, sem regra de EV)
| Mercado | Hit-rate |
|---|---:|
| OU 2.5 | 8/18 (44,4%) |
| DC (1X/X2, lado mais provável) | 13/18 (72,2%) |

### EV com Shin de-vig (regra de compra 2%–15%, stake 1u)
| Mercado | Apostas geradas | Vitórias | P&L | ROI |
|---|---:|---:|---:|---:|
| **OU 2.5** | 10/18 | 4 (40,0%) | **−1,45u** | **−14,5%** |
| **DC (1X/X2)** | 11/18 | 6 (54,5%) | **−2,83u** | **−25,7%** |

### Quebra por time (gols esperados vs reais, calibração)

Para cada time nos 18 jogos, comparamos gols feitos/sofridos reais com o
`lambda` (gols esperados) que o modelo atribuiu à partida, e o Brier score
(1X2) — mede se o erro está distribuído ou concentrado em times específicos.

| Time | J | ΔAtaque (GF−xGF) | ΔDefesa (xGC−GC) | 1X2 | Brier |
|---|---:|---:|---:|---:|---:|
| Botafogo | 2 | **+4,22** | **−2,92** | 1/2 | 0,53 |
| Grêmio | 2 | **+4,05** | −1,99 | 1/2 | 0,47 |
| Palmeiras | 2 | **+3,73** | −1,20 | 1/2 | 0,51 |
| Chapecoense | 2 | +2,52 | −0,66 | 1/2 | 0,64 |
| Vitória | 2 | +0,79 | −2,12 | **2/2** | 0,30 |
| Cruzeiro | 1 | −0,96 | **−2,50** | 1/1 | 0,37 |
| Coritiba | 1 | −1,58 | −0,09 | 0/1 | 0,95 |
| Internacional | 2 | **−1,22** | +1,14 | 0/2 | 1,10 |
| Flamengo | 2 | **−1,64** | −1,34 | 0/2 | 1,02 |
| *(demais 11 times)* | — | próximo de 0 | próximo de 0 | — | — |

ΔAtaque > 0 = time fez mais gols do que o modelo previa (ataque subestimado);
ΔDefesa > 0 = time sofreu menos gols do que o modelo previa (defesa
subestimada).

**Brier médio global (1X2): 0,657** vs. piso de referência "sempre
33%/33%/33%" = 0,667 — calibração praticamente nula nesta amostra (mal supera
o chute uniforme). Mas o erro não está distribuído igualmente: está
concentrado em ~5 times com viés forte nos dois lados simultaneamente
(Botafogo/Grêmio/Palmeiras para cima, Flamengo/Internacional para baixo),
enquanto o restante do elenco está razoavelmente calibrado. Padrão consistente
com drift do Elo herdado de 2024/25 não capturando mudanças de elenco/técnico
rápido o suficiente (`form_half_life_years=4.0`) — hipótese a investigar se
persistir na marca de 40 jogos, não indicativo suficiente ainda.

## Resultados — N=40 (2026-07-15)

Reexecução com o dobro da amostra (jogos de 2026-01-28 a 2026-03-11).

| Métrica | N=18 | N=40 | Tendência |
|---|---:|---:|---|
| 1X2 hit-rate | 38,9% (7/18) | 42,5% (17/40) | leve melhora |
| OU2.5 hit-rate (bruto) | 44,4% (8/18) | 47,5% (19/40) | leve melhora |
| DC hit-rate (bruto) | 72,2% (13/18) | 77,5% (31/40) | melhora |
| OU2.5 EV — apostas geradas | 10 | 25 | — |
| **OU2.5 EV — ROI** | −14,5% | **−33,8%** | **piorou** |
| DC EV — apostas geradas | 11 | 23 | — |
| DC EV — ROI | −25,7% | −16,5% | melhorou |
| Brier médio (1X2, piso uniforme=0,667) | 0,657 | 0,656 | estagnado |

### Quebra por time — N=40 (destaques)

| Time | J | ΔAtaque | ΔDefesa | 1X2 | Brier |
|---|---:|---:|---:|---:|---:|
| Palmeiras | 4 | **+5,66** | −1,32 | 3/4 | 0,43 |
| Chapecoense | 3 | +4,02 | −2,71 | 1/3 | 0,71 |
| Grêmio | 4 | +3,48 | −2,63 | 3/4 | 0,42 |
| Botafogo | 3 | +3,23 | −2,47 | 2/3 | 0,49 |
| Internacional | 5 | **−2,07** | +0,68 | 2/5 | 0,77 |
| Cruzeiro | 4 | −1,21 | **−4,17** | 1/4 | 0,82 |

Palmeiras, Grêmio e Botafogo mantêm o mesmo viés positivo de N=18 (times que
o modelo subestima) com base agora 2x maior — não era ruído do N=18.
Internacional segue subestimado negativamente. Cruzeiro surge como o pior
calibrado em defesa (sofreu bem mais gols do que o modelo previa), sinal
novo que não estava claro em N=18.

## Leitura

O achado central de N=40 **não é "mais do mesmo" — é uma inversão de
expectativa**. Em N=18 a leitura foi "cedo demais pra refutar o backtest de
1.165 jogos". Com o dobro da amostra:

- **O ROI de OU2.5 não convergiu de volta para o +7,9% do backtest — piorou
  de −14,5% para −33,8%**, com mais que o dobro de apostas geradas (25 vs
  10). O viés (o modelo apostando OVER onde o backtest histórico indicava
  edge no UNDER) se repetiu e se intensificou, não diluiu. Isso já não é
  atribuível só a ruído de amostra pequena.
- **DC melhorou de −25,7% para −16,5%** — ainda negativo, mas na direção
  certa. Hit-rate bruto subiu de 72,2% para 77,5%, mais perto do patamar
  necessário pras odds curtas (~1,3–2,0) darem ROI positivo.
- **Calibração (Brier) ficou estagnada** (0,657 → 0,656) — o modelo não está
  "aprendendo" a temporada 2026 conforme mais jogos entram nessa janela de
  40, e o viés por time (Palmeiras/Grêmio/Botafogo pra cima,
  Internacional/Cruzeiro pra baixo) se manteve entre as duas marcas.
- **Hipótese de causa raiz não descartada, agora mais provável**: o
  `form_half_life_years=4.0` do Elo pesando demais o histórico 2024/25 pra
  times que mudaram elenco/técnico. Vale investigar diretamente (não só
  esperar mais N) na próxima janela de código — comparar meia-vida mais
  curta especificamente nos times com viés persistente.

## Compromisso de reexecução

**Reexecutar esta varredura na marca de 80 jogos disputados** (dobro
novamente, mantendo a cadência 18→40→80), quando o IC95% do ROI/RPS já
fecha o suficiente para separar sinal de ruído — mesmo critério usado no
veredito H4 (`docs/CONCLUSOES.md`, `data/h4_verdict.log`). Comando:

```
python scripts/predict_walkforward_ev.py 80
python scripts/predict_first18_teams.py 80
```

Se o ROI de OU2.5 continuar piorando em N=80, isso deixa de ser "cedo
demais" e vira caso pra investigar o `form_half_life_years` antes de
acumular mais jogos — não adianta esperar mais dados se a causa é um
hiperparâmetro mal ajustado pro início de temporada.

## Status operacional

Brasileirão entra em **modo de observação** (mesmo regime já aplicado ao
mercado cripto): sem intervenções ativas neste teste forward. O modo sombra
continua operando automaticamente (captura ~10h, settle ~23h,
`scripts/sombra_diaria.py`), acumulando dados sem necessidade de
intervenção manual até a próxima marca de reavaliação.
