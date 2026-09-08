# Kernel Redis v2 — implementação e validação Python

08/09/2026 UTC. Alterações autorizadas de transporte, ordenação, recuperação e readiness. Sem alteração das fórmulas, parâmetros, dependências, banco operacional, coortes, agendas ou ordens.

## Fonte aplicada

- `brasileirao_predictor/kernel_daemon.py`: validação v2, execução somente de request registrado, finalização atômica, poll de recuperação, supervisão das tarefas, fechamento do cliente após cleanup, sinais Windows/Unix restaurados ao encerrar e healthcheck de protocolo/liveness.
- `brasileirao_predictor/kernel_redis_v2.py`: constantes e scripts Lua Python, sem I/O ao importar.
- `tests/test_kernel_protocol.py`, `tests/test_kernel_runtime.py`, `tests/test_kernel_v2_runtime.py`, `tests/test_redis_integration.py`: contratos, ciclo de execução, cancelamento, recuperação, Redis real e heartbeat. O teste Redis anterior com FLUSHDB foi substituído.

As seis fontes operacionais foram sincronizadas com as mesmas fontes validadas no worktree. Schema v2 e produtor/consumidor .NET pertencem às outras partes desta entrega.

## Contrato coordenado

Canal de entrada `system:invoke_kernel:v2`; envelope v2 acrescenta `state_version` string decimal positiva até `9223372036854775807`. Não usa timestamp de parede como versão. O produtor Redis deve obter a string com GET após INCR e preservar os bytes dos números no payload. O kernel rejeita v1; não existe fallback que contorne o registro.

| Chave | Semântica |
| --- | --- |
| `kernel:v2:current:{match}` | String com os bytes JSON canônicos completos da invocação atual. |
| `kernel:v2:request:{run}` | Hash: payload imutável, lineup_state exato, status pending/completed e result após conclusão. TTL 60 s desde o registro, não renovado. |
| `kernel:v2:lease:{run}` | Token da tentativa, distinto de run_id; máximo 5 s, limitado ao prazo restante do request. |
| `kernel:v2:pending` | ZSET de runs com instante Redis da próxima tentativa; poll a cada 250 ms, até 32 por chamada. |
| `fair_odds:{match}` | Resultado v2 com IDs, idempotency_key e state_version; máximo 5 s, limitado ao prazo restante do request. |
| `health:kernel` | JSON protocol_version/session_id, renovado com TTL 5 s; sessão antiga não renova nem apaga o heartbeat de outra. |

`lineup_state:{match}` deve ser igual ao snapshot registrado. Claim e complete comparam tanto o payload atual quanto o snapshot. Um payload adulterado com os mesmos IDs é recusado sem remover o pending legítimo. Request expirado ou realmente substituído é retirado da recuperação. Token de tentativa vencido não pode concluir nem liberar a nova tentativa.

Scripts Python: CLAIM recebe cinco KEYS (current, request, lease, pending, lineup); COMPLETE recebe seis (current, request, lease, fair, pending, lineup); RELEASE recebe cinco como CLAIM. Os ARGV e limites ficam documentados junto das constantes. As funções .NET executam seus próprios scripts de registro/invalidação/publicação, usando o mesmo contrato.

A conclusão confere tipos, argumentos, ACL das mutações e PUBLISH antes de escrever. Grava fair, chama PUBLISH por pcall e só então marca completed/result, remove pending e libera lease. Falha de PUBLISH tratada pelo pcall remove o fair da tentativa e mantém trabalho pendente. Erros de ACL previsíveis são recusados antes da primeira escrita. Se a resposta do EVAL se perder após commit, completed impede nova gravação, renovação de TTL e nova publicação pelo kernel.

Pub/Sub de entrada é um aviso de trabalho. O request e índice pending preservados permitem recuperar perda de aviso ou de processo. O ciclo fecha/cancela tarefas da sessão antes de fechar o cliente Redis que elas usam. A liberação de tentativa é limitada a 2 s; se não puder confirmar, a reserva expira e permanece elegível à recuperação até o prazo do request.

O healthcheck usa um script atômico que exige protocolo v2, session_id e PTTL positivo. Flags antigas ou sem prazo não marcam readiness. O poll renova o heartbeat; crash ou desconexão o deixam expirar. O modo de saúde no CLI não mudou de argumentos.

## Validação nova

- **139 testes unitários passaram**, incluindo schema, números/IDs inválidos, versão acima da precisão double do Lua mantida como string, não aceitação de v1, cancelamento, liberação após falha, cliente aberto até cleanup e fallback/restauração de sinais Windows.
- **18 integrações com Redis real 8.2.1 passaram**, em instância criada para esta tarefa, loopback porta 26380 DB14, run_id conferido antes/depois; DBsize final zero. Não usaram banco/modelo operacional nem apostas.
- Ruff e formato dos seis arquivos passaram; Pyright dos dois módulos: zero erros/avisos de análise. O aviso de configuração de `.venv` ausente no worktree permanece, com interpretador operacional explicitamente fornecido.

Integrações: concorrência/replay sem renovar TTL; conclusão antiga após a nova; payload adulterado sem apagar pending; mudança de lineup sem mudança de head; resposta de conclusão perdida; lease retomado com novo token; poll após perda de wake-up/processo; deadline do request; seis negações ACL; expiração de saúde após crash; proteção contra sessão antiga; desconexão e rejeição de health legado/sem TTL.

Recibos finais:

- `work/validation/kernel_v2_unit_health.json` e `.log`.
- `work/runtime_fix/validation/kernel_v2_redis_health.json` e `.log`.
- `work/validation/kernel_v2_lint_health.json`, `kernel_v2_health_format.json`, `kernel_v2_pyright_health.json` e logs.

Testes Redis exigem `LINEUP_TEST_REDIS_URL` e `LINEUP_TEST_REDIS_RUN_ID`, endpoint loopback em porta diferente de 6379, DB não zero e identidade efetivamente correspondente. Sem opt-in, são pulados; o marker integration deve ser explicitamente selecionado. Limpeza somente de chaves/membros UUID e usuário ACL exclusivo da fixture; nenhum FLUSH. O wrapper usado foi `work/runtime_fix/runtime_redis_runner.py --db 14 ...`.

O primeiro comando Redis desta etapa deixou os testes deselecionados pelo pytest.ini; não foi registrado como aprovação. A segunda execução incluiu `-m integration` e executou as integrações. O recibo final acima inclui também heartbeat.

## Limites da evidência

Estes testes executam os scripts Lua reais, mas o registro das fixtures Python é uma transação sintética. Eles não substituem o E2E cruzado com o produtor e consumidor .NET, que está sendo feito separadamente. Não validam ainda o conjunto de containers Compose ou o SLA de latência.

O protocolo usa Redis standalone, conforme Compose; não declara compatibilidade com Redis Cluster. Scripts são atômicos quanto à concorrência, mas Redis não desfaz comandos anteriores em todo erro possível. ACL/tipos/argumentos previsíveis são verificados antes; falhas imprevisíveis de servidor/persistência continuam fora de garantia de processamento exatamente uma vez.

Pub/Sub final não tem confirmação de entrega ao assinante nem aceite de ordem. Conclusão/publcação atômicas e deduplicação no consumidor não equivalem a entrega financeira exatamente uma vez. Request tem prazo de 60 s; trabalho que não concluiu nesse prazo expira em vez de reaparecer horas depois. Lucro e utilidade preditiva não foram medidos nem inferidos nesta mudança.
