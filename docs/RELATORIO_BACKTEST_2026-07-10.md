# Relatório de Backtest Walk-Forward — Brasileirão Série A (2026-07-10)

## Dataset

| Item | Valor |
|---|---|
| Fonte | Sofascore (ut_id 325), coletado 2026-07-10 na máquina do operador |
| Temporadas | 2024 (388), 2025 (393), 2026 parcial (384 eventos, 156 jogados) |
| `sofascore_matches` | 1.165 eventos, com odds abertura+fechamento, HT, stats, xG |
| `matches` (espelho) | 937 jogos disputados + 228 fixtures 2026 |
| Calibração serving | a=0.199, b=0.708, α=0.0006, ρ=0.014 (937 jogos) |

## Metodologia

Walk-forward por blocos de **19 rodadas (190 jogos ≈ 1 turno)**, 4 blocos
testados; o 1º turno de 2024 é burn-in e nunca é testado. Parâmetros do
Poisson recalibrados ANTES de cada bloco só com jogos passados; Elo forward
por construção. Funil pré-registrado: edge vs preço em [2%, 15%], stake fixo
1u, preço de abertura quando existe (`bet_at='open'`), CLV = odd pactuada ×
Shin do fechamento − 1. Bootstrap por cluster de jogo (over+under do mesmo
jogo não são independentes). Governança: harness de controle positivo PASSOU
(edge sintético λ×1,3 detectado; ruído rejeitado) ANTES do pré-registro de
H1/H2; DSR descontado pelas 2 tentativas do registro.

## Resultados por mercado (1.673 apostas no funil)

| Mercado | n | Acerto | ROI | CLV open |
|---|---:|---:|---:|---:|
| **OU 2.5 (H1)** | **455** | **49,7%** | **+7,9%** | **+19,55%** |
| 1X2 | 474 | 26,2% | −15,4% | −6,09% |
| Dupla chance | 273 | 49,1% | −13,1% | −6,97% |
| BTTS | 102 | 48,0% | +6,7% | −0,80% |
| OU 1.5 | 186 | 46,8% | −8,6% | −1,73% |
| OU 3.5 | 146 | 47,3% | +6,2% | −1,26% |
| OU 4.5 / 5.5 / 0.5 | 37 | — | ~0 | negativo |

A lição da Copa se REPRODUZIU em liga: 1X2/DC sangram (viés de achatamento
estrutural); a única população com CLV positivo forte é OU 2.5.

## H1 — OU 2.5, edge 2–15% (pré-registrada)

| Critério | Medido | Gate | Passa? |
|---|---|---|---|
| PSR | 0,94 | ≥ 0,80 | ✅ |
| IC95 do pnl médio (cluster) | [−0,022, +0,172] | lower > 0 | ❌ |
| DSR (N=2 tentativas) | 0,94 | ≥ 0,95 | ❌ (na trave) |

**VEREDITO: NO-GO** — nenhuma aposta real.

Sharpe por aposta observado: 0,0722 (gravado no trials.json).

### Leitura e investigação (mandato do 4.3)

- O **CLV open +19,55% em 455 apostas** é sinal de PREÇO real e forte — o
  modelo compra sistematicamente melhor que o fechamento na linha de gols,
  como na Copa (+16,11%). O que falha é a conversão em **pnl com IC fechado**:
  variância de resultado binário em ~500 amostras ainda engole o ROI de +7,9%.
- Caminhos para a reavaliação (nesta ordem, sem tocar no funil pré-registrado):
  1. **Mais dados**: ingerir 2023 (season_id 48982) → +380 jogos, +2 blocos.
  2. Rodar o restante de 2026 em modo SOMBRA (registro sem dinheiro) — cada
     rodada adiciona ~10 jogos à população out-of-sample.
  3. Se o IC fechar com N maior, registrar como nova leitura da MESMA H1
     (params idênticos) e reavaliar o gate.
- O DSR 0,94 está a 0,01 do gate com N=2 tentativas — não caçar o gate
  variando configuração (cada variação é tentativa N+1 e deflaciona mais).

## H2 — Picks de período 1T, confiança ≥60% (pré-registrada)

**n = 1.493 picks | acerto real 79,0% vs confiança média 79,8% → VALIDADA.**
Calibração quase perfeita (gap de 0,8pp). Segue **informativa**: não há odds
de período na base → sem ROI/CLV possível; uso permitido igual ao da Copa
(registro e stake reduzido opt-in via `BETLOG_MAX_INFO_STAKE`), nunca como
população principal.

## Adendo 2026-07-11 — Estratificação do CLV (população H1, 455 apostas)

O CLV +19,55% NÃO é uniforme:

| Estrato | n | ROI | CLV | Bate fechamento |
|---|---:|---:|---:|---:|
| **under** | 414 | +6,8% | **+21,5%** | 88% |
| over | 41 | +19,3% | −0,5% | 46% |
| edge 2–5% | 91 | **−7,3%** | −1,2% | 47% |
| edge 5–10% | 184 | +5,6% | +14,8% | 87% |
| **edge 10–15%** | 180 | +17,9% | **+34,9%** | **99%** |

