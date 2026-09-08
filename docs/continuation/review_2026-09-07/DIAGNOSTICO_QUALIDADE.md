# Qualidade preditiva do replay congelado

Diagnóstico adicional dos mesmos resultados já derivados. Nenhum modelo, peso ou regra foi ajustado.

Menor Brier e menor log-loss indicam previsões melhores. Os quatro previsores são comparados nos mesmos jogos em cada mercado e turno.

A climatologia usa somente os 1.520 jogos de 2021–2024. O Brier de 1X2 soma as três classes; o dos mercados binários usa a classe positiva. Não se devem comparar os números brutos de Brier entre 1X2 e os mercados binários.

## Primeiro turno

Jogos concluídos: 190 de 190 oficiais.

| Mercado | Jogos / rodadas | Previsor | Brier | Log-loss |
|---|---:|---|---:|---:|
| 1x2 | 190 / 19 | raw | 0.614227 | 1.025358 |
| 1x2 | 190 / 19 | calibrated | 0.591774 | 0.990462 |
| 1x2 | 190 / 19 | market_devig | 0.591774 | 0.990462 |
| 1x2 | 190 / 19 | climatology_train | 0.631233 | 1.048244 |
| ou25 | 190 / 19 | raw | 0.256290 | 0.705892 |
| ou25 | 190 / 19 | calibrated | 0.250913 | 0.694954 |
| ou25 | 190 / 19 | market_devig | 0.250913 | 0.694954 |
| ou25 | 190 / 19 | climatology_train | 0.254475 | 0.702164 |
| btts | 190 / 19 | raw | 0.256458 | 0.706089 |
| btts | 190 / 19 | calibrated | 0.255308 | 0.703778 |
| btts | 190 / 19 | market_devig | 0.247462 | 0.688077 |
| btts | 190 / 19 | climatology_train | 0.251773 | 0.696693 |

Diferença contra o mercado sem margem: valor positivo significa erro maior. IC95 por reamostragem pareada de rodadas.

| Mercado | Previsor − mercado | Δ Brier [IC95] | Δ log-loss [IC95] |
|---|---|---:|---:|
| 1x2 | raw | +0.022453 [-0.002776, +0.047228] | +0.034895 [-0.001197, +0.070539] |
| 1x2 | calibrated | +0.000000 [+0.000000, +0.000000] | +0.000000 [+0.000000, +0.000000] |
| ou25 | raw | +0.005377 [-0.002937, +0.013616] | +0.010937 [-0.006032, +0.027580] |
| ou25 | calibrated | +0.000000 [+0.000000, +0.000000] | +0.000000 [-0.000000, +0.000000] |
| btts | raw | +0.008996 [+0.005123, +0.013047] | +0.018012 [+0.010243, +0.026173] |
| btts | calibrated | +0.007847 [+0.004379, +0.011472] | +0.015701 [+0.008758, +0.023001] |

## Segundo turno disponível

Jogos concluídos: 58 de 190 oficiais.

| Mercado | Jogos / rodadas | Previsor | Brier | Log-loss |
|---|---:|---|---:|---:|
| 1x2 | 58 / 7 | raw | 0.721883 | 1.177102 |
| 1x2 | 58 / 7 | calibrated | 0.662413 | 1.083885 |
| 1x2 | 58 / 7 | market_devig | 0.662413 | 1.083885 |
| 1x2 | 58 / 7 | climatology_train | 0.665309 | 1.095419 |
| ou25 | 58 / 7 | raw | 0.253776 | 0.700845 |
| ou25 | 58 / 7 | calibrated | 0.252870 | 0.698992 |
| ou25 | 58 / 7 | market_devig | 0.252870 | 0.698992 |
| ou25 | 58 / 7 | climatology_train | 0.251692 | 0.696568 |
| btts | 58 / 7 | raw | 0.259979 | 0.713171 |
| btts | 58 / 7 | calibrated | 0.258882 | 0.710957 |
| btts | 58 / 7 | market_devig | 0.251366 | 0.695882 |
| btts | 58 / 7 | climatology_train | 0.252289 | 0.697725 |

Diferença contra o mercado sem margem: valor positivo significa erro maior. IC95 por reamostragem pareada de rodadas.

| Mercado | Previsor − mercado | Δ Brier [IC95] | Δ log-loss [IC95] |
|---|---|---:|---:|
| 1x2 | raw | +0.059470 [-0.001205, +0.112524] | +0.093216 [+0.010997, +0.170731] |
| 1x2 | calibrated | +0.000000 [+0.000000, +0.000000] | +0.000000 [+0.000000, +0.000000] |
| ou25 | raw | +0.000906 [-0.016960, +0.022928] | +0.001853 [-0.034360, +0.046461] |
| ou25 | calibrated | +0.000000 [+0.000000, +0.000000] | +0.000000 [+0.000000, +0.000000] |
| btts | raw | +0.008613 [+0.004438, +0.015491] | +0.017289 [+0.008883, +0.031108] |
| btts | calibrated | +0.007516 [+0.003756, +0.013669] | +0.015075 [+0.007471, +0.027406] |

## Interpretação e limites

Os intervalos usam 2.000 reamostragens de rodadas oficiais completas observadas, seed 20260909 com deslocamento fixo por painel. Preservam os mesmos eventos entre previsores e ponderam a média pelo número de jogos. Não há ajuste por múltiplas comparações nem incerteza do treino/calibração dentro desses intervalos.

O segundo turno tem poucas rodadas disponíveis; seus intervalos são especialmente instáveis. Jogos futuros e placares ausentes não foram tratados como perdas zero. As rodadas podem permanecer correlacionadas entre si e nem sempre representam a mesma semana devido a adiamentos.

O modelo e o Elo ficaram congelados no fim de 2024. Esta execução mede esse candidato fixo, e não reproduz a atualização contínua do serving. As odds são retrospectivas, sem prova de disponibilidade pré-jogo; o mercado sem margem também não é probabilidade verdadeira. Qualidade probabilística não comprova valor econômico ou execução.

O histórico já tinha sido explorado, e este diagnóstico é posterior aos resultados econômicos. Todos os mercados e comparadores pré-definidos estão publicados, inclusive os que pioraram. Nenhum resultado permite reivindicar teste cego, promoção de estratégia ou lucro futuro.
