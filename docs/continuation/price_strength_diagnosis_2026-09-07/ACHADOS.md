# Diagnóstico dos erros e acertos do xG em 2025

Decomposição descritiva dos resultados já congelados e auditados. Nenhuma nova previsão, aposta, calibração ou regra foi calculada. As apostas citadas são pagamentos hipotéticos em odds agregadas retrospectivas.

O calibrado principal terminou pior financeiramente que o xG bruto. A decomposição abaixo mostra quais decisões mudaram; ela não prova que a calibração causou o placar de cada jogo nem autoriza escolher uma política pelos resultados vistos.

| Modelo | Apostas | Acertos/erros | Saldo líquido | ROI | p prevista | Taxa real | p mercado da seleção |
| --- | --- | --- | --- | --- | --- | --- | --- |
| xg_calibrated_primary | 312 | 83/229 | -68.700u | -22.02% | 37.51% | 26.60% | 28.53% |
| xg_raw_diagnostic | 340 | 102/238 | -27.967u | -8.23% | 37.32% | 30.00% | 27.89% |
| old_raw_frozen_2024 | 297 | 85/212 | -39.641u | -13.35% | 37.35% | 28.62% | 28.09% |
| market_proportional_devig | 0 | 0/0 | +0.000u | — | — | — | — |

## O que mudou ao aplicar a calibração

| Transição | Jogos | Saldo raw | Saldo calibrado | Diferença cal−raw |
| --- | --- | --- | --- | --- |
| same_bet | 258 | -46.232u | -46.232u | +0.000u |
| changed_bet | 44 | +2.945u | -22.795u | -25.740u |
| raw_only | 38 | +15.320u | +0.000u | -15.320u |
| calibrated_only | 10 | +0.000u | +0.327u | +0.327u |
| neither | 18 | +0.000u | +0.000u | +0.000u |

A soma exata das entradas, saídas e trocas é -40.733u. Apostas mantidas recebem o mesmo pagamento, mesmo quando a probabilidade mudou.

Escalas congeladas em 2024: mandante 0.998135; visitante 0.911659. Isso altera as taxas de gols e pode alterar a ordenação das apostas; o ajuste não foi escolhido usando estes resultados de 2025.

| Taxa | Lambda raw média | Lambda calibrada média | Gols observados médios |
| --- | --- | --- | --- |
| home | 1.4903 | 1.4875 | 1.5190 |
| away | 1.0802 | 0.9848 | 0.9973 |

## xg_calibrated_primary

Todos os mercados e lados aparecem, inclusive os sem apostas.

| Mercado/lado | n | Acertos | Erros | Saldo | ROI | p prevista | Taxa real | p mercado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1x2/home | 99 | 36 | 63 | -5.050u | -5.10% | 46.43% | 36.36% | 35.62% |
| 1x2/draw | 9 | 3 | 6 | +5.403u | 60.03% | 26.69% | 33.33% | 18.52% |
| 1x2/away | 125 | 13 | 112 | -59.350u | -47.48% | 23.54% | 10.40% | 16.04% |
| ou25/over | 65 | 23 | 42 | -11.275u | -17.35% | 48.38% | 35.38% | 39.01% |
| ou25/under | 6 | 4 | 2 | +1.157u | 19.28% | 58.36% | 66.67% | 50.10% |
| btts/yes | 3 | 2 | 1 | +1.565u | 52.17% | 49.11% | 66.67% | 40.89% |
| btts/no | 5 | 2 | 3 | -1.150u | -23.00% | 56.60% | 40.00% | 48.53% |

Faixas fixadas no pedido. Intervalos fechados à esquerda e abertos à direita; a última faixa de probabilidade inclui 1.

| Probabilidade | n | Acertos/erros | Saldo | p prevista | Taxa real | p mercado |
| --- | --- | --- | --- | --- | --- | --- |
| 0-.2 | 20 | 1/19 | -12.900u | 17.82% | 5.00% | 11.14% |
| .2-.4 | 130 | 19/111 | -41.842u | 26.17% | 14.62% | 18.09% |
| .4-.6 | 154 | 58/96 | -14.935u | 48.39% | 37.66% | 38.42% |
| .6-.8 | 8 | 5/3 | +0.977u | 61.71% | 62.50% | 51.02% |
| .8-1 | 0 | 0/0 | +0.000u | — | — | — |

