# Relatório de Validação Forward — Primeiros 18 Jogos do Brasileirão 2026 (2026-07-12)

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

Scripts:
- [scripts/predict_first18_2026.py](../scripts/predict_first18_2026.py) — 1X2 puro (hit-rate bruto)
- [scripts/predict_first18_ou_dc.py](../scripts/predict_first18_ou_dc.py) — OU2.5 e DC (hit-rate bruto)
- [scripts/predict_walkforward_ev.py](../scripts/predict_walkforward_ev.py) — EV/P&L simulado (aceita N de jogos como argumento; default 18, reexecutar com `40` na próxima marca)
- [scripts/predict_first18_teams.py](../scripts/predict_first18_teams.py) — quebra por time (gols esperados vs reais, Brier por time)

## Resultados

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

## Leitura

Ambos os mercados deram **EV negativo forward** nesta amostra — o oposto do
sinal esperado a partir do backtest (OU2.5 lá tinha ROI +7,9%). Achados:

- **Viés OU inverteu de direção**: 8 das 10 apostas de OU2.5 geradas foram
  **OVER** (modelo via mercado subestimando gols), oposto do padrão
  histórico onde o edge vinha do lado UNDER. A abertura de temporada 2026
  teve vários placares elásticos (5-1, 5-3, 4-0) que quebraram a calibração
  herdada de 2024/25.
- **DC com hit-rate razoável (54,5%) mas P&L negativo**: as odds de DC
  apostadas são curtas (1,08–2,3); com esse hit-rate o payoff médio das
  vitórias não cobre as derrotas — é preciso hit-rate bem mais alto
  (~70-75%+) pra essas odds darem ROI positivo.
- **N=18 é estatisticamente insuficiente** para refutar um backtest de
  1.165 jogos — é mais um sinal de atenção (early-season drift do Elo por
  transferências de janela) do que uma refutação.

## Compromisso de reexecução

**Reexecutar esta varredura na marca de 40 jogos disputados** (≈1 turno
completo), quando o IC95% do ROI/RPS já fecha o suficiente para separar
sinal de ruído — mesmo critério usado no veredito H4
(`docs/CONCLUSOES.md`, `data/h4_verdict.log`). Comando:

```
python scripts/predict_walkforward_ev.py 40
```

## Status operacional

Brasileirão entra em **modo de observação** (mesmo regime já aplicado ao
mercado cripto): sem intervenções ativas neste teste forward. O modo sombra
continua operando automaticamente (captura ~10h, settle ~23h,
`scripts/sombra_diaria.py`), acumulando dados sem necessidade de
intervenção manual até a próxima marca de reavaliação.
