# Continuidade autorizada — dados DC-20260909

O usuário pediu continuar procurando e testando os dados faltantes até cumprir
o mandato. Esta continuidade mantém a pesquisa isolada e não declara rentabilidade.

## Próxima captura definida antes de sua observação

Fixture OddsPapi `id1000032566887012`, Coritiba FC PR x CA Paranaense PR,
selecionado exclusivamente pelo calendário antes das odds. Kickoff conhecido
na captura: **12/09/2026 00:00 UTC (11/09 21:00 em São Paulo)**.
Decisão de pesquisa fixa T−60: **11/09/2026 23:00 UTC (20:00 em São Paulo)**.
Capturar a partir de 22:58:30 UTC, antes de 23:00 UTC. A rotina pode ser iniciada
entre 22:55 e 22:59:15 UTC. Chegada tardia vira janela perdida, não dado PIT.

Somente o par Pinnacle / bet365.bet.br, 1X2 FT. Não trocar bookmaker por preço,
ausência ou recusa. Preservar parent bookmakerIsActive, suspended, marketActive
e active de cada seleção. O piloto encontrou bookmakerIsActive=false na oferta
apesar de preços ativos nas seleções; não homologar esses preços. O flag
indica principalmente coleta no agregador, não suspensão provada na casa.
[Esclarecimento e correções ER](../execution_readiness_2026-09-09/RESULTADO.md).

Uma chamada nova de odds, duas consultas de conta não tarifadas, no máximo.
Preservar reserva20 do contrato e exigir saldo antes da chamada >=21; assinatura
gratuita compatível250/sem renovação e sem preço pago. Orçamento da pesquisa
futura: uma requisição de cota, sem compras. `followup_capture.py` cria marcador
exclusivo antes da rede para impedir repetição. Dados novos ficam em
`C:/BRASILEIRAO/work/data-completion-2026-09-09/followup`.

Comando testado fora da janela (retorna WAITING sem ler chave ou acessar rede):

```powershell
& 'C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv/Scripts/python.exe' -I 'C:/BRASILEIRAO/work/data-completion-2026-09-09/followup_capture.py'
```

A captura é homologação de informação disponível, não aposta, pick operacional,
liquidação ou teste das coortes. Se kickoff/status mudar, conservar raw e
marcar incompatível com o calendário congelado; não reinterpretar o corte.
Não consultar resultados ou fechamento desse evento nesta rotina.

## Acompanhamento na tarefa atual

Verificação diária às 19:57 de São Paulo, permitindo preparar a captura de
11/09. Antes da janela, a rotina não consome API. Pode verificar até duas fontes
oficiais públicas por rodada diária quando isso puder resolver uma lacuna;
conservar recibos e alterar apenas documentos atuais. Não repetir download de
dados já verificados, não executar testes sem mudança ou falha material.

As duas rotinas foram corrigidas e ensaiadas na etapa ER. Quando existir
`followup/capture.json`, inclusive um corpo inválido preservado, auditar em
processo separado e sem credenciais:

```powershell
& 'C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv/Scripts/python.exe' -I 'C:/BRASILEIRAO/work/data-completion-2026-09-09/audit_followup.py'
```

Esse executor usa live_capture_admission.py, combina estado do par com receipt
antes do corte e calendário congelado, e conserva `execution_admitted=false`
enquanto faltarem condições de execução. Congelar o resultado.
Se houver dado admissível, registrar a próxima validação ANTES de qualquer
desempenho. Se continuar inativo/sem limites, reportar o bloqueio concreto e
qual evidência externa decide o passo seguinte. Não ampliar indefinidamente
consultas, casas ou filtros até aparecer resultado positivo.

Esta etapa diária termina em 12/09/2026, ou quando a captura estiver auditada
e nenhuma ação útil autorizada restar. Atualizar/pausar o próprio acompanhamento;
não arquivar a tarefa nem alterar agendamentos H14/H15/H9/A1. O objetivo geral
continua aberto se existir pendência, mesmo quando a rodada termina.

Permanecer silencioso quando nada relevante mudar. Informar avanço material,
falha, conclusão delimitada ou informação indispensável. Nunca dizer "tudo OK"
enquanto faltar cobertura, procedência, execução, custos ou validação adequada.
O computador deve permanecer ligado e o aplicativo aberto para acessar arquivos
locais, conforme a [documentação oficial de tarefas agendadas](https://learn.chatgpt.com/docs/automations?surface=app).
