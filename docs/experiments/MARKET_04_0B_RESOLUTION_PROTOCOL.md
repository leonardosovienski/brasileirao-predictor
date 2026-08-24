# MARKET-04 — Fase 0B, pré-checagem de resolução e cobertura

Revisão 2 congelada antes da primeira execução sobre a base operacional.

## Pergunta

O serving atual produz variação jogo a jogo suficiente em `P(Over 2.5)` e
`P(BTTS Sim)` para justificar o protocolo completo de ordenação contra o
mercado? Existem odds históricas completas de ambos os lados com cobertura
suficiente?

## Relógio e limites

- motor: serving walk-forward, ensemble xG desligado;
- desenvolvimento: 2021–2023;
- 2024: não é carregado antes de o gate de variância e cobertura passar;
- 2025 e 2026: proibidos ao runner;
- execução retrospectiva, read-only, sem picks e sem elegibilidade econômica.

## Gates declarados

O relatório preserva média, desvio-padrão populacional, variância, mínimo,
máximo, range, P10/P90 e histograma de largura 5pp. Os thresholds congelados
são `threshold_var.ou25=0,02` e `threshold_var.btts=0,02`.

Se `std(p_over25) < 0,02` **ou** `std(p_btts) < 0,02`, o veredito global é
`NO_GO_STRUCTURAL` e o runner termina sem carregar 2024.

O protocolo completo da 0B só pode prosseguir para mercados que também tenham
cobertura de odds completas `>= 80%`. Odds ausentes, não finitas ou `<= 1`
são inelegíveis. Falhar resolução produz `NO_GO_LOW_MODEL_RESOLUTION`; passar
resolução sem cobertura apenas registra insuficiência de dados, sem inferir
ausência de edge.

## Protocolo completo condicional

Somente se ambos os desvios e ambas as coberturas passarem, para OU2.5 e BTTS:

1. de-vig binário por normalização das probabilidades implícitas;
2. ambos os lados de cada mercado (Over/Under e Sim/Não), totalizando 10
   células por mercado nas faixas `<-5pp`, `-5–0pp`, `0–5pp`, `5–10pp`,
   `>=10pp`;
3. ROI flat diagnóstico e monotonicidade não decrescente em ao menos 3 faixas;
4. 1.000 permutações em `mês × faixa de |ΔElo efetivo|`;
5. power analysis para ROI alvo de 5%, poder 80% e alfa bilateral 5%;
6. desenvolvimento 2021–2023 e uma única validação 2024, com requisitos de
   poder derivados do desenvolvimento.

GO exige monotonicidade, amostra suficiente em todas as faixas observadas e
taxa nula de monotonicidade `<5%`. Nada nesta fase habilita capital.
