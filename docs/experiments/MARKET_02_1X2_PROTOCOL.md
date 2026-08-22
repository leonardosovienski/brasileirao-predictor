# MARKET-02 — residual multinomial 1X2 ancorado na abertura

Congelado em 2026-08-22 antes da primeira medição do candidato canônico.

## Hipótese e contraste

O mercado de abertura de-vigado por Shin é o offset. A única família de sinal
adicionada é a divergência logarítmica entre as probabilidades do serving e do
mercado nas três classes 1X2 (duas coordenadas independentes). Uma regressão
multinomial com referência na vitória do mandante aprende correções
regularizadas (`l2=5.0`). O fechamento nunca é feature; serve apenas como régua.

- Controle principal: abertura de-vigada por Shin.
- Tratamento: abertura + residual do serving.
- Referências diagnósticas: serving puro e fechamento de-vigado.
- Desenvolvimento: 2021–2023, walk-forward em blocos cronológicos de 100 jogos,
  treino mínimo de 300. Nenhum grid de hiperparâmetros.
- Validação única: ajuste em todo 2021–2023 e avaliação congelada em 2024.
- 2025: holdout intocado.
- 2026: diagnóstico somente se o candidato não degradar a validação.

Primária: RPS pareado tratamento−abertura. Guardrails: Brier 1X2 e log-loss.
GO técnico exige delta médio negativo em 2024 e nenhum IC95 de guardrail
inteiramente acima de zero. Accuracy é `DIAGNOSTIC_ONLY`, sempre com n e
cobertura. O teste não demonstra edge econômico e não habilita capital.

## Resultado e decisão

Desenvolvimento walk-forward (`n=622`): o residual já apresentou direção
desfavorável contra a abertura; no log-loss a degradação fechou acima de zero.

Validação congelada de 2024 (`n=340` de 380 previsões; cobertura de abertura
completa e válida no painel pareado 89,47%). O banco tem 378 linhas não nulas,
mas 38 contêm ao menos uma odd placeholder/suspensa (`<=1`) e são inelegíveis
para de-vig:

- RPS: `+0,002135`, IC95 `[+0,000588, +0,003649]`;
- Brier 1X2: `+0,004813`, IC95 `[+0,001115, +0,008436]`;
- log-loss: `+0,006542`, IC95 `[+0,000709, +0,012212]`;
- accuracy, apenas diagnóstico: abertura 52,06% → residual 51,18%;
- serving puro: 48,82%; fechamento, somente referência: 53,53%.

Decisão: **NO-GO comprovado**. O residual do serving acrescentado à abertura
piora as três perdas probabilísticas. Ele não será servido nem medido em 2026.
O resultado demonstra que, nesta especificação, a divergência Elo−mercado não
contém informação incremental útil. 2025 permaneceu intocado.

Diagnóstico separado, sem ajuste, da abertura pura em 2026 (`n=225`, cobertura
100%): accuracy 48,89%, RPS 0,200112, Brier 0,610527 e log-loss 1,013484. Ela
melhora o RPS do serving (0,208921), mas não chega perto de 60% de acerto.
