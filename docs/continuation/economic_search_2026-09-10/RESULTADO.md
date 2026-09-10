# Busca econômica BE-20260910

**Foi encontrado um candidato de diferença de preços, ainda sem comprovação de execução. O novo modelo de gols foi reprovado. O projeto não foi entregue lucrando.**

As correções RI/IE anteriores permanecem válidas apenas nos escopos testados. Esta rodada mudou o foco para duas perguntas econômicas, com protocolo registrado antes do novo desempenho. Base main/b95dabaf05800918ee46f4a40f1cfa74688ce4a8. Congelamento 10/09/2026 12:34:25 UTC; avaliação 13:42:56–13:43:24 UTC; recuperação de fontes encerrada às13:48 UTC, dentro dos90 minutos. Trabalho solo e arquivos em C:/BRASILEIRAO.

## 1. Pergunta e 2. prioridade

Os três melhores preços de 1X2 permitiriam cobrir vitória, empate e derrota com sobra após custos? Essa pergunta recebe prioridade porque dispensa acertar o vencedor e testa diretamente uma diferença de preços. Alternativa independente: uma previsão fixa, feita só com gols anteriores, conseguiria superar a oferta Pinnacle? O fracasso de três capturas de um único evento não respondia a nenhuma dessas perguntas em outros períodos.

## 3. Hipótese e 4. experimento

Principal: carteira que divide 1 u entre H/D/A proporcionalmente a 1/odd, reduz o prêmio das odds em 1% e desconta 2% da stake. Selecionar apenas sobras>=0,5%. Essa conta mede um **envelope hipotético dos máximos anônimos publicados**, sem tratar esses máximos como ofertas executáveis. Não usa o vencedor e não precisa de labels.

Alternativa: Poisson independente com forças de ataque/defesa regularizadas por 10 jogos equivalentes, janela 730 dias, meia-vida 365, resultados defasados ao menos 7 dias. Mínimo 300 jogos anteriores. Os preços não entram na previsão. Seleção fixa: maior EV após custo 2%, mínimo 3%, um lado/jogo, stake 1 u, banca 100 u sem aportes. Todas as partidas de uma data reservam capital antes de qualquer liquidação do dia. Comparador: mesmas regras, somente médias da liga, sem forças dos clubes. Nenhum parâmetro foi ajustado ao resultado.

## 5. Dados e 6. disponibilidade

