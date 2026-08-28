# Auditoria e versão 2.0 — recomendação OU2.5

Data da revalidação: 2026-08-27.

## Decisão

O estado correto do filtro é **NO_BET**. Capital continua desabilitado e a força da indicação fica limitada a 40/100 até existir evidência prospectiva A1. Não foi encontrado filtro retrospectivo com amostra, limite inferior de retorno, CLV e estabilidade suficientes.

“Versão 2.0” neste documento significa o protocolo/filtro OU2.5, não uma alegação de que todo o aplicativo mudou de versão principal.

## O que foi revalidado

- Backfill de 1.140 partidas: 380 por temporada em 2021, 2022 e 2023; zero jogos sem preço e zero não conciliados.
- Replay temporal aninhado: parâmetros escolhidos somente no passado de cada fold e usados, sem retuning, no bloco seguinte.
- Grade fechada com 3 cadências de retreino × 3 tamanhos de bloco × 1.620 configurações por fold.
- 77.760 avaliações de configurações foram preservadas, incluindo resultados ruins.
- Correção de multiplicidade por Holm, comparação com apostar sempre, não apostar e mercado de-vigado.
- Políticas de abstinência/“certeza”: 54 políticas para o modelo esportivo e 54 para o modelo ancorado no mercado.
- 806 testes passaram; Ruff e Pyright passaram; CI integrada passou.
- 22 artefatos JSON de pesquisa passaram parsing estrito, sem `NaN` ou `Infinity`.

## Resultado quantitativo

- Brier do modelo esportivo no replay do anchor: **0,246397**.
- Brier do modelo ancorado: **0,242527**.
- Brier do mercado de-vigado: **0,242146** — melhor dos três.
- Apostar sempre no maior EV do modelo perdeu aproximadamente **8,95% a 9,59%** por aposta, conforme a cadência.
- A célula retrospectiva nominalmente mais atraente fez ROI de **+26,31%**, mas com somente **16 apostas** e limite inferior de 95% de **−26,82%**; houve instabilidade por lado e faixa de odd. Não é evidência de lucro.
- Nas políticas de “certeza”, a maior amostra foi 89 apostas no modelo esportivo e 7 no ancorado. Políticas elegíveis: **zero**.
- O filtro ancorado no mercado produziu zero picks elegíveis. Veredito: **NO_GO**.

## Bugs e fragilidades corrigidos

1. Intervalos para uma única aposta eram reportados como se fossem estimáveis. Agora retornam `null` quando `n < 2`.
2. Métricas vazias emitiam `-Infinity`, que não é JSON interoperável. Todos os escritores usam JSON estrito.
3. O sistema podia congelar/nomear um candidato apesar da evidência insuficiente. Agora o candidato fica nulo e a ação é `NO_BET` sem `n >= 200`, LCB de ROI positivo e LCB de CLV positivo.
4. CLV era calculado por razão crua de odds. Agora usa a odd tomada multiplicada pela probabilidade justa de fechamento do par Over/Under de-vigado.
5. A data da fonte de odds podia diferir da data operacional. A v2 preserva ambas e o delta; 128/1.140 registros tinham diferença de um dia.
6. Um replay de agosto de 2026 lia `current_elo`, criando risco de lookahead. Agora reajusta Elo e parâmetros somente com jogos anteriores a cada fixture.
7. A CLI de primeiro/segundo tempo falhava em checkout com cache derivado vazio. Agora recalcula em memória, em modo somente leitura.
8. Manifestos passaram a incluir hashes do motor de pesquisa e do runner, além dos artefatos.

## O que acertamos e o que erramos

Acertamos ao exigir replay temporal, folds aninhados, baselines, perdas individuais, multiplicidade, estabilidade e bloqueio de capital. Também acertamos ao separar probabilidade, EV conservador e força da indicação.

Erramos quando resultados de amostra minúscula podiam parecer mais conclusivos do que eram; quando o CLV não correspondia ao preço justo de fechamento; e quando “testar até lucrar” ainda podia ser confundido com calibração. Repetições ilimitadas sobre os mesmos dados fabricam seleção e não evidência. A v2 fecha a grade, registra tudo e exige validação futura.

## Contrato congelado v2

- Chance do resultado: probabilidade calibrada/ancorada, separada da decisão de apostar.
- EV conservador: EV após haircut de incerteza e fricção; não é probabilidade.
- Força: escala 0–100, limitada a 40 enquanto faltar A1.
- Dados de 2024, 2025 e 2026: observados/contaminados, sem peso confirmatório.
- Capital: desabilitado.
- Promoção futura: somente com coorte A1 prospectiva, preços executáveis e horários de captura atestados, candidato congelado antes dos resultados, `n >= 200`, limite inferior de ROI > 0, limite inferior de CLV > 0, Holm <= 0,05 e estabilidade por temporada, lado e faixa de odd.

## Limitação das odds retroativas

As odds de 2021–2023 são médias/máximas agregadas de múltiplas casas. A fonte não informa bookmaker nominal nem instante executável de captura. Servem para replay exploratório, mas não para CLV, A1 ou liberação de capital.

## Entregáveis

- `ou25-recommendation-v2.json`: contrato operacional congelado.
- `ou25_factorial_summary_v2.json`: nove células e hashes dos artefatos completos.
- `ou25_market_anchor_summary_v2.json`: comparação de Brier e filtro ancorado.
- `ou25_certainty_summary_v2.json`: políticas de abstinência.
- `ou25_backfill_manifest_v2.json`: origem, semântica e hash do backfill.
- `ou25_nested_serving_manifest_v2.json` e `ou25_nested_dixon_coles_manifest_v2.json`: manifestos reproduzíveis.
- `ERRATA_OU25_V1.md`: correções que invalidam interpretações otimistas da v1.
- `ou25_v2_code_bundle.zip`: código, testes, contratos e documentação da v2.

Nenhuma promessa de lucro é feita. A melhoria validada é metodológica: menos leakage, métricas corretas, abstinência obrigatória e um caminho prospectivo falsificável.
