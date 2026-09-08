# .NET runtime v2 — implementação e verificação

O Worker registra o snapshot de escalações e a invocação corrente no mesmo script Redis, com comparação dos bytes do estado anterior. O contador por partida vem de INCR e é serializado como string decimal; o script não reserializa os doubles de entrada. O consumidor só publica sinais depois de uma segunda validação atômica de todos os snapshots, imediatamente junto da publicação do batch.

## Interfaces e fronteiras

`MarketStateEngine.InvokeKernelAsync(matchId, eloA, eloB, updatedState, expectedStateJson, sourceEventId, stateTtl, ct)` retorna `KernelRegistrationResult(Status, PayloadJson)`. Status possíveis do script: `registered`, `duplicate`, `superseded`, `conflict`. Conflitos de estado fazem o Worker reler e mesclar o outro lado. Duplicatas retornam o pedido canônico sem renovar seu TTL; pedidos superados não voltam a ser correntes.

`KernelRedisProtocolV2` contém exclusivamente os scripts C# de registro, publicação final de sinais e watchdog. Claim, lease, conclusão e polling pertencem ao módulo Python separado. Invocações usam `system:invoke_kernel:v2`, `protocol_version=brasileirao.redis/2`, `state_version` e `idempotency_key`. O consumidor exige a correspondência desses campos, job/run/match, bytes exatos da notificação/chave e o snapshot de escalações registrado. Os sinais publicados incluem protocol/job/run/state_version.

O registro invalida fair odds anteriores, remove o pending e lease superados e cria o pedido durável de 60 segundos. Uma publicação de wakeup negada não perde esse pedido; o polling Python pode recuperá-lo. A publicação final exige pedido completed/result consistente, fair odds com TTL positivo, estado corrente e dedup por run. Todas as permissões de publicação são verificadas antes do marcador, para não consumir a tentativa quando PUBLISH é negado por ACL. O watchdog compara o estado e a invocação corrente antes de gravar fallback e invalidar current/fair/pending/lease juntos.

## Fila e ordem declarada

O mesmo evento capturado é tentado até três vezes para RedisConnectionException ou RedisTimeoutException, com esperas de 100 e 200 ms canceláveis. O CAS e a identidade do evento tornam seguro repetir após resposta incerta de um registro já aceito. O replay idêntico também restaura o acompanhamento de timeout em memória. Erros permanentes não entram em repetição infinita.

Channel DropOldest agora usa o callback da API para registrar fallback do item realmente expulso. TryWrite pode retornar true ao expulsar o item anterior; o teste confirma tanto o nome/lado do descartado quanto a permanência do evento mais recente.

Por lado, o novo estado guarda CapturedAt e hash da representação recebida. Captura menor é ignorada; captura igual exige evento idêntico, e conflito com a mesma captura é rejeitado. Isso compara o relógio declarado pelo evento; não autentica a cronologia nem a revisão do provedor. Estados legados sem relógio por lado não recebem timestamps inferidos.

## Verificação concluída

- `dotnet test dotnet/LineupWorker.Tests/LineupWorker.Tests.csproj --configuration Release --no-restore --collect:"XPlat Code Coverage" --results-directory artifacts/dotnet-runtime-v2-fourth`, via runner com allowlist e identidade da instância: 81 passed, 1 skip reservado ao E2E entre processos, 0 failed.
- Cobertura: 695/807 linhas (86,12%), 233/290 desvios (80,34%); ambos gates de 80% preservados e satisfeitos.
- Recibo: `work/runtime_fix/validation/dotnet_v2_fourth.json`; XML: `work/integration-repo/artifacts/dotnet-runtime-v2-fourth/68340292-cc2b-443a-974b-75cf1bab4e49/coverage.cobertura.xml`.
- Redis temporário 8.2.1, porta 26380, DB15, run_id `97c7a9cc8a5fa8deb9387dd63a0505f8b66e9196` conferido antes/depois. DB15 terminou vazio. Sem FLUSHDB; o harness recusa DB15 já ocupado, preserva chaves preexistentes e remove somente chaves da execução aceita.
- As duas primeiras tentativas foram bloqueadas por assinatura de Expiration no teste novo. A terceira compilou e revelou erro de inicialização do harness: INFO sem AllowAdmin e sem liberação do semáforo no erro. Ambos corrigidos; a quarta execução passou.
- Revisão independente de ACL: o teste Redis real do reviewer reproduziu perda do marker na versão anterior e confirmou marker ausente quando PUBLISH é negado na versão corrigida. Evidência: `work/runtime_fix/lua_boundary_audit_20260908T033058/audit.json`.
- Build final Release `--no-restore --warnaserror`: 0 avisos, 0 erros, recibo `work/runtime_fix/validation/dotnet_v2_warnaserror.json`.
- O parent concluiu o E2E real .NET/Python em DB13: 1 passed, 0 skipped. Pedido registrado antes de iniciar o daemon foi recuperado pelo polling, gerou fair odds e um batch corrente; o smoke de escalação sintética também atravessou o Worker real. Recibo `work/runtime_fix/validation/runtime_v2_cross_process.json`.
- `work/runtime_fencing/DOTNET_FINAL_MANIFEST.json` contém hashes SHA256 de 12 arquivos atribuídos ao agente e igualdade byte a byte entre fonte operacional e checkout isolado. O teste E2E, CI, schemas e módulo Python são responsabilidade do parent/outro agente.

As regressões cobrem registro/dedup/TTL, precisão dos inputs, invalidação de execução anterior, CAS depois das leituras do consumidor, batch único, fair sem TTL, request pending, estado divergente, ausência de snapshot/mercado, watchdog com snapshot velho, merge concorrente dos lados, replay atrasado, DropOldest, falhas antes de registrar e resposta perdida depois do commit.

## Limites

Não há entrega garantida de eventos que nunca chegaram ao Worker, sobreviveram apenas em RAM antes de uma queda, ou esgotaram as três tentativas. O pedido registrado tem janela absoluta de 60 segundos para recuperação. Pub/Sub não fornece ACK do consumidor final, persistência de sinais, nem prova de execução de ordem. A autoridade é a aceitação serializada neste Redis standalone, não um consenso externo nem autenticação da origem. Preflight evita erros previsíveis de tipos/ACL; scripts Lua não prometem rollback de falhas extraordinárias de memória/servidor após uma escrita.

Nenhuma fórmula de modelo, regra econômica, agenda, coorte ou dado operacional foi alterado por esta etapa.
