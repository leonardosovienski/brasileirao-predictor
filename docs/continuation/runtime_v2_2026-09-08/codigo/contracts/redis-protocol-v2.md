# Protocolo Redis v2: registro, cálculo e publicação condicionais

O protocolo `brasileirao.redis/2` resolve a aceitação de respostas antigas e a
reserva de processamento que permanecia consumida após falha. A versão atual
é definida pelo registro aceito atomicamente no Redis, ligado ao snapshot de
escalação usado no cálculo. `timestamp_t3` continua sendo um relógio de auditoria,
não um critério de ordenação distribuída.

O schema v1 fica preservado como histórico. O kernel v2 não aceita uma mensagem
v1 nem uma mensagem v2 válida apenas pelo schema: ela precisa coincidir com o
registro imutável e com a versão atual. Atualize produtor e consumidor juntos;
não publique mensagens v1 para tentar contornar o registro v2.

## Mensagens e estado

O canal de invocação é `system:invoke_kernel:v2`. A mensagem contém os campos do
schema v1 e `state_version`, uma string decimal positiva alocada com Redis INCR.
O valor não passa por ponto flutuante. A combinação de versão e `run_id` identifica
a execução; `idempotency_key` identifica o evento e seus inputs para repetição.

| Chave | Conteúdo / finalidade |
| --- | --- |
| `lineup_state:{match}` | Snapshot serializado de escalação registrado com a invocação. |
| `kernel:v2:sequence:{match}` | Contador persistente de versões por partida, sem TTL. |
| `kernel:v2:current:{match}` | Bytes exatos da mensagem de invocação atual. |
| `kernel:v2:request:{run}` | Hash com mensagem imutável, snapshot, status e resultado; validade de 60 segundos, sem renovação por retry. |
| `kernel:v2:identity:{idempotency_key}` | Vínculo da identidade à execução por 60 segundos. |
| `kernel:v2:lease:{run}` | Token exclusivo do processador com lease de 5 segundos. |
| `kernel:v2:pending` | Sorted set de execuções pendentes, com horário da próxima tentativa pelo relógio Redis. |
| `fair_odds:{match}` | Resultado vigente, por até 5 segundos, limitado também pela validade restante da solicitação. |

A indicação de saúde do kernel contém `protocol_version` e um `session_id`
UUID, com TTL de cinco segundos. Renovação e remoção verificam a sessão dona;
um processo antigo não renova nem apaga o token de outro. O healthcheck exige
protocolo v2, sessão válida e TTL positivo na mesma leitura Lua. O antigo flag
sem validade não comprova saúde. O heartbeat acompanha o ciclo ativo do daemon.

O resultado e sua notificação em `fair_odds_ready:{match}` carregam protocolo,
job, run, match, idempotency_key e state_version, além das cinco odds. Null continua significando
seleção indisponível. Notificação não substitui o conteúdo vigente da chave.

## Pontos de aceitação atômica

1. O produtor compara os bytes do estado que leu com o estado vigente. Se houver
   conflito, relê e recompõe o snapshot. Um registro aceito atualiza escalação,
   aloca versão, grava solicitação/current/identidade, invalida fair anterior e
   agenda o processamento na mesma operação atômica. O Worker aguarda essa
   operação; a criação da versão não fica em uma tarefa solta posterior.
2. O kernel só obtém um lease se solicitação e versão continuarem atuais e
   pendentes. Uma repetição concorrente não obtém o mesmo lease. Um token novo
   após expiração impede o processador antigo de concluir como dono.
3. A conclusão compara novamente mensagem atual, registro, snapshot e token.
   Somente o dono atual pode gravar e notificar. Falha conhecida libera apenas
   o próprio lease e mantém o trabalho recuperável. Conclusão repetida após
   resposta de rede incerta não regrava a previsão nem renova seu TTL.
4. O consumidor calcula candidatos e depois faz a comparação final dentro do
   Redis, junto da publicação do lote: execução atual, snapshot correspondente,
   resultado concluído, bytes e validade da fair odd. Uma atualização ocorrida
   durante seus awaits faz o lote antigo ser rejeitado. A emissão por execução
   é deduplicada no servidor.

O watchdog também deve comparar o snapshot esperado ao aplicar fallback e
invalidar o cálculo associado na mesma operação. Ele não pode restaurar um
snapshot lido antes de uma escalação mais recente.

## Recuperação e limites

Pub/Sub funciona como aviso para trabalho já registrado. O daemon também consulta
pendências persistidas, permitindo retomar uma solicitação após perda do aviso,
reinício do processo ou lease expirado, durante a validade original de 60 segundos.
Isso não torna a fila permanente nem autoriza processar pedidos vencidos.

Scripts Lua executam sem interleaving, mas não oferecem rollback de comandos já
executados quando um comando posterior falha. Validar tipos, argumentos e
pré-condições antes das escritas e tratar a falha de publicação faz parte do
contrato. A garantia não inclui perda de estado do servidor além da configuração
de persistência do Redis. [Documentação Redis sobre scripts](https://redis.io/docs/latest/develop/programmability/eval-intro/).

A notificação `fair_odds_ready` perdida não é recuperada automaticamente pelo MSE:
o resultado pode expirar em cinco segundos sem emissão, uma abstenção. A
recuperação automática do kernel começa após o registro aceito no Redis; antes
dele, o retry limitado do Worker não substitui uma fila durável de ingestão.

A publicação de `bet_signals` continua sendo Pub/Sub, sem confirmação de entrega
ao assinante externo. A deduplicação da emissão não é uma promessa de execução
financeira exatamente uma vez. Um sinal válido no instante de emissão não pode
ser revogado retroativamente por uma atualização posterior. [Semântica de entrega
do Redis Pub/Sub](https://redis.io/docs/latest/develop/pubsub/).

As operações são destinadas à instância Redis standalone usada pelo Compose.
Não se declara compatibilidade Redis Cluster: os scripts usam chaves de vários
slots, incluindo o índice global de pendências.

A ordem de aceitação no Redis não autentica a cronologia do provedor. O Worker
preserva `CapturedAt` e identidade por lado: descarta eventos anteriores, ignora
repetição idêntica e rejeita conflitos com o mesmo horário declarado. Snapshots
legados sem esses campos não recebem horários inventados. Uma fonte com relógio
incorreto ainda exige reconciliação na origem.

## Verificação manual

`python -m brasileirao_scripts.hotpath_smoke --match-id MATCH --redis URL` verifica
uma solicitação v2 **já registrada** pelo produtor .NET. Pode reenviar seus bytes
como aviso, mas não fabrica autoridade nem renova TTLs. A opção `--n` repete a
verificação, sem criar novos cálculos. Os tempos publicados são tempos de
verificação; não são benchmarks de cálculo novo.

Em ambiente descartável, `--synthetic-lineup --n 3` cria três partidas fabricadas
publicando os dois eventos de escalação por partida. O Worker .NET real faz o
registro; o smoke aguarda o snapshot com os dois lados e verifica o resultado.
Esse modo não escreve diretamente as chaves de autoridade do protocolo.

Testes de integração devem usar instância descartável explicitamente configurada,
dados sintéticos e caminhos separados. Não executar limpeza global em uma instância
existente. Nenhum teste deste contrato precisa abrir banco operacional, ajustar
modelos, acessar coortes ou enviar ordens.
