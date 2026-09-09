# DC-20260909 — dados obtidos, testes e pendências

**Estado: aquisição histórica concluída; critérios econômicos ainda não atendidos.
Continuidade prospectiva agendada. Lucro executável não demonstrado.**

Trabalho de 09/09/2026 em `C:/BRASILEIRAO`, base local main
`5dec2521bab581d5dda104d954f4cc6274b74702`. O mandato original foi preservado.
Esta rodada sucede PF-20260909; não altera seus protocolos nem apaga resultados.

## Pergunta, mecanismo e prioridade

É possível observar oferta Bet365 e referência Pinnacle identificadas e
contemporâneas, suficientes para medir vantagem após custos e executar uma
validação econômica? O mecanismo é diferença de preço entre casas distintas;
a oferta não participa da referência. A incerteza dominante era a aquisição
e a admissibilidade do preço. Novos ajustes de xG continuam sem prioridade.

O [protocolo](PROTOCOL.md) foi registrado antes de novos preços/desempenho;
o [complemento](ACQUISITION_ADDENDUM.md) definiu o replay closing e o piloto
regional antes de sua avaliação. Não houve busca de novo filtro após o saldo.

## Dados efetivamente providenciados

| Insumo | Obtido e verificado | Limite de uso |
| --- | --- | --- |
| OddsPapi, Série A Jan–Jun/2026 | 177/177 arquivos de timelines; 623.271.596 bytes; hashes conferidos | Exploração histórica, sem clocks de recebimento na época nem calendário PIT |
| Football-Data BRA.csv | CSV oficial recuperado pelo host sem www; 380 jogos de 2025 | Closing retrospectivo; aviso de referência Pinnacle desatualizada |
| Catálogo de bookmakers | Identidades distintas pinnacle, bet365 e bet365.bet.br; cloneOf=null no catálogo | Não prova independência econômica completa nem execução |
| Calendário prospectivo | 21 fixtures elegíveis; primeiro selecionado antes de abrir odds | Calendário atual adquirido por esta pesquisa; preservar revisões futuras |
| Piloto atual | 3 payloads do mesmo fixture, par Pinnacle/Bet365 Brasil, início/recebimento/HTTP Date/hash | 1 evento independente; bookmaker ofertante inativo nas 3 capturas |
| Fontes contratuais | Documentação de fonte, quota, estados, termos Bet365 BR e referência fiscal de 2025 | Condições pessoais, custos e limites efetivos não inferidos |

No histórico OddsPapi, 22 arquivos existentes foram reaproveitados e 155 novos
arquivos válidos foram obtidos. Houve 156 tentativas novas de histórico: uma
ConnectionResetError, preservada no manifesto, foi recuperada conforme
[reparo delimitado](REPARO_TRANSPORTE.md). Nenhum jogo foi substituído.
O universo de 177 veio de metadados anteriores e inclui faltantes/inativos na análise.

