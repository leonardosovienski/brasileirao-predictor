# Correção das falhas pendentes do runtime — 8 de setembro de 2026 UTC

O trabalho corrige o ciclo de registro, cálculo e emissão de sinais entre o
Worker .NET e o kernel Python. A versão aceita no Redis passa a acompanhar o
snapshot da escalação até a publicação final. As fórmulas do modelo, os critérios
econômicos, as coortes e os estudos encerrados não fazem parte dessa alteração.

## Correções implementadas

- **Resposta antiga substituindo a nova:** o protocolo v2 registra uma versão
  por partida e uma solicitação imutável. A conclusão verifica novamente a
  versão atual, os bytes da solicitação, o snapshot e o token do processador.
  Uma execução antiga não pode sobrescrever a vigente.
- **Sinal antigo após operações assíncronas:** o consumidor confere a execução,
  o snapshot, a fair odd e seu TTL dentro do mesmo script Redis que publica o
  lote. Uma mudança ocorrida durante suas leituras invalida a emissão antiga.
- **Falha consumindo a reserva:** trabalho pendente e concluído são distintos.
  O lease dura no máximo cinco segundos e só seu dono pode liberá-lo. Falhas e
  respostas incertas não transformam uma reserva em conclusão. A repetição de
  uma conclusão já aceita não renova a previsão nem a publica novamente.
- **Perda do aviso inicial:** a solicitação registrada entra num índice de
  pendências. O daemon consulta esse índice e pode retomar trabalho após perda
  do Pub/Sub ou reinício, durante a validade original de 60 segundos.
- **Mistura de versões da escalação:** registro e atualização do snapshot são
  atômicos, com comparação do estado lido. O Worker aguarda o resultado e relê
  o estado em caso de conflito. Eventos antigos/repetidos são tratados por lado;
  conflitos no mesmo horário declarado são recusados. O watchdog também compara
  o estado antes de aplicar fallback e invalidar a execução associada.
- **Falhas de publicação dentro de Lua:** permissões e tipos relevantes são
  verificados antes das mutações. Os testes reais de ACL confirmaram que uma
  publicação negada não deixa o sinal marcado como enviado. Scripts Lua não
  fazem rollback automático de comandos anteriores a um erro.
- **Fila e saúde do processo:** a entrada trata falhas transitórias com retry
  limitado do mesmo evento e observa o item realmente descartado por lotação.
  O heartbeat do kernel tem TTL e token de sessão; uma sessão antiga não remove
  a indicação de saúde de outra, e a indicação expira após parada abrupta.

O smoke foi migrado para v2. Pode verificar uma solicitação já registrada ou,
em ambiente descartável, enviar escalações fabricadas ao Worker real. Ele não
escreve diretamente as chaves que autorizam o cálculo. O workflow de CI passou
a identificar sua própria instância Redis e a usar o novo modo de smoke.

## Validação

| Verificação final | Resultado |
| --- | --- |
| Unitários Python do kernel | 139 passaram |
| Unitários do smoke migrado | 12 passaram |
| Integrações Python com Redis real | 18 passaram |
| Suíte .NET com Redis real | 81 passaram; 1 caso entre processos adiado para execução separada |
| Integração entre processos .NET/Python | 1 passou, sem skips; inclui recuperação, deduplicação e smoke pelo Worker real |
| Cobertura .NET | 695/807 linhas (86,12%); 233/290 ramos (80,34%); ambos os gates existentes de 80% passaram |
| Build .NET Release com warnings como erros | Sem erros ou warnings |
| Ruff, formato e Pyright dirigidos | Passaram; Pyright verificou os dois módulos do kernel e o módulo de smoke |
| Schemas e estrutura do workflow | Passaram nas verificações locais |

Os 151 unitários Python são a soma das duas suítes dirigidas; não representam
uma nova execução de toda a suíte Python do projeto. O caso .NET inicialmente
pulado foi executado e aprovado separadamente. Revisão e testes foram internos,
com divisão de implementação e conferência dentro da mesma equipe.

Os números e recibos finais estão em `estado.json`. Foram usados dados sintéticos,
worktree isolado, ambiente por lista permitida e bloqueio de rede externa Python.
O Redis de teste foi compilado da fonte oficial na versão 8.2.1 e executado numa
distro WSL1 criada apenas para esta etapa, com porta própria e run_id conferido.
Nenhuma instância operacional foi limpa ou reutilizada.

A validação distingue testes unitários, scripts Lua com Redis real e execução
entre processos Python/.NET. O teste entre processos registra uma solicitação
antes de iniciar o kernel, exige recuperação pelo índice de pendências, confere
o resultado e o sinal e repete mensagens para verificar deduplicação. O modo de
escalação sintética também atravessa a fila e o produtor .NET reais.

O teste entre processos substitui apenas o carregamento de parâmetros do banco
por uma tupla sintética. O daemon, o cálculo, o Redis e o consumidor são reais;
isso não valida parâmetros financeiros nem a origem dos dados. Ao terminar, o
Redis temporário foi encerrado e sua distro removida; a porta 26380 deixou de
aceitar conexões. O recibo de limpeza registra 03:49:27 UTC.

Docker/Compose E2E não foi executado nesta máquina. O daemon Docker não estava
disponível, e a tentativa isolada de WSL2 retornou
`HCS_E_HYPERV_NOT_INSTALLED`. A alternativa WSL1 permitiu testar Redis real;
ela não comprova build, volumes, rede ou ciclo de vida dos containers. O workflow
foi atualizado, mas não se afirma uma execução remota do CI.

## Uso, migração e limites

Produtor e consumidor precisam usar `brasileirao.redis/2` juntos. O schema v1
foi preservado como histórico; mensagens v1 não passam pelo novo kernel. Código
e testes locais não equivalem a uma implantação em serviços operacionais.

O protocolo visa Redis standalone. O TTL de 60 segundos não é uma fila permanente,
e o contador/versionamento não autentica o relógio do provedor. A proteção por
lado utiliza `CapturedAt` declarado; dados legados sem esse campo não recebem
horários inventados.

Pub/Sub continua sem confirmação de entrega. Se o MSE perder a notificação
`fair_odds_ready`, a previsão pode expirar sem emissão. Um sinal aceito no instante
da publicação não pode ser revogado retroativamente. Deduplicar a emissão não
garante execução financeira exatamente uma vez. Essas restrições continuam
explícitas no contrato, sem novas filas ou adaptadores de bolsa nesta etapa.

Nenhum backtest ou ajuste econômico foi repetido. As quatro correções de pesquisa
da revisão anterior foram preservadas. Os resultados financeiros anteriores
continuam sendo os mesmos; esta entrega corrige software e não demonstra lucro.

## Evidências preservadas

`before.json` identifica o estado inicial. `estado.json` registra fontes finais,
testes, limites e hashes protegidos; `backup_receipt.json` identifica a cópia
persistente. Os recibos incluem tentativas que falharam e verificações que não
executaram testes, claramente separadas das aprovações finais. Relatórios e
manifests de estudos encerrados não foram reescritos.

As decisões de atomicidade e entrega seguem a documentação primária de
[scripts Redis](https://redis.io/docs/latest/develop/programmability/eval-intro/)
e [Pub/Sub](https://redis.io/docs/latest/develop/pubsub/). O servidor de teste usa
a [fonte oficial Redis 8.2.1](https://github.com/redis/redis/releases/tag/8.2.1).
