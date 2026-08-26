# PROMPT CODEX — Sessão de reteste e reavaliação (read-only científico)

Contexto: coletor A1 implementado e em shadow (modo econômico). Modelo de
previsão INTOCÁVEL nesta sessão. Objetivo: verificar integridade de tudo que
existe e medir o que mudou com dados novos — SEM alterar serving, SEM treinar,
SEM consumir 2024 ou 2025.

Leia antes: HANDOFF.md, data/trials.json, docs/PROJECT_LOGIC_REGISTER.md.

## RESTRIÇÕES ABSOLUTAS
1. Modelo/serving/cache/config: proibido alterar. Reteste é REGRESSÃO.
2. 2024: proibido (validação única já tem dono: hipóteses futuras).
3. 2025: proibido (holdout selado).
4. 2026: somente diagnóstico read-only de regras já congeladas.
5. Nenhum backtest novo, nenhum threshold novo, nenhuma ressurreição de
   hipótese refutada (ver trials.json: 26 registros).
6. Nenhum pick, stake, capital. Shadow do coletor segue REHEARSAL_ONLY.
7. Listar todos os desvios; sem commit/push.

## TAREFA 1 — Regressão histórica (o número NÃO pode mudar)
- Rodar o painel canônico (--engine h9_frozen) em 2021–2023 (n=940) e
  comparar com os valores registrados: RPS, Brier, log loss, accuracy.
- CRITÉRIO: qualquer divergência > 1e-6 em relação aos valores de referência
  documentados = REGRESSÃO DE PIPELINE. Investigar causa antes de prosseguir
  e reportar como incidente, não como "mudança de performance".

## TAREFA 2 — 2026 atualizado (o que pode ter mudado de verdade)
Reexecutar os diagnósticos de 2026 com TODOS os jogos disponíveis agora:
- n atual de 2026 (T1/T2), accuracy, RPS, Brier, log loss vs. baseline
  registrado (RPS 0,208918 / Brier 0,630819 / log loss 1,044541 / acc 47,11%);
- T2-2026 atualizado: n, accuracy, intervalo binomial 95% sob p=0,50,
  calibração marginal dos lambdas (λ médio vs gols reais, casa e fora, com IC).
  Atualizar o veredito RESULT_NOISE_NOT_PARAMETER_DRIFT: mantém, reforça ou
  enfraquece? Reportar novo n e novo IC;
- Matriz de confusão 2026 atualizada + decomposição λ por resultado real
  (guardrail permanente implementado na sessão anterior);
- p_draw médio vs. taxa real de empates 2026 atualizado;
- Reliability de p_draw por faixa (guardrail permanente).
- COMPARAR explicitamente com os números da sessão anterior (n=225,
  T2 n=35, 28,6%) e registrar delta.

## TAREFA 3 — Saúde do coletor A1 (dados novos de verdade)
- Dias de shadow acumulados, snapshots por dia, requests consumidas vs.
  orçamento (245/mês no modo econômico);
- Métricas: event_coverage, market_coverage, identity_resolution_rate,
  conflict_rate, quarentenas (e motivos);
- Sportingbet BR: mercado 101 apareceu em snapshots posteriores? Pixbet
  apareceu? Atualizar docs/COVERAGE.md;
- Rodar scripts/evaluate_gate_a1.py e reportar saída (esperado:
  REHEARSAL_ONLY enquanto não fecharem 7 dias);
- Hash-chain íntegro em todos os arquivos diários (verify_chain).

## TAREFA 4 — Integridade do repositório
- Suíte completa + ruff + pyright + ci_check (reportar contagens);
- trials.json: nomes únicos, todos com status;
- Confirmar que structural_edge.py NÃO recebeu nenhum snapshot
  (homologated=false em 100% das linhas);
- Confirmar que nenhum endpoint histórico foi chamado (logs do coletor).

## ENTREGA
docs/RELATORIO_RETESTE_<data>.md com:
1. Regressão histórica: idêntica sim/não (se não, causa raiz);
2. Tabela 2026: antes (n=225) vs. agora (n atual), métrica por métrica;
3. Veredito T2 atualizado com novo n e ICs;
4. Saúde do coletor: tabela de métricas + saída do avaliador;
5. Integridade: contagens de testes, ledger, hash-chain;
6. Lista explícita de desvios.