| Odd | n | Acertos/erros | Saldo | p prevista | Taxa real | p mercado |
| --- | --- | --- | --- | --- | --- | --- |
| 1-2 | 15 | 9/6 | +1.347u | 59.29% | 60.00% | 50.68% |
| 2-3 | 130 | 47/83 | -20.540u | 48.48% | 36.15% | 39.02% |
| 3-5 | 63 | 17/46 | -1.177u | 34.47% | 26.98% | 24.74% |
| 5+ | 104 | 10/94 | -48.330u | 22.51% | 9.62% | 14.51% |

Acertos e erros separados: as taxas reais de 100% e 0% são consequência dessa separação, não evidência de calibração.

| Grupo | n | Saldo | p prevista média | p mercado média |
| --- | --- | --- | --- | --- |
| wins | 83 | +164.880u | 44.49% | 35.40% |
| losses | 229 | -233.580u | 34.98% | 26.04% |

Os cinco maiores acertos somam +26.400u, ou 16.01% dos pagamentos líquidos positivos. Todas as 229 derrotas custam exatamente 1,02u; não existe uma derrota individual mais cara neste desenho.

| Cinco maiores acertos | Seleção | Odd | p modelo | p mercado | Saldo |
| --- | --- | --- | --- | --- | --- |
| Cruzeiro × Ceará (13472870) | 1x2/away | 7.5 | 19.97% | 12.66% | +6.480u |
| Palmeiras × Bahia (13473390) | 1x2/away | 6.25 | 21.85% | 15.25% | +5.230u |
| Vasco da Gama × Juventude (13472744) | 1x2/away | 6.25 | 22.12% | 15.13% | +5.230u |
| Atlético Mineiro × Grêmio (13472902) | 1x2/away | 5.75 | 20.12% | 16.62% | +4.730u |
| São Paulo × Red Bull Bragantino (13472752) | 1x2/away | 5.75 | 25.54% | 16.60% | +4.730u |

## xg_raw_diagnostic

Todos os mercados e lados aparecem, inclusive os sem apostas.

| Mercado/lado | n | Acertos | Erros | Saldo | ROI | p prevista | Taxa real | p mercado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1x2/home | 79 | 33 | 46 | +10.970u | 13.89% | 44.32% | 41.77% | 33.97% |
| 1x2/draw | 14 | 4 | 10 | +5.803u | 41.45% | 25.62% | 28.57% | 17.60% |
| 1x2/away | 147 | 21 | 126 | -46.640u | -31.73% | 26.17% | 14.29% | 17.49% |
| ou25/over | 91 | 39 | 52 | +0.255u | 0.28% | 49.39% | 42.86% | 39.30% |
| ou25/under | 2 | 2 | 0 | +1.660u | 83.00% | 60.35% | 100.00% | 51.32% |
| btts/yes | 6 | 2 | 4 | -0.995u | -16.58% | 52.02% | 33.33% | 42.64% |
| btts/no | 1 | 1 | 0 | +0.980u | 98.00% | 54.66% | 100.00% | 46.67% |

Faixas fixadas no pedido. Intervalos fechados à esquerda e abertos à direita; a última faixa de probabilidade inclui 1.

| Probabilidade | n | Acertos/erros | Saldo | p prevista | Taxa real | p mercado |
| --- | --- | --- | --- | --- | --- | --- |
| 0-.2 | 11 | 1/10 | -4.970u | 18.07% | 9.09% | 10.57% |
| .2-.4 | 169 | 28/141 | -38.847u | 27.69% | 16.57% | 18.86% |
| .4-.6 | 154 | 70/84 | +16.610u | 48.34% | 45.45% | 38.19% |
| .6-.8 | 6 | 3/3 | -0.760u | 61.19% | 50.00% | 49.81% |
| .8-1 | 0 | 0/0 | +0.000u | — | — | — |