Por tempo: CLV positivo nos 4 blocos (+14,9% a +26,5%) e nas 3 temporadas —
estável, não é sorte de um período. Por odd: concentrado na faixa 2,10–2,60.

**Leitura**: as casas abrem a linha de gols "genérica" e o mercado aperta
para o UNDER até o fechamento; o modelo, calibrado numa liga de poucos gols,
enxerga isso na abertura. A faixa 2–5% de edge é ruído pagando vig (ROI
negativo) — o sinal vive em 5–15%. **A pergunta que o backtest não responde:
o `initialFractionalValue` é um preço capturável na vida real, ou
abertura-fantasma?** É exatamente o que a H3 mede.

### H3 — modo sombra (registrada em 2026-07-11)

`h3-ou25-sombra-2026` no TrialRegistry: mesmo funil pré-registrado (SEM mudar
gatilho — otimizar sub-janela seria tentativa N+1), captura de odds correntes
pré-apito via `scripts/sombra.py --capture`, settle pós-jogo com CLV vs
fechamento. **Decisão com n ≥ 100 liquidados**: CLV IC95 > 0 e ROI aceitável
→ nova leitura de H1 com N ampliado; senão, abertura-fantasma documentada e
linha encerrada. Primeiro pick já capturado (Botafogo × Santos 16/07, under
2.5 @1,95). Relatório estratificado por seleção/faixa é observacional.

## Adendo 2026-07-17 — auditoria da FONTE das odds de abertura

Investigação disparada pela observação de que, nos jogos de 17/07, as odds
de abertura eram o **espelho exato** das odds vivas (Mirassol×Grêmio: open
over/under 1,60/2,30 vs corrente 2,30/1,60 — constante em 10 snapshots ao
longo de 6 dias). O parser foi **inocentado**: abertura
(`initialFractionalValue`) e preço atual (`fractionalValue`) são lidos do
MESMO objeto `choice` casado por nome — troca por parsing é impossível.
A inversão vem da própria fonte. Quantificação nos jogos disputados com
ambos os preços:

| Ano | n | Espelho EXATO | Par de abertura mais perto do FECHAMENTO INVERTIDO | Over favorito na abertura | Over favorito no fechamento |
|---|---:|---:|---:|---:|---:|
| 2024 | 246 | 6% | 60% | 64% | 14% |
| 2025 | 374 | 8% | 59% | 61% | 12% |
| 2026 | 177 | 11% | 60% | 66% | 20% |

**Leitura**: o `initialFractionalValue` do Sofascore favorece o OVER em
~64% das aberturas, enquanto o fechamento favorece o UNDER em ~86% — e em
60% dos jogos o par de abertura se parece mais com o fechamento INVERTIDO
do que com ele mesmo. Isso é mais compatível com **abertura-template
(fantasma)** do que com drift de mercado real. Implicação direta: o CLV
open +19,55% da H1 (apostas a preço de abertura, 88% dos unders "batendo o
fechamento") pode ser em grande parte artefato dessa abertura não
negociável — exatamente o cenário que a H3 foi registrada para testar.
**As populações H3/H5 usam odds CORRENTES** (colunas atualizadas a cada
ingest, corroboradas por `odds_snapshots` com timestamp) e permanecem a
medição válida. Nenhuma mudança de config; a decisão continua com o gate
pré-registrado das sombras.

## Plano de operação — retomada do Brasileirão 2026

A Série A retoma em **16-17/07** (5 jogos atrasados) e a rodada cheia começa
em **21/07** (Atlético-MG×Bahia; 23/07 concentra 5 jogos). 228 fixtures já
estão no banco. **Por força do NO-GO, a operação é 100% MODO SOMBRA** (zero
dinheiro real) até a reavaliação:

1. **Pré-rodada (D-1)**: `python -m src.ingest_sofascore` (atualiza odds das
   fixtures) → `python scripts/sync_matches_from_sofascore.py` →
   `python -m src.cron_update_models`.
2. **Conferência de preço**: `python scripts/odds_shop.py --from-file <snap>`
   (validado hoje com snapshot de teste) ou online com `ODDS_API_KEY`
   (sport key `soccer_brazil_campeonato` — confirmar no /v4/sports na 1ª
   chamada real).
3. **Previsão + registro obrigatório**: `python scripts/prever.py HOME AWAY
   --mando` (log append-only carimba antes do apito).
4. **Registro sombra**: apostas OU2.5 que passarem no funil entram no
   `bet_log` com stake informativo (trava `BETLOG_MAX_INFO_STAKE`), nunca
   dinheiro.
5. **Pós-jogo**: `python -m src.bet_log settle HOME AWAY H A --ht H-A` +
   `python -m src.settle` (aferição do palpite).
6. **A cada rodada**: reexecutar 1 e acumular população out-of-sample; ao
   fim de cada mês, reavaliar H1 com o N ampliado.

## Estado da suíte

**241 testes verdes** | `ci_check.py` **5/5 barreiras verdes** (P12, P3,
smokes Flamengo×Palmeiras pré-jogo e live). Vendor core v1.1.0 em sincronia.
