# MARKET-03 — ordenação do residual modelo × mercado

Congelado em 2026-08-24 antes da primeira execução do runner canônico.

## Pergunta

A divergência `p_modelo - p_mercado_sem_vig` ordena resultados fora da
amostra, especialmente para empate, ou o serving é apenas ruído adicional em
relação ao mercado?

Este é um diagnóstico esportivo/econômico exploratório. As odds históricas são
o agregado sem bookmaker nomeado do SofaScore e têm executabilidade
desconhecida. ROI, PSR e DSR produzidos aqui não constituem evidência econômica.

## Relógio e amostras

- motor: serving walk-forward, ensemble xG desligado;
- desenvolvimento: 2021–2023;
- validação única: 2024;
- 2025: holdout selado e proibido ao runner;
- 2026: não é lido pelo runner; somente diagnóstico posterior de regra já
  congelada poderia consumi-lo;
- jogos simultâneos permanecem protegidos pela guarda de kickoff;
- fechamento agregado nunca entra como feature do motor; é somente régua.

## Grade declarada e multiplicidade

As 60 células são declaradas antes da medição:

- seleções: `away`, `draw`, `home` (3);
- divergência absoluta em probabilidade: `<−5pp`, `−5–0pp`, `0–5pp`,
  `5–10pp`, `≥10pp` (5);
- odd decimal: `1–2`, `2–3`, `3–5`, `≥5` (4).

O DSR usa o ledger histórico mais estas 60 tentativas. Não se aplica desconto
por correlação: `effective_trials_policy=CONSERVATIVE_NO_CORRELATION_DISCOUNT`.
Reduzir esse denominador depois de observar resultados é proibido.

## Métricas

Primárias pareadas no painel completo: RPS e Brier 1X2 do serving contra o
mercado Shin sem vig. Log loss é guardrail.

Por célula: `n`, coverage, probabilidades médias, frequência observada, Brier
binário modelo/mercado, ROI flat diagnóstico, PSR, DSR e amostra aproximada
necessária para detectar ROI de 5% com poder 80% e alfa bilateral 5%. Accuracy
não decide nada.

## Controle negativo

Os resultados são permutados dentro de `mês × faixa de |ΔElo efetivo|`.
Previsões, odds, calendário e composição aproximada de força permanecem no
lugar. O teste mede quantas permutações também produzem ROI monotônico do
empate através das faixas de divergência.

## Encerramento

A hipótese atual só permanece viva se, na validação 2024:

1. o ROI diagnóstico do empate for não decrescente em pelo menos três faixas;
2. todas as faixas observadas atingirem a amostra calculada para o efeito-alvo;
3. menos de 5% das permutações reproduzirem monotonicidade.

Falhar qualquer condição produz `NO_GO_CURRENT_RESIDUAL`. A hipótese não pode
renascer por novos thresholds nas mesmas probabilidades; exige mecanismo novo
ou informação PIT nova. Mesmo um resultado positivo permite apenas desenhar
replicação prospectiva com bookmaker nomeado. Capital permanece desabilitado.

## Resultado da execução congelada

Executado em 2026-08-24 após o registro acima:

- desenvolvimento: `n=940`, coverage 100%; mercado venceu o serving em RPS
  (`0,203666` contra `0,212817`); ROI de empate não monotônico;
- validação 2024: `n=378/380`, coverage 99,47%; mercado venceu em RPS
  (`0,198260` contra `0,214532`), Brier e log loss;
- empate em 2024: ROI diagnóstico por divergência `<−5pp`, `−5–0pp`, `0–5pp`,
  `5–10pp` = `−43,95%`, `+8,66%`, `−38,62%`, `−9,09%`;
- monotonicidade: ausente em desenvolvimento e validação;
- controle nulo 2024: 255/1.000 permutações também foram monotônicas (25,5%);
- amostras de poder: não atingidas; o menor requisito estimado por faixa foi
  6.527, refletindo a alta variância de apostas em empate.

Veredito: **`NO_GO_CURRENT_RESIDUAL`**. A divergência de empate do serving
atual não ordena valor fora da amostra. Não executar 2026 para tentar resgatar
a hipótese. Reabertura exige mecanismo novo ou informação PIT nova.
