# Reparo delimitado de transporte

Durante a aquisição houve ConnectionResetError no fixture
`id1000032566886550` (ordinal36). Não foi recebido payload para esse evento.
Os demais pedidos continuaram sem substituir o fixture ou mudar as casas.

Após encerrar o lote, fazer uma única recuperação manual desse erro de
transporte, no mesmo endpoint/par/parâmetros, com intervalo superior ao
cooldown. Não repetir 401/403/429 nem respostas válidas sem cobertura. A primeira
falha permanece em acquisition.json; esta recuperação terá recibo separado.
O universo177 e todas as regras permanecem congelados. Isso não é uma variante
de estratégia nem reinício da busca; nenhum desfecho/EV motivou o reparo.
O histórico não consome cota, e o total de pedidos da rodada permanece abaixo
do teto177. Se falhar novamente, manter o dado ausente e o motivo explícito.
