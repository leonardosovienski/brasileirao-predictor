# A1 OU2.5 — runbook da Fase 0 sem labels

## Estado e objetivo

Esta fase mede cobertura, continuidade, disponibilidade, latência e incerteza
da referência. Ela não lê resultado, fechamento, CLV, ROI ou P&L; não emite
pick; não habilita Kelly nem capital. O threshold permanece descongelado até
existirem sete dias válidos de operação e um orçamento de fricção revisado.

No plano gratuito, a operação usa somente T−24h/T−6h/T−1h/T−10m e permanece
`REHEARSAL_ONLY_BUDGETED`; o gate de continuidade horária não se aplica. Antes
de qualquer chamada tarifada, `/account` confirma a cota; são preservadas 20
requisições mensais, cada fixture/janela admite no máximo duas tentativas e um
erro impõe backoff de 30 minutos. O estado local nunca armazena a chave.

## Preparação sem segredo

```powershell
uv run python scripts/a1_phase0.py --init
uv run python scripts/a1_phase0.py --verify
uv run pytest tests/test_a1_phase0.py tests/test_collector_contract.py
```

Qualquer alteração na política, coletor ou código da Fase 0 muda o fingerprint
e bloqueia novas observações até revisão e nova inicialização explícita.

## Configuração local da chave

Não cole a chave em chat, arquivo versionado ou comando que fique no histórico.
Configure `ODDSPAPI_KEY` no gerenciador de segredos/ambiente do processo que
executará o job. Confirme o tier e a cadência permitida antes de agendar.

## Execução manual inicial

```powershell
uv run python scripts/collect_odds_a1.py --discover
uv run python scripts/collect_odds_a1.py --collect
uv run python scripts/a1_phase0.py --report
uv run python scripts/evaluate_gate_a1.py
```

O primeiro smoke deve ser acompanhado manualmente. A tarefa agendada só deve
ser instalada depois de confirmar que nenhum segredo aparece em stdout/stderr,
que os aliases resolvem e que snapshots/quarentena estão nos diretórios
esperados. Agendamento exige autorização operacional explícita do usuário.

Depois do smoke aprovado, o instalador existente registra descoberta semanal,
captura a cada 15 minutos e métricas diárias, falhando antes de qualquer
alteração se a chave não existir no ambiente do usuário:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_collector_a1_task.ps1
```

## Saída para a próxima fase

Depois de sete dias aprovados, estime cada componente de
`friction_budget_pp`, revise e congele o contrato antes de observar qualquer
closing ou resultado da coorte científica. O tamanho da coorte de CLV é
calculado por:

```powershell
uv run python scripts/a1_phase0.py --clv-power <desvio-piloto-log-clv> <efeito-minimo-log-clv>
```

O piloto usado para estimar o desvio não pode ser reutilizado como confirmação.