Reutilizados bytes públicos já preservados da [Football-Data — Brasil](https://football-data.co.uk/brazil.php), SHA256 ba3e9ea79ab4091b117a901f3914940cea07f1fe06de0deb57af5076f664ccb6.4.940 jogos de2012–2024:380 por temporada,20 clubes e38 jogos por clube, sem chave duplicada. Há1 trio Pinnacle ausente,1 trio máximo ausente e1 placar/resultado não liquidável. A linha sem placar é Chapecoense-SC/Atletico-MG,2016-12-11; não foi convertida em void nem usada no treino.636 linhas fora do período foram descartadas por Season antes da interpretação dos demais campos. Nenhum label2025/2026 ou conteúdo de coorte protegida foi consultado nesta rodada.

[Notas da fonte](https://football-data.co.uk/notes.txt) identificam PSC/MaxC como fechamento e máximos, mas não fornecem casa de cada máximo, timestamps históricos de recepção, simultaneidade ou aceite. O [aviso de desatualização Pinnacle desde23/07/2025](https://football-data.co.uk/data.php) motivou manter2012–2024; não certifica os anos anteriores. Decisão do cenário é fechamento, nunca T−60 reconstruído. O atraso de7 dias dos resultados é uma suposição conservadora, sem recibos históricos de publicação. Os anos podem ter sido usados em pesquisas anteriores: **não são holdout independente comprovado**.

## 7. Resultado

| Cenário | Universo | Carteiras/fills hipotéticos | Stake total | Resultado após fricções fixadas | ROI sobre stake |
| --- | ---: | ---: | ---: | ---: | ---: |
| Máximos anônimos, três lados |4.940|226 carteiras/678 pernas|226 u|+4,6376 u|+2,0520%|
| Previsão de gols, Pinnacle |3.800|632|632 u|−99,60 u|−15,7595%|
| Comparador médias da liga, Pinnacle |3.800|1.458|1.458 u|−98,99 u|−6,7894%|
| Execução real de qualquer estratégia | — |0|0|Não realizada|Não mensurável|

Os dois mecanismos têm universos e hipóteses diferentes; a tabela não estima superioridade causal entre eles. Modelo e comparador compartilham o universo de 3.800 jogos, com exposições distintas e explicitadas.

Arbitragem:226 candidatas em 183 datas, 13 temporadas, 4,575% dos 4.940 jogos; 1 jogo sem preços.4.714 sem carteira candidata, incluindo o faltante. A carteira completa devolveria 235,1576 u incluindo principal, descontaria 226 u de stake e 4,52 u de custo adicional, resultando em 104,6376 u de banca hipotética. Exposição máxima por data 4 u. O capital inicial 100 u é suficiente para esse cenário de liquidação diária e preenchimento integral. O prazo real de liquidação/capital preso é desconhecido. A sobra por evento varia 0,0050–0,2374 u; cinco maiores somam 0,61735 u, 13,31% do total.

| Temporada | Candidatas | Sobra condicional (u) |
| --- | ---: | ---: |
|2012|31|0,47266|
|2013|18|0,27711|
|2014|41|0,73060|
|2015|23|0,37319|
|2016|16|0,25954|
|2017|9|0,09257|
|2018|7|0,20796|
|2019|9|0,54244|
|2020|9|0,33545|
|2021|8|0,14718|
|2022|14|0,40336|
|2023|33|0,56397|
|2024|8|0,23158|

Todas as sobras selecionadas são positivas **por construção**. A distribuição em anos demonstra incidência do envelope, não lucro realizado, simultaneidade ou significância estatística. Não representa renda anual/mensal nem escalabilidade.

Modelo:3.128 escolhas com EV estimado, mas só 632 financiáveis.671 jogos sem edge, 1 sem Pinnacle e 2.496 abstenções por falta de capital; 3.168 abstenções no total. Receita 545,04 u, custos 12,64 u, saldo final 0,40 u. Primeira abstenção por capital em 21/05/2017; anos posteriores sem fills não são anos de retorno nulo de uma estratégia financiada. Perdas 2015/2016/2017:−38,50/−50,63/−10,47 u. Exposição máxima 9 u/data; drawdown 107,16 u desde o pico. Comparador termina com 1,01 u; maior exposição 10 u/data e drawdown 135,71 u. Sua temporada 2017 positiva não o tornou lucrativo no conjunto.

No painel comum 3.799 jogos, logloss modelo 1,02267; médias 1,05221; Pinnacle normalizada 0,99724. Brier multiclasse, soma dos três quadrados:0,61315/0,63395/0,59607. O modelo melhora a previsão sobre médias, mas fica atrás da referência e perde dinheiro. Nas 632 escolhas financiadas, probabilidade média estimada 37,20% e frequência observada 27,53%. Portanto qualidade relativa à média não bastou para superar os preços.

Bootstrap fixo de blocos 28 dias, 2.000 amostras, seed 20260910: IC 95% do ROI dos fills do modelo[−27,317%;−3,526%], comparador[−17,142%;+4,852%]. A diferença de PnL pareada tem IC[−150,414;+126,528]u. São diagnósticos exploratórios dos fills observados, condicionados ao esgotamento de capital. **Não refazem a política a cada amostra, não corrigem busca histórica desconhecida e não estimam renda futura.** O resultado da conta fechada já reprova o critério, independentemente desses intervalos.

## 8. Custos e 9. riscos

Arbitragem nas mesmas 226 carteiras: custos 0/1/2/3/5% resultam+9,1576/+6,8976/+4,6376/+2,3776/−2,1424 u, sempre após deterioração 1% do prêmio. Os 4,6376 u são todo o espaço restante para custos fixos adicionais nesse período e escala. Não há unidade monetária inferida, tarifa pessoal, imposto ou manutenção conhecidos. Lucro total após esses custos permanece null.

Se apenas parte das pernas for aceita, o pior evento pode perder 0,9635 u. Num estresse que atribui a cada carteira seu pior subconjunto incompleto com probabilidade uniforme, aproximadamente 2,4676% de falhas eliminam a sobra média. Essa frequência é **limiar calculado, não taxa medida**. Mínimo de deterioração total do prêmio que zera uma das carteiras escolhidas:1,7501%, contra 1% já descontado. Regras diferentes de cancelamento, aposta anulada isoladamente, limites, moeda, arredondamento e slippage podem quebrar a cobertura.

Modelo perde−86,96 u mesmo retirando o custo adicional dos mesmos fills; com deterioração 1% do prêmio,−103,3104 u. Sensibilidades preservam fills e não refazem o caminho do capital: perdas superiores à banca são estresses aritméticos, não trajetórias financiáveis. Margem embutida não foi cobrada duas vezes.

## 10. Limitações e recuperação tentada

Foram 10 GETs públicos diretos, zero APIs autenticadas e zero consumo da reserva DC. Três documentos Football-Data foram recuperados com HTTP 200, hashes e recibos. OddsPortal/2024 redirecionou 301 para OddsAgora, depois 307 para verificação de idade; a página exige declaração de 18 anos. Não foi feita declaração pessoal pelo usuário, criado cookie ou contornado o controle. Betfair/docs e especificação redirecionaram 302 para historicdata.betfair.bet.br, que falhou com URLError nas duas consultas. A consulta web da especificação retornou apenas página que requer JavaScript. O material público Betfair descreve planos, mas nenhum arquivo de preços foi recebido. Não se conclui que a fonte seja inexistente, que o plano livre seja executável ou que dados adquiridos tenham clocks/volumes adequados.

Não foram recuperadas casas/timestamps dos 226 máximos. Não houve login, aposta, compra, novo agendamento, API limitada ou alteração dos helpers DC. A consulta pública pontual de duas partidas 2024 não forneceu histórico de ofertas identificado. Nada dessa recuperação foi usado para retunar o experimento. Requerimentos para a etapa seguinte: preços identificados simultâneos, possibilidade de preencher cada lado, regras compatíveis e custos totais, em universo futuro separado e previamente registrado. A captura DC congelada de uma dupla permanece distinta desse experimento de três pernas.

## 11. Testes

Dez testes materiais aprovados antes dos desfechos: carteiras reconciliadas em todos os vencedores, perdas em preenchimento parcial, massa/simetria Poisson, exclusão de futuro/alvo/últimos 6 dias, independência de odds na previsão, filtragem de temporadas antes dos campos, duplicata/label inválido, reserva simultânea de capital, não liquidação inventada e ausência de edge por normalização da própria casa. Auditoria independente Decimal com 40 dígitos conferiu 4.939 envelopes calculáveis, 226 seleções, cada retorno/fill e as duas bancas. Todos os hashes de saída conferidos. Ruff/formato e Pyright aprovados; erro inicial de anotação de tupla no teste foi corrigido, sem alteração do executor ou resultado. Ver reprodução e recibos para checks finais de pacote.

## 12. Estados e 13. decisão

- **Técnica:** executor offline pronto no escopo testado. Não homologa serving, execução financeira ou infraestrutura operacional. Revisões RI/IE não foram repetidas integralmente.
- **Dados:** admissíveis para os cenários retrospectivos explicitados; insuficientes para demonstrar oferta simultânea, aceitação, capacidade ou lucro executável.1 label inválido preservado, nenhuma imputação financeira.
- **Economia:** principal atingiu 226 candidatas/13 temporadas, superando o critério prévio 30/3 para investigar simultaneidade. Evidência suficiente **apenas para essa próxima investigação**; lucro executável não mensurável. Modelo de gols sem suporte e reprovado no cenário fixo. Não foi escolhido como estratégia o comparador menos negativo.

Encerradas as duas perguntas desta rodada: uma produziu candidato condicionado a dados comerciais ainda não recuperados; outra falhou. Nenhuma variante foi acrescentada para salvar o saldo. O objetivo global de lucro futuro permanece não alcançado.

## 14. Próxima informação decisiva

A descoberta que mais muda a decisão é a existência de 226 carteiras matematicamente positivas, acompanhada da fragilidade a falhas de preenchimento. Isso desloca a prioridade para **obter ofertas simultâneas identificadas e medir se as três pernas poderiam ser preenchidas com margem restante suficiente**. O modelo fixo de gols perde prioridade: mesmo o preço hipoteticamente disponível não o salvou.

Uma nova fase deve congelar fontes/casas, universo, clocks, custos, critério de seleção e orçamento antes das novas cotações; separar observação de aceite e preservar rejeições. Sem esses dados, aumentar stake ou exibir o envelope como lucro seria uma conclusão falsa. As restrições do mandato, coortes e captura futura continuam vigentes.

Relatório, protocolo, código, todos os outputs e recibos são entregues em C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_BE_20260910. Git/backup final em C:/BRASILEIRAO/AUDITORIA/BUSCA_ECONOMICA_2026-09-10.json.
