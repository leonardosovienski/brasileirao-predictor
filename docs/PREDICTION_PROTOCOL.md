# Protocolo de previsão

Versão: `prediction-protocol/1`
Estado: obrigatório para qualquer previsão apresentada como oficial.

## 1. Finalidade e classes

Toda saída deve ser classificada antes do cálculo:

1. `OFFICIAL_PRE_MATCH`: congelada estritamente antes do kickoff.
2. `OFFICIAL_LIVE`: congelada depois do kickoff, com minuto, placar e relógio da observação.
3. `RETROSPECTIVE_ONLY`: simulação feita depois do kickoff ou depois de conhecido o resultado. Nunca é evidência prospectiva.

Uma previsão bloqueada não recebe palpite oficial. Nenhuma classe autoriza capital.

## 2. Relógio e conjunto de informação

O corte é `predicted_at`, em UTC aware. Só pode entrar informação com `available_at <= predicted_at` e jogo de treino com `kickoff_at < predicted_at`. Resultado só entra se já estava oficialmente disponível.

Para uma previsão operacional em agosto de 2026, o histórico deve conter **todos os jogos elegíveis já conhecidos**, inclusive 2025 e os jogos anteriores de 2026. Isso não abre o holdout para pesquisa:

- política científica: 2021–2023 desenvolvimento, 2024 validação, 2025 holdout selado e 2026 exploratório;
- estado operacional: ajuste walk-forward com tudo que existia antes da previsão;
- resultados operacionais de 2025/2026 não podem ser usados para escolher retrospectivamente arquitetura, hiperparâmetro ou regra de decisão.

## 3. Procedimento

1. Fixar evento, mandante, visitante, `event_id`, kickoff e tipo da previsão.
2. Criar o documento de prontidão descrito em `PREDICTION_REQUIREMENTS.md`.
3. Executar `python -m brasileirao_scripts.check_prediction_readiness <arquivo.json>`; código 2 bloqueia emissão.
4. Ajustar a versão congelada do serving com histórico completo até `predicted_at`. Ensemble xG permanece desligado.
5. Gerar a distribuição completa: `P(casa)`, `P(empate)`, `P(fora)`, lambdas e placares mais prováveis.
6. Congelar entrada, versão/fingerprint, horários e saída em ledger append-only antes de comunicar o resultado.
7. Comunicar separadamente:
   - probabilidades 1X2;
   - placar modal e sua probabilidade;
   - diferença entre as duas maiores probabilidades 1X2;
   - nível de incerteza;
   - disponibilidade e uso de escalação/mercado;
   - limitações.

## 4. Escolha, empate e incerteza

O inventário completo de sinais, confundidores, dados PIT e diagnósticos está
em `docs/DRAW_VARIABLE_CATALOG.md`.

O argmax 1X2 e o placar modal respondem perguntas diferentes. Um 1–1 modal não implica que empate supere a soma de todos os placares de vitória. Ambos devem aparecer.

Não existe hoje threshold validado para converter automaticamente jogos equilibrados em empate. Portanto:

- não inventar convicção quando as probabilidades estiverem próximas;
- não substituir o argmax manualmente após observar o resultado;
- sem política de decisão congelada e validada, rotular `SEM_ESCOLHA_ROBUSTA` e manter a distribuição;
- qualquer regra nova de empate é uma hipótese, testada uma variável por vez e nunca promovida por accuracy isolada.

## 5. Escalações e dados ao vivo

Escalação só altera quantitativamente a previsão se existir transformação congelada, PIT e validada. Até lá, provável/confirmada e mudanças de titulares são contexto declarado, não peso improvisado.

Em previsão ao vivo, minuto, placar e `live_observed_at` são obrigatórios. Estatísticas ao vivo sem pesos validados não entram no cálculo; podem ser arquivadas e descritas como observação. Cada nova previsão recebe novo ID e linha; nenhuma anterior é editada.

Toda previsão `OFFICIAL_LIVE`, inclusive `LIVE-2026-08-22-001`, recebe
`pre_match_evidence_eligible=false` e `economic_evidence_eligible=false`.
Ela pode ser avaliada apenas na coorte live separada; nunca compõe narrativa,
coverage ou métricas prospectivas pré-jogo.

## 6. Avaliação

Pré-jogo, ao vivo e retrospectiva são coortes separadas. Sempre informar `n` e coverage. RPS é a métrica primária 1X2; Brier e log loss são guardrails; accuracy é `DIAGNOSTIC_ONLY`. Settlement é append-only e ligado pelo `prediction_id`.

Não promover modelo, regra ou capital na mesma amostra em que a hipótese foi concebida.
