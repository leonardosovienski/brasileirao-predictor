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
| `kernel:v2:ready` | Sorted set de resultados concluídos, indexado por run_id e prazo absoluto da fair odd no Redis. |
| `fair_odds:{match}` | Resultado vigente, por até 5 segundos, limitado também pela validade restante da solicitação. |
| `kernel:v2:signal_outbox` | Stream dos últimos 10.000 lotes aceitos, com identidade, JSON e prazo econômico original. |
| `lineup:v2:watchdogs` | Índice persistente de partidas incompletas e seus prazos de timeout. |

A indicação de saúde do kernel contém `protocol_version` e um `session_id`
UUID, com TTL de cinco segundos. Renovação e remoção verificam a sessão dona;
um processo antigo não renova nem apaga o token de outro. O healthcheck exige
protocolo v2, sessão válida e TTL positivo na mesma leitura Lua. O antigo flag
sem validade não comprova saúde. O heartbeat acompanha o ciclo ativo do daemon.

O Worker também exige os dois loops ativos: `mse` e `inbox`. Seus heartbeats de
cinco segundos usam chaves `system:lineup_worker:health:{instance_id}:{role}`.
O instance_id padrão é o hostname, e os dois tokens precisam compartilhar a
mesma sessão. O healthcheck consulta os dois atomicamente; apenas PING no Redis
não indica que o Worker está vivo. Isso mede atividade dos loops, não cobertura
de mercado, qualidade de dados ou rentabilidade.

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
   é deduplicada no servidor. O lote entra na outbox antes do aviso Pub/Sub;
   repetir a operação após resposta incerta não cria outro registro na stream.

O watchdog também deve comparar o snapshot esperado ao aplicar fallback e
invalidar o cálculo associado na mesma operação. Ele não pode restaurar um
snapshot lido antes de uma escalação mais recente.

`WatchdogDeadlineUnixMs` registra no estado o prazo original da primeira aceitação.
Correções posteriores preservam esse prazo. Registro e índice watchdog são
atualizados juntos; quando os dois lados chegam, o índice é removido. A nova
instância do Worker consulta o índice desde a inicialização, usando o relógio
Redis, sem depender de acompanhamento em memória. Repetição idêntica pode reparar
o índice, comparando snapshot e execução atuais antes de confirmar a entrada.
Fallback e retirada do índice também são condicionais. Estados legados sem prazo
registrado não permitem reconstruir com certeza o prazo original; o sistema não
inventa esse histórico.

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

A conclusão registra o resultado no índice ready junto dos demais efeitos. O
MSE consulta esse índice desde a inicialização e a cada 100 ms, mesmo sem aviso
Pub/Sub. O cursor avança por resultados sem mercado disponível, evitando que
eles bloqueiem outros. Replays não renovam o TTL. Se a indisponibilidade durar
mais que a validade original, o resultado expira e não pode gerar novo sinal.
Nova versão, watchdog e emissão aceita retiram a referência correspondente.

A publicação de `bet_signals` continua como aviso Pub/Sub. A fonte recuperável
é a stream `kernel:v2:signal_outbox`: um registro por lote, retido até o limite
exato de 10.000 lotes. Consumidores podem usar grupos Redis e confirmação, mas
precisam verificar identidade, versão vigente e `expires_at_ms` antes de usar um
sinal. Retenção não prolonga sua validade. Nenhum executor financeiro é fornecido
por esse contrato. Deduplicação de registro não garante execução financeira
exatamente uma vez, e a retenção limitada não garante entrega a assinante ausente
indefinidamente. [Semântica de entrega do Redis Pub/Sub](https://redis.io/docs/latest/develop/pubsub/).

As operações são destinadas à instância Redis standalone usada pelo Compose.
Não se declara compatibilidade Redis Cluster: os scripts usam chaves de vários
slots, incluindo o índice global de pendências.

A ordem de aceitação no Redis não autentica a cronologia do provedor. O Worker
preserva `CapturedAt` e identidade por lado: descarta eventos anteriores, ignora
repetição idêntica e rejeita conflitos com o mesmo horário declarado. Snapshots
legados sem esses campos não recebem horários inventados. Uma fonte com relógio
incorreto ainda exige reconciliação na origem.

## Verificação manual

A entrada recuperável usa `lineup:v2:inbox`, campo `payload` com o JSON de
`LineupEvent`, e grupo `lineup-worker-v2` desde a posição `0-0`. O helper
`brasileirao_scripts.lineup_inbox.enqueue_lineup` retorna o ID armazenado. O
produtor deve repetir o mesmo evento após resposta incerta; o registro da
escalação deduplica a repetição. O helper recusa novas entradas quando há 10.000
registros, sem apagar pendências para abrir espaço.

O Worker usa XREADGROUP e recupera pendências com XAUTOCLAIM após um segundo.
Só confirma depois que o tratamento do evento termina; falhas não possuem mais
limite de três tentativas nesse caminho. Eventos devem ter 11 titulares distintos,
identidade válida e captura dentro da janela de timeout configurada (55 minutos
por padrão); captura mais de cinco minutos no futuro é recusada. Entradas
inválidas/expiradas deixam diagnóstico com ID, motivo e hash na stream
`lineup:v2:rejected` (últimos 1.000), sem ecoar seu payload. XACKDEL ACKED confirma
e limpa atomicamente, respeitando referências de outros grupos. Isso requer
Redis 8.2 ou posterior. [XREADGROUP](https://redis.io/docs/latest/commands/xreadgroup/),
[XAUTOCLAIM](https://redis.io/docs/latest/commands/xautoclaim/) e
[XACKDEL](https://redis.io/docs/latest/commands/xackdel/).

O canal legado `lineups:*` permanece compatível, com fila volátil e retry limitado.
Para as garantias de recuperação, migre o produtor para a inbox. O Redis precisa
aceitar a escrita; perda anterior a essa confirmação continua responsabilidade
do produtor. A persistência do Redis define a resistência a falhas do servidor.

`python -m brasileirao_scripts.hotpath_smoke --match-id MATCH --redis URL` verifica
uma solicitação v2 **já registrada** pelo produtor .NET. Pode reenviar seus bytes
como aviso, mas não fabrica autoridade nem renova TTLs. A opção `--n` repete a
verificação, sem criar novos cálculos. Os tempos publicados são tempos de
verificação; não são benchmarks de cálculo novo.

Em ambiente descartável, `--synthetic-lineup --n 3` cria três partidas fabricadas
armazenando os dois eventos de escalação por partida na inbox. O Worker .NET real faz o
registro; o smoke aguarda o snapshot com os dois lados e verifica o resultado.
Esse modo não escreve diretamente as chaves de autoridade do protocolo.

Testes de integração devem usar instância descartável explicitamente configurada,
dados sintéticos e caminhos separados. Não executar limpeza global em uma instância
existente. Nenhum teste deste contrato precisa abrir banco operacional, ajustar
modelos, acessar coortes ou enviar ordens.
