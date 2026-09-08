# Teste histórico do novo candidato xG — resultado

**Não houve melhora geral. O candidato calibrado perdeu mais que o modelo anterior; a versão sem calibração perdeu menos, mas continuou negativa. Nenhuma das duas superou o mercado nos três painéis probabilísticos.**

## Amostra e método

Executado uma vez em 08/09/2026 UTC, após congelar o plano e antes de examinar as novas métricas. São dados reais históricos já explorados, sem apostas executadas.

- Universo: 380 partidas de 2025; painel comum de **368**. Seis partidas foram excluídas por histórico insuficiente de time/mando e seis por preços incompletos ou inválidos.
- Forças iniciais: histórico de 2021–2023. Calibração: **368 alvos elegíveis de 2024**. Avaliação: 2025, sem reajuste das escalas ou parâmetros.
- Parâmetros do candidato: os defaults congelados da implementação, não os parâmetros reduzidos da demonstração. Janela de cinco partidas por mando, mínimo de três e meia-vida de 90 dias.
- Comparador anterior: probabilidades brutas já salvas do modelo ajustado somente até o fim de 2024. O blend aprendido em 2025 não foi usado para avaliar o próprio ano de calibração.
- Mesmos jogos, odds, filtros e custos para todos os braços: no máximo uma aposta por partida; 1 unidade fixa; custo adicional de 0,02u inclusive nas perdas; sem reinvestimento.

Faltam os horários históricos de publicação/recebimento do xG. Por isso, este é um **diagnóstico condicional à hipótese de disponibilidade após 48 horas**, com decisão uma hora antes do jogo. O adaptador separado não cria campos de disponibilidade observada nem relaxa o CLI estrito. As forças podem incorporar partidas anteriores de 2024/2025 somente pela regra hipotética congelada.

## Retorno hipotético nos mesmos 368 jogos

| Versão | Apostas | Acertos | Saldo líquido | ROI sobre valor apostado |
| --- | ---: | ---: | ---: | ---: |
| Modelo anterior bruto, congelado em 2024 | 297 | 85 | **−39,641u** | **−13,35%** |
| Novo xG sem calibração — diagnóstico | 340 | 102 | **−27,967u** | **−8,23%** |
| Novo xG calibrado — candidato principal | 312 | 83 | **−68,700u** | **−22,02%** |

O candidato principal perdeu 29,059u a mais que o anterior. A versão sem calibração perdeu 11,674u a menos, mas esse resultado secundário não justifica promovê-la. Não houve versão positiva.

O mercado sem margem, aplicado às mesmas odds que o originaram, não produziu apostas pelo filtro de edge positivo. Seu ROI é indefinido por ausência de stake, não um retorno de investimento de 0%.

As odds são agregadas retrospectivas, sem prova de casa, horário de oferta ou aceitação. Os saldos são pagamentos contrafactuais nessas cotações; não representam dinheiro ganho/perdido em operação real.

## Qualidade das probabilidades

Brier médio: menor é melhor. Comparações devem ser feitas dentro de cada linha; 1X2 soma três classes e os mercados binários usam a classe positiva.

| Mercado | Anterior bruto | Novo xG bruto | Novo xG calibrado | Mercado sem margem |
| --- | ---: | ---: | ---: | ---: |
| 1X2 | 0,613903 | 0,603280 | **0,601410** | **0,580211** |
| Over/under 2,5 | **0,249801** | 0,251101 | 0,250973 | **0,242638** |
| Ambas marcam | **0,248318** | 0,253262 | 0,251512 | 0,249036 |

O novo candidato melhorou a média de 1X2 contra o modelo anterior e piorou over/under e ambas marcam. Contra o mercado, ficou pior nos três. O log-loss apresenta a mesma direção dessas comparações. A calibração reduziu um pouco os erros médios do novo modelo bruto, mas alterou as escolhas de apostas e piorou o retorno desta regra.

Foram feitas 2.000 reamostragens pareadas de **33 semanas**, carregando as mesmas partidas e também os casos sem aposta para todos os modelos. A diferença de Brier do calibrado menos o anterior em 1X2 foi −0,01249, com intervalo descritivo de 95% [−0,02710; +0,00109]. A diferença de saldo por fixture foi −0,07896u, intervalo [−0,22441; +0,05510]. Ambos incluem zero: não estabelecem melhora ou piora universal fora desta amostra.

Esses intervalos não corrigem as buscas anteriores, a seleção retrospectiva da arquitetura nem a incerteza da estimação. 2025 já foi examinado no projeto; não é um novo holdout intocado. A comparação envolve candidatos completos e não isola o efeito de xG, atualização temporal ou calibração.

## Comparação entre casas

**Não avaliada com dados reais elegíveis.** Os históricos identificados foram recebidos após as partidas e não contêm os envelopes completos e relógios necessários. Não foram inventados status, timestamps ou casas para alimentar o scanner. Os estudos encerrados de descoberta/movimento de preço e extensão de 51 IDs não foram reexecutados.

## Evidências e continuidade

Plano SHA-256: `507c69fc01aaabd9d78734b1153f740c3c347f601f5b1609cd54839a1698aaaa`.

Fingerprint do candidato: `fd63b94d185887476940340fccd211cb424e033f4058ee3aaf4a4db2a7cfb322`.

`PLANO.json`, `EXECUTION_LOCK.json` e `FORECAST_LOCK.json` preservam as decisões antes da pontuação; `forecasts.json`, `panel.json`, `event_results.json`, `results.json` e `MANIFEST.json` permitem conferir os cálculos. O adaptador condicional e a aritmética passaram em **26 testes sintéticos**, incluindo equivalência com o candidato estrito em fixtures manufaturadas e ausência de uso de informação futura.

A auditoria independente passou em **113.864 verificações**: reconciliou fontes e IDs, recalculou seleções e pagamentos sem importar o seletor/liquidador usado no teste, conferiu Brier/log-loss, drawdown e a reamostragem semanal. Isso confirma a aritmética, não a publicação histórica do xG ou a execução das odds. Os 14 hashes protegidos continuam iguais; os 477 arquivos do backup original também foram conferidos antes desta etapa.

O estudo termina com resultado negativo/misto, sem mudança de janela, lag, ano, limiares ou parâmetros para recuperar desempenho. Não houve promoção, aposta, alteração de coorte, agenda ou baseline. O resultado anterior T2 de 2026 permanece −1,23u; não deve ser comparado diretamente com este saldo anual de 2025.
