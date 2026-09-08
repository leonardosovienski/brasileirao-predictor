# Revisão de integração e fronteiras atômicas

Estado final: 2026-09-08. Fontes finais de retry/overflow/saúde revisadas, recibos finais de teste conferidos e ambiente temporário removido. Revisão separada de implementação na mesma equipe; não é certificação externa.

## Ambiente real utilizado

- Redis 8.2.1 compilado do repositório oficial, tag conferida contra o commit `cd0b12938b6c99978440c6f7e44e34d7ff0aa537`. A imagem Alpine 3.22.5 foi conferida pelo SHA256 oficial. URLs, hashes e comandos estão em `redis_env_review_runtime`.
- Instância nova em `127.0.0.1:26380`, sem persistência, 16 bancos, identificada pelo run_id `97c7a9cc8a5fa8deb9387dd63a0505f8b66e9196`. Bancos reservados: 12 revisão ACL, 13 E2E, 14 Python, 15 .NET.
- Distro WSL1 própria: `codex-brasileirao-redis-20260908`, diretório `redis_env_review_runtime/distro-wsl1`. Automount dos discos Windows e interop desativados. Nenhuma distro existente foi iniciada ou modificada.
- WSL2 falhou com `HCS_E_HYPERV_NOT_INSTALLED`. Docker CLI existe, mas o daemon não responde. Docker/Compose E2E permanece não executado; Redis real em WSL1 não substitui essa verificação.
- Wrapper `runtime_redis_runner.py` confere identidade do servidor antes/depois, usa ambiente permitido explicitamente e o worktree isolado. Opções E2E propagam os nomes `LINEUP_E2E_PYTHON`, `LINEUP_E2E_KERNEL_SCRIPT`, `LINEUP_E2E_REDIS_URL`, `LINEUP_E2E_REDIS_RUN_ID`.

## Falhas encontradas e verificações realizadas

1. **Deduplicação antes de publicação com erro ACL.** A versão inicial de `PublishSignals` gravava o marcador e depois falhava em `PUBLISH`. Redis não revertia o marcador; a repetição autorizada retornava zero e perdia o sinal. O patch faz preflight das permissões de todas as publicações e do marcador. Redis real confirmou marcador ausente sob falha e repetição autorizada retornando um. Evidência definitiva: `lua_boundary_audit_20260908T033058/audit.json`.
2. **Concatenação dos literais Lua no C#.** `Checks +` um literal bruto removia as quebras de linha das bordas e gerava `endkind`, recusado por Redis. O agente acrescentou separador explícito `"\n"`. O mesmo probe real passou após o ajuste. Há snapshot da versão com erro em `lua_boundary_audit_20260908T032925`.
3. **Conclusão Python e falha de HSET após PUBLISH.** A ordem anterior permitia escrita/publicação parcial se a permissão de `HSET` estivesse ausente. O agente adicionou preflight. O probe atualizado retornou `ACL_DENIED`, preservou request pendente e lease, e não escreveu fair nem produziu notificação. O teste usa seis chaves, incluindo snapshot da escalação. O probe anterior com cinco chaves era incompatível com essa revisão e não constitui falha do código.
4. **Ciclo registro/lease/conclusão/fence.** Na revisão estática atual, igualdade de bytes da invocação, snapshot, token, versão e validade é novamente verificada na fronteira final. Registro novo invalida fair/lease anterior; uma conclusão antiga não pode sobrescrever a atual. O consumidor usa o snapshot registrado, sem misturar VORP de execução posterior.

Todos os probes ACL usaram somente chaves UUID próprias no banco 12 e usuários ACL temporários. O banco voltou ao tamanho zero; nenhum FLUSHDB/FLUSHALL foi executado e nenhum usuário preexistente foi alterado.

## Ajustes finais de fila, saúde e harness

