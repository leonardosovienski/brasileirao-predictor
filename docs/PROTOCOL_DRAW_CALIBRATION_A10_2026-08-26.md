# A10 — calibração específica de empate

Estado antes da execução: **pré-especificada para desenvolvimento/validação histórica**.

## Motivação

No painel de desenvolvimento, o serving não produz argmax de empate. O ensemble
xG aumenta a resolução dos empates, mas piora de forma ampla casa/fora. A hipótese
é que uma calibração binária estreita de `empate` possa corrigir parte desse erro
sem reintroduzir o ensemble.

## Intervenção congelada

1. Ajustar em 2021–2023 uma regressão logística com intercepto e slope:
   `logit(P(empate observado)) = a + b * logit(p_draw_serving)`.
2. Aplicar `p_draw_calibrado = logistic(a + b*logit(p_draw))`.
3. Redistribuir `1-p_draw_calibrado` entre casa e fora preservando exatamente a
   razão original `p_home:p_away`.
4. Não ajustar threshold, regularização, filtro ou regra categórica.

## Avaliação única

- Validação: 2024.
- Primária: Brier binário empate/não-empate.
- Guardrails: RPS, Brier 1X2 e log loss 1X2, todos pareados.
- Diagnósticos: número/direção de flips do argmax e matriz de confusão.
- Critério de candidato: melhora na primária e nenhum guardrail pior; ICs são
  reportados, não usados para redefinir a intervenção.
- 2025 e 2026 não participam de ajuste, escolha ou avaliação.

