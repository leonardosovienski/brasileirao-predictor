# TRACK A02 — estados dinâmicos por clube

Registrado em 2026-08-22 antes da primeira execução do motor
`dynamic_strength` no painel canônico.

## Procedência e limite de inferência

A ideia de separar ataque e defesa não é cega: o protótipo histórico
`sim_melhorias.py` e seus resultados em 2025/2026 já existiam. Portanto este
documento não chama a ideia de pré-registro confirmatório. Ele congela, antes
da nova medição, a implementação nova de estados residuais curto+longo e o
protocolo que impede novo ajuste em 2026. O holdout 2025 não será avaliado.

## Contraste de uma variável

- Controle: `--engine serving`, ensemble xG desligado.
- Tratamento: `--engine dynamic_strength`, idêntico ao controle mais estados
  ofensivos e defensivos por clube em log-rate.
- Congelados: Elo, `mu`, mando, NB+DC, janelas de calibração, cadência de
  refit, `max_goals` e ausência do ensemble xG.
- Estados: razões gols observados/esperados com prior Gamma neutro; memórias
  EWMA `alpha_short=0.30` e `alpha_long=0.05`, peso 50/50 entre memórias e
  entre evidências de ataque/defesa, `ridge_reg=1.0`, `eps=0.1`.

## Dados e decisão

- Desenvolvimento: 2021-01-01 a 2023-12-31, usado somente para detectar erro
  de implementação ou degradação evidente; nenhum grid será aberto nesta
  primeira leitura.
- Validação: 2024-01-01 a 2024-12-31, uma única execução após congelar código.
- Primária: delta pareado de RPS tratamento-controle, bootstrap móvel de 21
  jogos, 1.000 réplicas, seed 13.
- Guardrails: Brier 1X2, log-loss e Brier OU2.5 não podem apresentar IC95 de
  degradação inteiramente acima de zero. Accuracy é `DIAGNOSTIC_ONLY`.
- GO técnico: RPS menor no tratamento em 2024 e nenhum guardrail com
  degradação estatisticamente demonstrada. IC95 cruzando zero torna o achado
  inconclusivo, não comprovado.
- 2026: somente diagnóstico depois da decisão de 2024, sem alterar parâmetro.
  Toda taxa de acerto será acompanhada de `n` e cobertura.

Nenhum resultado deste protocolo demonstra edge econômico ou autoriza capital.

## Auditoria da primeira execução

A primeira execução de desenvolvimento revelou que o código inicializava o
prior dentro do acumulador EWMA; assim, o próprio decaimento apagava o ridge
depois de vários jogos. Isso contradiz a especificação acima de prior Gamma
permanente. O relatório inicial fica preservado, mas é inválido para decidir a
hipótese. A correção mantém `ridge_reg` somado ao numerador e denominador no
momento de extrair a razão. Ela foi registrada antes da repetição e não usa
2024, 2025 ou 2026.

## Resultado e decisão

A repetição corrigida em desenvolvimento teve `n=940`, cobertura 100%:

- RPS: delta tratamento−controle `+0,001042`, IC95
  `[-0,000907, +0,003100]`;
- Brier 1X2: `+0,002456`, IC95 `[-0,001824, +0,006851]`;
- log-loss: `+0,003737`, IC95 `[-0,002739, +0,010519]`;
- Brier OU2.5: `−0,002030`, IC95 `[-0,008169, +0,003767]`;
- accuracy 1X2, apenas diagnóstico: 47,13% → 46,70%.

Decisão: **NO-GO** para esta parametrização. Não houve ganho de RPS em
desenvolvimento e nenhum efeito fechou a favor do tratamento. Conforme o
protocolo, 2024 e 2026 não foram consumidos; 2025 permaneceu intocado. O motor
de produção não foi alterado.
