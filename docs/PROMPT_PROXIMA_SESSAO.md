# Próxima sessão — dados e execução verificáveis

Trabalhe sozinho em `C:/BRASILEIRAO/brasileirao-predictor`, mantendo os dados
e entregas em `C:/BRASILEIRAO`. Leia [ESTADO_ATUAL](ESTADO_ATUAL.md),
[RETOMADA](continuation/RETOMADA.md),
[mandato](continuation/MANDATO_LUCRO_2026-09-09.md),
[resultado ER](continuation/execution_readiness_2026-09-09/RESULTADO.md) e
[CONTINUIDADE](continuation/data_completion_2026-09-09/CONTINUIDADE.md).

Continue resolvendo as pendências concretas de preços, procedência temporal,
capacidade, custos e validação. Os 177 históricos já foram adquiridos e
verificados; não repetir o lote nem alterar filtros com base no saldo closing.
A fonte pública avisa referência Pinnacle desatualizada. No piloto, a Bet365
Brasil estava sinalizada sem coleta ativa no agregador; isso não prova
suspensão da oferta na casa. Nada disso demonstra lucro.

O acompanhamento já está configurado na tarefa atual, diariamente às 19:57
de São Paulo. Use a rotina e a janela UTC congeladas para a captura de 11/09,
respeitando idempotência, quota e reserva. A auditoria deve rodar em processo
separado sem credenciais. Não recrie a automação nem force aquisição fora da janela.

Preserve H14/H15/H9/A1 integralmente. Não execute avaliadores, apostas,
logins de casas ou compras; não abra coortes como holdout. Novas decisões
materiais precisam de protocolo anterior ao desempenho. Atualize apenas os
guias atuais e novos checkpoints; conserve os documentos históricos.

Verifique HEAD e diff antes de editar; o recibo final está em
`C:/BRASILEIRAO/AUDITORIA/EXECUTION_READINESS_2026-09-09.json`.
[HANDOFF](../HANDOFF.md) e [índice documental](INDICE_DOCUMENTACAO.md) mantêm
o histórico. Não usar caminhos do computador antigo como destinos de escrita.