| Odd | n | Acertos/erros | Saldo | p prevista | Taxa real | p mercado |
| --- | --- | --- | --- | --- | --- | --- |
| 1-2 | 9 | 6/3 | +1.830u | 59.93% | 66.67% | 51.02% |
| 2-3 | 136 | 58/78 | +1.320u | 48.63% | 42.65% | 38.79% |
| 3-5 | 82 | 24/58 | +3.893u | 34.01% | 29.27% | 24.80% |
| 5+ | 113 | 14/99 | -35.010u | 24.32% | 12.39% | 15.17% |

Acertos e erros separados: as taxas reais de 100% e 0% são consequência dessa separação, não evidência de calibração.

| Grupo | n | Saldo | p prevista média | p mercado média |
| --- | --- | --- | --- | --- |
| wins | 102 | +214.793u | 43.10% | 33.91% |
| losses | 238 | -242.760u | 34.85% | 25.31% |

Os cinco maiores acertos somam +26.900u, ou 12.52% dos pagamentos líquidos positivos. Todas as 238 derrotas custam exatamente 1,02u; não existe uma derrota individual mais cara neste desenho.

| Cinco maiores acertos | Seleção | Odd | p modelo | p mercado | Saldo |
| --- | --- | --- | --- | --- | --- |
| Cruzeiro × Ceará (13472870) | 1x2/away | 7.5 | 22.01% | 12.66% | +6.480u |
| Palmeiras × Bahia (13473390) | 1x2/away | 6.25 | 24.05% | 15.25% | +5.230u |
| Santos × Vitória (13472825) | 1x2/away | 6.25 | 18.03% | 15.19% | +5.230u |
| Vasco da Gama × Juventude (13472744) | 1x2/away | 6.25 | 24.35% | 15.13% | +5.230u |
| Atlético Mineiro × Grêmio (13472902) | 1x2/away | 5.75 | 22.17% | 16.62% | +4.730u |

## old_raw_frozen_2024

Todos os mercados e lados aparecem, inclusive os sem apostas.

| Mercado/lado | n | Acertos | Erros | Saldo | ROI | p prevista | Taxa real | p mercado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1x2/home | 92 | 39 | 53 | +13.943u | 15.16% | 46.96% | 42.39% | 36.07% |
| 1x2/draw | 11 | 3 | 8 | +2.263u | 20.57% | 27.81% | 27.27% | 19.48% |
| 1x2/away | 142 | 20 | 122 | -57.807u | -40.71% | 27.99% | 14.08% | 19.43% |
| ou25/over | 33 | 12 | 21 | -0.385u | -1.17% | 43.02% | 36.36% | 34.83% |
| ou25/under | 12 | 7 | 5 | +1.235u | 10.29% | 57.98% | 58.33% | 47.75% |
| btts/yes | 1 | 1 | 0 | +1.230u | 123.00% | 47.13% | 100.00% | 41.11% |
| btts/no | 6 | 3 | 3 | -0.120u | -2.00% | 54.77% | 50.00% | 47.71% |

Faixas fixadas no pedido. Intervalos fechados à esquerda e abertos à direita; a última faixa de probabilidade inclui 1.

| Probabilidade | n | Acertos/erros | Saldo | p prevista | Taxa real | p mercado |
| --- | --- | --- | --- | --- | --- | --- |
| 0-.2 | 24 | 0/24 | -24.480u | 16.18% | 0.00% | 10.35% |
| .2-.4 | 139 | 27/112 | -17.031u | 29.50% | 19.42% | 20.33% |
| .4-.6 | 121 | 50/71 | +0.460u | 47.62% | 41.32% | 37.90% |
| .6-.8 | 13 | 8/5 | +1.410u | 64.80% | 61.54% | 52.48% |
| .8-1 | 0 | 0/0 | +0.000u | — | — | — |

| Odd | n | Acertos/erros | Saldo | p prevista | Taxa real | p mercado |
| --- | --- | --- | --- | --- | --- | --- |
| 1-2 | 23 | 14/9 | +2.210u | 60.75% | 60.87% | 51.55% |
| 2-3 | 97 | 37/60 | -8.760u | 47.44% | 38.14% | 38.13% |
| 3-5 | 89 | 25/64 | +4.169u | 34.28% | 28.09% | 24.83% |
| 5+ | 88 | 9/79 | -37.260u | 23.22% | 10.23% | 14.18% |

