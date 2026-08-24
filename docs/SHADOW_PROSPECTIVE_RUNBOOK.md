# Runbook: coorte prospectiva H3/H5

> **STALE / HISTÓRICO desde 2026-08-22.** H3/H5 estão mortas/substituídas e
> este documento não deve operar a coorte vigente. Para H9 e o estado atual,
> use o topo de `HANDOFF.md` e `docs/READINESS.md`.

H1 permanece `HYPOTHESIS_REFUTED`. H3/H5 usam somente odds correntes pré-jogo,
modelo, mercado e thresholds congelados em `data/trials.json`; a meta é 100
`MATURED_ELIGIBLE`, sem capital.

Antes de capturar, a integração de odds deve fornecer um bookmaker real e
auditável em `BRASILEIRAO_BOOKMAKER`. Sem ele, `scripts/sombra.py --capture`
falha fechado e não grava pick elegível. `sofascore` é a fonte, não um bookmaker.

Após cada ingestão, execute captura. O settle só promove um pick com resultado
oficial e a última snapshot válida anterior ao kickoff, do mercado/seleção do
pick. Ausência de closing mantém o pick pendente. Use
`python scripts/monitor_shadow_cohort.py` para a visão somente leitura e
`python scripts/evaluate_shadow_cohort.py` para o gate estrito.

Os jobs canônicos `brasileirao-sombra-manha` e `brasileirao-sombra-noite`
também registram um smoke da fonte antes da rotina de sombra e emitem o
relatório de estabilidade. Eles não persistem pick enquanto não existir
bookmaker congelado. A estabilidade exige três janelas ao longo de 24 horas;
repetições imediatas não contam como evidência.

Qualquer alteração de modelo, trial, mercado, threshold ou closing encerra a
coorte e exige trial novo iniciado em zero.
