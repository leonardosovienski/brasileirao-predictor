# Fechamento .NET: recuperação de fair odds, outbox e saúde dos ciclos

Esta etapa usa snapshots e recibos novos em `work/pending_closure`; não modifica relatórios, resultados, planos ou recibos encerrados. A matemática de odds/edge/Kelly permanece igual.

## Falhas e mudanças

O MSE anterior dependia de `fair_odds_ready:*`: uma conclusão válida ocorrida sem assinante, durante uma desconexão ou antes da inicialização não era consumida. Agora o kernel escreve atomicamente o índice `kernel:v2:ready`, cujo membro é run_id e cujo score é o deadline real da chave fair. O MSE consulta esse índice ao iniciar e a cada 100 ms, recuperando também depois de falhas Redis. A consulta usa Redis TIME, ZSCAN com cursor e limpeza de expirados; não renova odds nem reinicia cálculos. Runs sem mercado/edge continuam disponíveis até expirar, e o cursor evita que a primeira página impeça a inspeção das seguintes. COUNT32 é uma sugestão ao Redis, não limite rígido de tamanho da resposta.

Cada recuperação volta pelo mesmo caminho de validação: fair/current/result/snapshot/TTL e identidade completa, com repetição de todos os fences no script final. Novo registro e watchdog removem do ready a execução superada. Aceitação final e replay já concluído removem o membro ready. O índice é apenas uma pista para localizar resultados; não concede autoridade para emitir.

Falha Redis ou JSON na auditoria de latência deixa diagnóstico no log e não impede a retenção se os fences econômicos passam. A auditoria não substitui nem relaxa essas verificações.

## Outbox explícita, sem executor financeiro

`kernel:v2:signal_outbox` é um Redis Stream. O script final valida tipos, identidades e permissões de escrita antes de mutações, faz um único `XADD MAXLEN = 10000` por lote, grava o marcador de deduplicação e remove ready. Somente depois tenta o aviso Pub/Sub com `pcall`; ausência de assinantes ou negativa de PUBLISH não apaga o lote. XADD negado/tipo inválido não deve consumir o marcador nem a pista ready. Retorno positivo do script significa lote retido na outbox, não prova de entrega Pub/Sub nem de ordem executada.

Campos do registro: `protocol_version`, `job_id`, `run_id`, `match_id`, `state_version`, `expires_at_ms`, `batch_json`. O JSON do lote concatena as representações C# individuais, preservando os doubles sem reserialização pelo CJSON Lua. O deadline econômico usa Redis TIME + PTTL fair no script final; a chave fair nunca é renovada.

Contrato para um consumidor externo futuro: usar grupo próprio via XGROUP/XREADGROUP e recuperar pendentes via XAUTOCLAIM; validar protocolo, identidade, versão corrente e deadline antes de qualquer uso; confirmar via XACK somente depois do processamento idempotente correspondente. Esse consumidor não foi criado, e nenhuma execução financeira foi inventada. MAXLEN10000 permite remover registros antigos mesmo se algum grupo não os confirmou. Persistência após reiniciar Redis depende da configuração de persistência/replicação do servidor; Stream e dedup não prometem entrega infinita nem exactly-once financeiro. Um lote válido ao ser gravado pode ficar obsoleto depois e deve ser recusado pelo consumidor.

## Healthcheck

`WorkerHealth` é compartilhado por MSE e inbox com um SessionId. As chaves `system:lineup_worker:health:{instanceId}:mse` e `...:inbox` usam TTL5s e JSON com protocolo/instance/session/role. InstanceId padrão é Environment.MachineName (hostname do container). Cada ciclo renova apenas após processamento/leitura bem-sucedido; a renovação não sobrescreve bytes de outra sessão. Cleanup compara a própria sessão antes de DEL.

O CLI `--healthcheck` verifica atomicamente ambos os JSON, TTL positivo, protocolo correto, instância esperada e igualdade de sessão. PING sem Worker retorna falha; um único ciclo saudável não substitui o outro. A detecção de parada abrupta tem a janela de até cinco segundos do heartbeat. Reinício enquanto a sessão antiga ainda tem lease pode aguardar sua expiração; isso é um limite conservador de liveness, não elegibilidade econômica. O callback do inbox e seu cleanup são integrados pelo parent no Worker.

## Evidência produzida nesta etapa

- `dotnet_lost_ready_baseline.json`: regressão nova contra MSE anterior falhou após 3s, com fair/result/ready válidos e nenhum aviso. `dotnet_ready_outbox_first.json`: cinco regressões dirigidas passaram no código novo.
- `dotnet_health_baseline_second.json`: CLI anterior retornou 0 com Redis respondendo e Worker ausente (esperado 1). `dotnet_health_green_rebuild.json`: três regressões passaram no CLI/heartbeat novos, incluindo chamada de processo real ao CLI, TTL, duas sessões/instâncias e cleanup.
- A primeira tentativa do teste health teve colisão de nome Process no partial de testes. A primeira tentativa verde ainda usou DLL incremental da baseline porque a cópia preservara mtime anterior; a recompilação forçada pelo timestamp apenas no checkout isolado corrigiu isso. Nenhum desses recibos foi substituído.

Os recibos citados ficam em `work/pending_closure/validation`, vinculados à nova instância Redis isolada run_id `273e80f8cca2bcfdf62f19e6244aabc4dc5ecd06`, DB15.

## Verificação final

- `dotnet_pending_full.json`: suíte Release completa com XPlat Code Coverage, 105 testes aprovados, 1 skip reservado ao E2E entre processos, 0 falhas. Inclui as mudanças do parent no Worker/inbox e as fixtures de 11 titulares.
- Cobertura: 845/970 linhas = 87,11%; 335/402 desvios = 83,33%. Ambos gates existentes de 80% preservados e satisfeitos. XML: `work/integration-repo/artifacts/dotnet-pending-full/d29dd56a-9370-4b1c-a26f-1bca45b6f4b0/coverage.cobertura.xml`.
- `dotnet_pending_warnaserror.json`: build Release completo com `--no-restore --no-incremental --warnaserror`, zero avisos/erros.
- Os dois recibos finais confirmaram run_id antes/depois e DB15 vazio ao terminar. Os testes não usaram banco/coorte operacional, conta, modelo econômico novo nem dependências novas.
- `work/pending_closure/DOTNET_FINAL_MANIFEST.json`: hashes SHA256 e igualdade da fonte operacional com o checkout isolado de sete arquivos desta etapa; WorkerRuntimeFencingTests também contém a atualização de fixtures do parent.
- Auditoria ACL independente em Redis real, DB12, mesma instância nova: negar XADD, SET ou ZREM não gravou marker/outbox parcial e preservou ready; o replay permitido criou um lote. Negar PUBLISH reteve outbox+marker e removeu ready; replay retornou zero sem duplicar. DB12 terminou vazio. Recibo `work/pending_closure/outbox_acl_20260908T042148/audit.json`, ligado ao SHA256 final do script `1ad2128c9d82d26bed3e36d984fadd8464ad883e4f1915d60a28a5136f7a8f3f`.

As regressões adicionais verificam recuperação na inicialização e com MSE já ativo, transient Redis, pistas malformadas/ausentes, versão superada/expiração, sem assinante de saída, replay de índice/notificação sem novo XADD, limite exato de 10 mil registros, tipo de outbox inválido sem consumir retry, falha de auditoria, CLI com processo real, sessão/instância/TTL e expiração natural após parar renovações.