Acertos e erros separados: as taxas reais de 100% e 0% são consequência dessa separação, não evidência de calibração.

| Grupo | n | Saldo | p prevista média | p mercado média |
| --- | --- | --- | --- | --- |
| wins | 85 | +176.599u | 44.25% | 34.74% |
| losses | 212 | -216.240u | 34.58% | 25.42% |

Os cinco maiores acertos somam +26.150u, ou 14.81% dos pagamentos líquidos positivos. Todas as 212 derrotas custam exatamente 1,02u; não existe uma derrota individual mais cara neste desenho.

| Cinco maiores acertos | Seleção | Odd | p modelo | p mercado | Saldo |
| --- | --- | --- | --- | --- | --- |
| Cruzeiro × Ceará (13472870) | 1x2/away | 7.5 | 22.60% | 12.66% | +6.480u |
| Vasco da Gama × Juventude (13472744) | 1x2/away | 6.25 | 22.96% | 15.13% | +5.230u |
| Cruzeiro × Santos (13472891) | 1x2/away | 6.0 | 22.56% | 15.75% | +4.980u |
| Atlético Mineiro × Grêmio (13472902) | 1x2/away | 5.75 | 29.45% | 16.62% | +4.730u |
| Bahia × Flamengo (13472796) | 1x2/home | 5.75 | 31.09% | 16.62% | +4.730u |

## Incerteza já publicada

Os intervalos abaixo são os mesmos da avaliação congelada; não foram recalculados para procurar subgrupos positivos.

| Comparação | Δ pagamento por jogo | IC95 semanal descritivo |
| --- | --- | --- |
| xg_calibrated_primary − old_raw_frozen_2024 | -0.0790u | [-0.2244; +0.0551]u |
| xg_calibrated_primary − market_proportional_devig | -0.1867u | [-0.3309; -0.0354]u |
| xg_raw_diagnostic − old_raw_frozen_2024 | +0.0317u | [-0.1131; +0.1728]u |
| xg_raw_diagnostic − market_proportional_devig | -0.0760u | [-0.2254; +0.0695]u |

## Implicações para uma correção futura

A diferença entre probabilidade prevista, mercado e frequência nas seleções deve ser examinada junto das perdas probabilísticas de todos os jogos. Melhorar Brier médio e melhorar o ranking das apostas são objetivos distintos. As tabelas identificam concentração e desvios descritivos; faixas positivas não são recomendações de filtro.

Convém verificar a especificação da calibração de taxas, sua função objetivo e como a redução de gols visitantes desloca home/draw/away, under e ambas não. Qualquer alteração exige outro candidato declarado e escolha com dados anteriores à avaliação; não ajustar escalas ou excluir mercados porque perderam nesta amostra.

Verificar também a proveniência do xG e das odds: atraso de 48h é uma hipótese, e preços agregados não atestam casa nem aceitação. O comparador entre casas permanece sem teste econômico com capturas elegíveis.

O JSON contém todas as transições por evento, os cinco maiores efeitos positivos e negativos das trocas, calibração por classe, contagens de deslocamentos de probabilidade e estratos completos. Esses registros permitem reproduzir a decomposição sem recomputar o modelo.

## Limitações

- 2025 já foi observado e explorado; este diagnóstico posterior não cria holdout independente.
- As faixas e comparações são descritivas, sem intervalos novos por subgrupo nem correção por buscas anteriores.
- Frequências condicionadas a acerto ou erro são 1 ou 0 por construção; não identificam calibração.
- Um acerto não prova qualidade da previsão e uma derrota não identifica a causa do erro.
- Os pagamentos usam 1u e custo fixo 0,02u; odds retrospectivas agregadas não comprovam execução real.
- Disponibilidade do xG após 48h é assumida, sem trilha histórica de publicação ou revisão.
- Comparar candidatos muda a política completa; o ganho ou a perda não identifica isoladamente o efeito causal do xG.
- Intervalos semanais publicados são descritivos e não corrigem busca anterior nem incerteza do ajuste.
- Não selecionar mercados, faixas, escalas ou limiares a partir dos saldos aqui exibidos.
