# Retomada — C:/BRASILEIRAO, DC-20260909

Leia [estado atual](../ESTADO_ATUAL.md), [mandato](MANDATO_LUCRO_2026-09-09.md),
[resultado DC](data_completion_2026-09-09/RESULTADO.md) e
[continuidade](data_completion_2026-09-09/CONTINUIDADE.md).
Trabalhe sozinho. Lucro executável não está demonstrado; capital bloqueado.

## Checkpoint

Base da rodada `main` em `5dec2521bab581d5dda104d954f4cc6274b74702`; commit
de integração no recibo `C:/BRASILEIRAO/AUDITORIA/DADOS_COMPLEMENTARES_2026-09-09.json`.
177/177 históricos verificados, CSV de 380 jogos de 2025 recuperado e três
capturas atuais de um único evento. Não repetir downloads completos.
O fechamento tem aviso de referência Pinnacle desatualizada; no piloto a
oferta Bet365 Brasil tinha `bookmakerIsActive=false`. Seleções ativas nos
filhos não anulam o estado inativo do bookmaker. Zero admissões para execução.

O replay closing condicional perdeu 9,24u; não ajustar filtros após esse saldo
nem chamar a fonte comprometida de validação. Os 138 testes da pesquisa
passaram. Nenhuma coorte protegida ou resultado de 2026 foi avaliado.

## Próxima ação concreta

O acompanhamento diário às 19:57 de São Paulo executa a rotina delimitada
`C:/BRASILEIRAO/work/data-completion-2026-09-09/followup_capture.py`.
Antes de 11/09 19:55, retorna WAITING sem API. Na janela, no máximo uma
consulta de odds para o fixture congelado `id1000032566887012`, par
Pinnacle / bet365.bet.br, antes da decisão de 11/09 20:00.
Conta gratuita e reserva mínima são novamente verificadas. Chegada tardia
não autoriza redefinir o corte ou fabricar disponibilidade.

Depois da captura, executar `audit_followup.py` em processo separado e sem
credenciais. Exigir clocks, calendário congelado e todos os estados ativos
antes de admitir a observação; aceite, capacidade e custos continuam separados.
Até duas consultas públicas oficiais úteis por rodada diária são permitidas.
Não repetir testes sem mudança ou falha que justifique. Em 12/09, ou ao
terminar a captura auditada, reavaliar o próximo passo dentro do mandato e
pausar o acompanhamento se nenhuma ação útil autorizada restar.

## Caminhos e reprodução

Código: `C:/BRASILEIRAO/brasileirao-predictor`. Novos dados, recibos e scripts:
`C:/BRASILEIRAO/work/data-completion-2026-09-09`. Entrega atual:
`C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_DC_20260909`.
[Reprodução offline](data_completion_2026-09-09/REPRODUZIR.md),
[pendências](data_completion_2026-09-09/PENDENCIAS.md) e [mapa de dados](../DATA_MAP.md).

Preservar H14/H15/H9/A1, artefatos, contratos, observadores, quotas reservadas,
claims, agendas e avaliadores. Não importar tarefas antigas nem ligar runtime
para reproduzir essa pesquisa. Nenhuma aposta, conta de apostas, compra ou
alteração financeira está autorizada. O ambiente mínimo Python não é uma
instalação operacional completa.

A [rodada PF anterior](price_feasibility_2026-09-09/RESULTADO.md) e os
[guias anteriores à consolidação](../history/antes_consolidacao_2026-09-09/README.md)
preservam seu contexto histórico. Não atualizar resultados congelados para
fazê-los parecer vigentes; atualizar os guias de entrada e acrescentar novo checkpoint.