- `ProcessQueueAsync` agora tenta o mesmo evento até três vezes apenas para `RedisConnectionException`/`RedisTimeoutException`, com esperas de 100/200ms entre tentativas. O retry relê estado, respeita CAS e os campos de captura por lado. Após resposta incerta de registro efetivado, a repetição idêntica mantém o acompanhamento de watchdog sem criar outra versão. Erros permanentes ou esgotamento são registrados; recuperação além desse limite ainda depende da fonte.
- `DropOldest` passou a usar o callback com o item efetivamente expulso, conservando o item novo na fila e produzindo fallback para a identidade correta. [Microsoft: canais limitados](https://learn.microsoft.com/en-us/dotnet/core/extensions/channels#bounded-creation-patterns).
- Saúde Python passou a ter TTL de 5 segundos e identidade de sessão. Release só remove o próprio token; uma sessão antiga não apaga saúde publicada por outra. Renovação está ligada à recuperação ativa do daemon. Não foi encontrada nova falha impeditiva nessas mudanças na leitura final.
- A pedido do responsável .NET, esta revisão implementou o harness de `WorkerRuntimeTests`: classe partial/coleção serializada, opt-in por URL loopback DB15 e run_id, recusa banco previamente não vazio, cleanup de chaves novas e caminho temporário conferido. Corpos dos testes ficaram sob responsabilidade do agente .NET.
- A primeira execução do novo harness compilou, mas expôs duas falhas do próprio setup: `INFO` via `ExecuteAsync` exige `AllowAdmin` nesta versão do cliente e xUnit pode omitir Dispose após Initialize falhar. Foram corrigidas com opção explícita e try/catch que fecha conexão/libera lock sem apagar chaves. A rodada falha deve permanecer nos recibos; não conta como aprovação do runtime.

## Limites mantidos explicitamente

- Recuperar o aviso perdido de invocação pelo índice pending não garante recuperar uma notificação `fair_odds_ready` perdida pelo MSE. A emissão final continua Pub/Sub, sem ACK do consumidor. Não descrever isso como entrega financeira exatamente uma vez.
- Os contratos v2 e os schemas revisados descrevem corretamente Redis standalone, validade original de 60 segundos, lease/fair de até 5 segundos, versão decimal sem conversão por float, rejeição de registros obsoletos e ausência de rollback Lua. Produtor e consumidor devem migrar juntos.

## Verificação final e encerramento

- Python: 139 testes passaram em `../validation/kernel_v2_unit_health.log`; 18 integrações Redis reais passaram em `validation/kernel_v2_redis_health.log`.
- .NET: `validation/dotnet_v2_fourth.log` registra 81 aprovados, zero falhas e um skip do teste que exige processo Python. Cobertura conferida no XML dessa execução: 695/807 linhas (86,12%) e 233/290 ramos (80,34%). Esse teste foi executado separadamente com as variáveis explícitas: `validation/runtime_v2_cross_process.json/.log` registra um aprovado, zero falhas e zero skips. O caso exercita processo Python real, Redis real, registro .NET/MSE, recuperação após aviso inicial perdido, smoke sintético com Worker e deduplicação. Isso não equivale a Compose E2E.
- A suíte contém regressões de estado intercalado, lease expirado, resposta de EVAL incerta, publicação negada, tipos inesperados, duplicação, retry pré-registro e identificação do item descartado. Os probes desta revisão acrescentam evidência direta de ACL no Redis 8.2.1.
- Após o responsável confirmar término dos testes, o cleanup conferiu novamente run_id e PID12, inclusive no arquivo da distro, e o caminho absoluto de instalação dentro do scratch. Executou `SHUTDOWN NOSAVE`, aceitou EOF como resultado esperado e removeu somente a distro `codex-brasileirao-redis-20260908`.
- `redis_env_review_runtime/cleaned.json` registra término às 03:49:27 UTC, com porta26380 sem aceitar conexões. A listagem final mostra somente as duas distros Docker originais, ambas paradas em WSL2. Scripts, arquivos de fonte e recibos foram preservados.
- O E2E tinha 12 chaves sintéticas ao terminar; no instante do cleanup o banco13 tinha seis após expirações normais. Bancos12/14/15 estavam vazios. Não houve leitura de conteúdo dessas chaves, FLUSHDB/FLUSHALL ou acesso a banco operacional.
- Nenhuma nova falha impeditiva foi identificada no escopo final. Permanecem os limites declarados de Pub/Sub, validade dos pedidos, retry limitado e Compose não executado.

Fontes primárias do provisionamento: [Redis 8.2.1](https://github.com/redis/redis/releases/tag/8.2.1), [commit oficial](https://github.com/redis/redis/commit/cd0b12938b6c99978440c6f7e44e34d7ff0aa537), [Alpine oficial](https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/x86_64/), [importação de distro WSL](https://learn.microsoft.com/en-us/windows/wsl/use-custom-distro).
