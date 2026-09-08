# Continuação executada — contratos do pipeline Python/Redis/.NET

**Cinco falhas mecânicas corrigidas e aplicadas ao repositório operacional. Passaram 119 testes Python e 46 testes .NET em ambiente isolado. A integração Redis/Compose permanece pendente; não surgiu evidência nova de lucro.**

Etapa de 07/09/2026, horário de São Paulo (recibos em UTC de 08/09). Base Git: `4dfdec6`, branch operacional `main`, limpa antes desta etapa. As mudanças desta etapa foram deixadas no diretório de trabalho, sem commit ou push.

## O que mudou

| Falha verificada | Comportamento corrigido | Evidência |
| --- | --- | --- |
| Todas as escalações do mesmo jogo usavam `kernel:{matchId}`; o kernel ignorava uma segunda atualização por 60 segundos. | A chave agora inclui SHA-256 do evento serializado e dos inputs do cálculo. Mesmo evento/inputs reutiliza chave; segundo lado ou correção com novo evento recebe outra. | Regressão falhou antes; testes incluem escalação parcial/completa, repetição, reinício e correção A→B→A. |
| O consumidor ignorava a notificação recebida e podia usar a chave de outra execução ou partida. | Exige correspondência de `match_id`, `job_id` e `run_id` entre canal, notificação e chave lida; rejeita notificação malformada. | Quatro regressões falharam antes. Casos positivos e chave expirada continuam cobertos. |
| O kernel aceitava campos obrigatórios ausentes, convertia identificadores `null` e reservava a chave antes de validar números. | Valida objeto, campos, tipos e valores finitos antes da reserva, sem defaults indevidos. Rejeita taxas não representáveis e preserva a possibilidade de retry válido após entrada inválida. | Sete falhas demonstradas na seleção inicial; 104 casos de protocolo passaram depois. |
| `FairOddsPayload.FromDict` lançava erro ao receber `null`, saída documentada do kernel para seleção indisponível. | Preserva `null` apenas naquela seleção e mantém as outras odds. Tipos malformados continuam rejeitados. | Seis falhas antes; 17 testes de protocolo .NET passaram depois. |
| Compose enviava `EXCHANGE_*`, mas o Worker lê configuração `Exchange:*` com prefixo `LINEUP_`. | Mapeia as mesmas variáveis de entrada para `LINEUP_Exchange__WebSocketUrl` e `LINEUP_Exchange__ApiKey` no container. | Configuração resolvida pelo Compose e leitura do provider .NET conferidas; nenhum endpoint externo acionado. |

O teste Redis do Worker também perdeu uma asserção que passava sempre que o estado existia. Ele agora exige as duas mensagens de invocação, seus inputs e chaves distintas. Esse teste foi compilado, mas sua execução com Redis continua pendente.

As fórmulas de previsão, edge, Kelly, TTLs e parâmetros científicos não foram alterados. O novo argumento `sourceEventId` é obrigatório na chamada interna `InvokeKernelAsync`; todos os chamadores do repositório foram atualizados.

## Validação executada nesta etapa

| Verificação | Resultado |
| --- | --- |
| Python: protocolo, runtime e contrato/grade de referência | **119 passaram** |
| .NET: todos os testes fora de `WorkerRuntimeTests` | **46 passaram** |
| Restore .NET com lock e build Release com avisos tratados como erros | Passaram; build com 0 avisos e 0 erros |
| Ruff e formato dos dois arquivos Python alterados | Passaram |
| Pyright do kernel com interpretador operacional explícito | 0 erros e 0 avisos de tipagem; aviso de configuração sobre `.venv` ausente no worktree, que não recebeu ambiente próprio |
| `docker compose config --format json` | Passou; nomes e defaults do Worker conferidos |
| `git diff --check` | Passou; apenas avisos de normalização CRLF/LF |
| Arquivos científicos protegidos | **14/14 hashes preservados**, antes e depois |
| Backup anterior | **477/477 arquivos** e manifesto conferidos por SHA-256, sem interpretar seus conteúdos |

Não somar esses números aos 1.082 testes Python da revisão anterior como se uma suíte geral nova tivesse sido executada. Não refiz a pesquisa econômica nem medi cobertura nesta etapa. Os testes atuais são proporcionais ao código alterado; o teste da grade conserva a saída de referência.

Usei worktree descartável, somente código versionado, sem copiar banco operacional, `.env`, credenciais ou coortes. O runner utiliza uma lista explícita de variáveis de ambiente; um audit hook bloqueia rede Python externa e acesso ao repositório vivo fora de `.venv`. Os doubles .NET não abrem conexão. O restore utiliza dependências fixadas; não houve upgrade de Python 3.14.6, predictor-core 3.1.0 ou predictor-ops 4.0.0.

## Integração ainda pendente

O Docker Desktop foi iniciado, mas os engines `default` e `desktop-linux` continuaram sem responder. O Windows negou abrir `com.docker.service` para iniciá-lo. Não houve elevação de privilégio nem criação de Redis. Permanecem não executados **1 teste Python Redis, 13 testes .NET WorkerRuntime e o Compose E2E**.

Neste host, `docker info` retornou código zero mesmo com erro de conexão e versão vazia. O novo `VALIDAR_REDIS_ISOLADO.ps1` exige uma versão válida antes de criar o Redis descartável. Sintaxe aprovada e recusa com Docker ausente executada (saída 1 esperada); o caminho com Docker disponível ainda precisa ser exercitado. O script usa portas locais exclusivas, sem volumes, e encerra somente o container que criou.

A validação de configuração Compose não prova conexão WebSocket, processamento entre containers, recuperação de Redis, encerramento limpo ou latência. Quando Docker estiver disponível, executar primeiro as integrações isoladas e depois o E2E com projeto/volumes descartáveis e insumos sintéticos.

## Limites e conclusão econômica

A deduplicação cobre o mesmo evento **serializado**, com os mesmos inputs, durante 60 segundos. Mudanças em `CapturedAt` ou ordem dos arrays produzem nova identidade. A correlação verifica os identificadores contra a chave lida naquele instante; não certifica ordem temporal global, igualdade integral do payload ou deduplicação de `bet_signals`. Estes não foram convertidos em ordens reais.

Nenhuma regra, agenda, trial, atestado ou coorte H14/H15/H9/A1 foi alterada. Não houve leitura de resultados protegidos, aquisição de dados, reabertura de estudos encerrados, ajuste com resultados de 2026, aposta ou uso de capital.

**Lucro realizável continua não demonstrado.** O resultado preservado do replay principal é −1,23 unidade em 9 apostas simuladas nos 58 jogos avaliáveis do segundo turno, de um universo de 190. Não foi recalculado nem extrapolado. Melhorar a entrega e validação das mensagens não demonstra vantagem preditiva ou econômica.

## Arquivos e reprodução

Código aplicado em `C:/Users/Superleo13/projetos/brasileirao-predictor`. Contexto, recibos, fontes congeladas e reprodução estão em `docs/continuation/runtime_contracts_2026-09-07/`. O arquivo `estado.json` enumera os dez arquivos de código/configuração alterados e seus hashes.

O backup independente desta etapa fica em `C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07/runtime_contracts_2026-09-07/`. O manifesto anterior de 477 arquivos não foi modificado; a etapa nova tem manifesto próprio.

Para reproduzir após excluir a conversa, siga `REPRODUZIR.md` no diretório desta etapa. Ele cria um worktree na base exata e sobrepõe as fontes congeladas, inclusive as mudanças ainda sem commit. Os recibos registram os comandos efetivamente executados.