O host `www.football-data.co.uk` respondeu 503. O endereço oficial
`football-data.co.uk/new/BRA.csv` respondeu 200. O bloqueio de aquisição daquela
fonte foi resolvido; o problema de validade dos preços é separado.
As [notas oficiais](https://football-data.co.uk/notes.txt) identificam as colunas
com C como fechamento; a [página Brasil](https://football-data.co.uk/brazil.php)
fornece o arquivo. Não tratar as colunas Max/Avg como bookmaker.

## Resultado do histórico temporal

Em T−60, 176/177 eventos tinham vetor Pinnacle ativo completo e 155/177 tinham
vetor Bet365 ativo completo. A interseção foi 154/177. Em 15 eventos Pinnacle
tinha todas as últimas mudanças dentro de 120s; em Bet365, nenhum.

Isso mede idade da última mudança registrada, não idade de uma observação
contínua do feed. Um preço que não mudou pode permanecer disponível; a timeline
não demonstra essa disponibilidade nem o recebimento local naquele instante.
Não preencher clocks ausentes nem relaxar 120s/30s para produzir aprovação.
Resultado: **zero pares admitidos para execução; zero seleções condicionais
sob os critérios temporais declarados**. 154 rejeições por idade de mudança,
23 por par ativo incompleto. Nenhum placar de 2026 foi utilizado.

O [contrato OddsPapi de histórico](https://oddspapi.io/us/docs/get-historical-odds)
documenta estado ativo, createdAt e limit. Esses campos ajudam a reconstruir
estados, mas não equivalem a recibos de aceitação ou limites garantidos ao usuário.

## Replay closing 2025 — resultado condicional e referência comprometida

O CSV tinha 336 vetores Pinnacle e 202 Bet365 não vazios; 158 pares eram numericamente
completos. Congeladas as escolhas antes de interpretar HG/AG/Res, a regra fixa
selecionou 32 apostas hipotéticas. Preservaram-se 348 abstenções: 222 sem par
numérico completo e 126 fora do critério de seleção.

Referência proporcional Pinnacle, oferta Bet365, um pick por jogo, EV de cenário
positivo e <=15%, custo 2% por stake, banca 100u e stake 1u. Toda a exposição de
uma data foi reservada antes da liquidação hipotética daquela data.

| Conta do cenário | Valor |
| --- | ---: |
| Banca inicial / aportes | 100u / 0u |
| Stakes | 32u |
| Retornos incluindo principal | 23,40u |
| Fricção hipotética | 0,64u |
| Resultado líquido | **−9,24u** |
| Banca final / principal pendente | 90,76u / 0u |
| ROI sobre stakes | −28,875% |
| Retorno sobre banca | −9,24% |
| Exposição simultânea no cenário diário | 3u |

Sem fricção adicional, as mesmas seleções perderam 8,60u; com 1/2/3/5%, perderam
8,92/9,24/9,56/10,20u. Sete vitórias. Sem a maior vitória, o saldo seria −12,22u.
Bootstrap exploratório por 34 semanas, 2.000 réplicas, semente 20260909:
intervalo percentil 95% de ROI [−89,93%; +52,50%]. A amplitude e o uso prévio de 2025
impedem confirmação; o bootstrap não corrige defeitos de fonte.

**Aviso de qualidade encontrado após o cálculo:** a
[própria Football-Data](https://football-data.co.uk/data) informa problemas de
atualização das odds Pinnacle desde 23/07/2025. Todas as 32 seleções deste cenário
ocorrem depois dessa data. O resultado original foi preservado e recebeu uma
auditoria de qualidade separada; não se refez o teste removendo datas ruins.

Portanto, −9,24u é um resultado aritmético condicional sobre referência
comprometida. Não é ROI executável, validação econômica ou refutação geral de
diferenças entre casas. Nenhuma aposta real foi enviada.

## Piloto prospectivo e condições de execução

Fixture `id1000032566887012`, Coritiba FC PR x CA Paranaense PR, kickoff observado
12/09/2026 00:00UTC. Três capturas independentes da operação existente foram
obtidas em 09/09, com tempos de resposta de 1,243s, 1,079s e 1,819s. São três
observações de um único evento, não três partidas independentes.

A Bet365 Brasil apresentou `bookmakerIsActive=false`, embora os campos de
seleção estivessem ativos. As três capturas foram rejeitadas como pares de preço.
O novo teste de regressão exige respeito ao estado do bookmaker, mercado e
seleção. Pinnacle tinha limites reportados 450, mas sem moeda comprovada nesse
payload; Bet365 Brasil tinha limit=null. Não converter esses números em capacidade.

Os [termos da Bet365 Brasil](https://help.bet365.bet.br/s/pt-br/terms-and-conditions)
admitem recusa total/parcial e ofertas alteradas, e condicionam validade à
confirmação de aceite. Isso impede usar um preço de feed como fill garantido.
A [referência fiscal da Receita para 2025](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/formularios/impostos/pagamento-aposta-de-quota-fixa-e-fantasy-sport/aplicativo.html)
também não transforma 2% por stake em imposto real: ano, base de cálculo e
condições aplicáveis precisam ser parametrizados antes de uma conclusão líquida.

## Custos, acesso e alternativas

Conta OddsPapi existente confirmada em endpoint não tarifado. A identificação
do plano 250 foi reconciliada com a [oferta oficial gratuita](https://oddspapi.io/us/sign-up)
e a [política de quota](https://oddspapi.io/us/docs/requests-and-quota).
Histórico e consulta de conta não incrementam a cota conforme o contrato.
Contador inicial 62, final 67 de 250: **cinco consultas de quota gratuita**, usadas
em catálogo de casas, fixtures e três capturas atuais. Restam 183, incluindo
reserva 20 preservada. Não houve contratação, compra, renovação nem aposta.
A primeira consulta final falhou; o recibo foi conservado e nova consulta
retornou 200 confirmando 67. Total de consultas de conta: 5, incluindo a falha.

The Odds API histórico permanece alternativa paga conforme sua
[documentação](https://the-odds-api.com/historical-odds-data/), sem consumo
autenticado nesta rodada. Acesso/APIkey/plano histórico não foram presumidos.
Odds-API.io tem [restrições no nível gratuito](https://odds-api.io/pricing/free)
para casas sharp; não se abriu conta. Betfair descreve diferenças entre preços
negociados e ladders/volume no [guia oficial](https://betfair-datascientists.github.io/data/usingHistoricDataSite/);
o caminho de download exige login, não realizado. Falhas de PDF foram registradas
e não houve contorno. Esses levantamentos não esgotam todas as fontes do mundo.

Continuam desconhecidos: custo total real, capacidade da oferta, slippage,
aceitação, liquidez, limites pessoais e validação futura suficiente. Não registrar
zero para esses campos. O desembolso adicional realizado nesta rodada foi zero.

## Testes, isolamento e reprodução

Passaram **138 testes** (80 existentes e 58 novos), lint/formatação Ruff e
Pyright dos três novos módulos. Uma implementação separada com Fraction,
sem importar os módulos de produção, confirmou as 32 escolhas, retornos e −9,24u.
Foi feita pelo mesmo pesquisador, não por revisor externo.

Seis verificações de fronteira UTC e execução fora da janela confirmaram que
o acompanhamento retorna WAITING sem abrir credencial ou fazer requisição.
O coletor futuro e a auditoria executam em processos separados.
A tipagem final incluiu explicitamente os três módulos, pois a configuração
do runtime exclui pesquisa. Corrigiu-se o estreitamento de tipo do limite
opcional e adicionou-se uma regressão que falhou antes da correção: status
booleano não pode representar o código numérico de pré-jogo. Os três
payloads do piloto conservaram resultados idênticos após esse endurecimento.
Versões anteriores, falhas e recibos da verificação foram preservados.

Pesquisa em Python 3.13.12; pytest 8.4.2, Ruff 0.12.12, Pyright 1.1.405. Auditorias
e testes impediram rede, SQLite, subprocessos e leitura de DADOS_PRESERVADOS/
dados operacionais; escritas foram limitadas às novas saídas. Somente os
processos de aquisição isolados tiveram acesso pontual à chave de dados.
Não houve uso de resultados H14/H15/H9/A1, alteração de contratos, agendas,
observadores, dependências compartilhadas, serving, banco ou Redis.
Não foi instalada a aplicação operacional completa, nem executado build/.NET/Compose.

[Reprodução e caminhos](REPRODUZIR.md) detalham entradas, scripts e recibos.
Dados brutos e termos capturados permanecem fora do Git em C:/BRASILEIRAO/work.
Código, protocolos, agregados e recibos sem credenciais ficam versionados.

## Decisão e informação que muda o próximo passo

O bloqueio anterior de acesso a dados foi substancialmente reduzido: há
histórico individualizado, fonte pública recuperada e capturas reais atuais.
A qualidade econômica continua bloqueada por procedência temporal, estado
inativo da oferta e condições de execução/custos desconhecidas.

**Qual descoberta mais mudou a decisão?** Acesso existente e gratuito forneceu
177 timelines, mas dados numéricos não bastam: a fonte de fechamento avisa
desatualização e a oferta atual estava inativa no estado superior.

**Qual hipótese perdeu prioridade?** O replay closing com Pinnacle nessa fonte
não serve como validação econômica. Mais ajuste de xG continua sem resolver
o gargalo. Não se rejeitam todas as hipóteses ou todas as casas por esses resultados.

**Qual informação agora decide o próximo passo?** Um par observado antes do
corte, com bookmaker ofertante ativo e procedência verificável, seguido de
condições de capacidade/custos e validação prospectiva independente.

A [continuidade](CONTINUIDADE.md) está configurada na tarefa atual diariamente
às 19:57 de São Paulo, com captura única planejada antes de 11/09 às 20:00 locais.
Autonomia não elimina o tempo necessário às observações nem permite fabricar
informação indisponível. A rodada não declara todos os dados resolvidos.
