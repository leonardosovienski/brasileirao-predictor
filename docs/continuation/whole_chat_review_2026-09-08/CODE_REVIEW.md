# Revisão adversarial nova do código operacional

Data: 08/09/2026 UTC. Revisão independente do diff vigente sobre `4dfdec6`, sem editar o repositório operacional, operar serviços, abrir banco/coortes ou executar backtest. Escopo: kernel Python, Worker/MarketStateEngine/contratos .NET, Compose, parser xG e auditoria de qualidade. Modelos e comparação de preços são examinados por outro revisor.

**Manteria as correções mecânicas. Não encontrei regressão bloqueante nova nos ajustes de schema, odds nulas, nomes de configuração ou parsing/qualidade de xG. Há limites importantes no runtime concorrente: mensagens válidas e corretamente correlacionadas ainda podem carregar o cálculo antigo; falhas após a reserva podem impedir o retry por 60 segundos. Isso impede tratar o conjunto como pronto para operação irrestrita.**

Li novamente o prompt atual, os checkpoints de HANDOFF/RETOMADA, o contrato Redis v1 e os diffs/callers/testes relevantes. Os números de testes e auditorias anteriores não foram usados como garantia geral de correção. Nesta revisão executei somente dois cenários sintéticos novos, descritos abaixo.

## Achados por severidade

### P1 antes de operação: correlação não garante o cálculo mais recente

Referências no repositório operacional:

- `brasileirao_predictor/kernel_daemon.py:267`: reserva por identidade da invocação.
- `brasileirao_predictor/kernel_daemon.py:288`: todas as invocações da partida escrevem na mesma chave `fair_odds:{match}`.
- `brasileirao_predictor/kernel_daemon.py:350`: handlers concorrentes por mensagem.
- `dotnet/LineupWorker/Services/MarketStateEngine.cs:116`: compara match/job/run entre a chave e a notificação.
- `dotnet/LineupWorker/Services/MarketStateEngine.cs:140`: lê posteriormente o estado da escalação, sem vinculá-lo à versão da previsão.

Reprodução sintética usando o `_handle_invoke` vigente:

1. `old-run`, timestamp 1000, reserva sua identidade; a resposta dessa chamada assíncrona fica atrasada.
2. `new-run`, timestamp 2000 e input diferente, reserva outra identidade, calcula, grava e publica.
3. A resposta do claim antigo chega; `old-run` calcula, sobrescreve a chave e publica sua própria notificação.
4. A chave agora contém `old-run`, com odds diferentes das que `new-run` havia gravado. A notificação antiga possui exatamente os mesmos match/job/run da chave e satisfaz os predicados novos do consumidor.

O teste controla somente a ordem de conclusão dos awaits; usa Redis em memória e grade sintética normalizada. Ele demonstra que o algoritmo permite a sequência, não sua frequência ou ocorrência observada num servidor Redis real. O envelope de saída sequer transporta `timestamp_t3`; esse campo atualmente é validado na entrada, mas não usado para ordenar o estado publicado.

Existe ainda uma janela no consumidor: após ler a chave e conferir os IDs, o código faz outros awaits para obter estado/auditar antes de publicar o sinal. Uma resposta mais recente pode surgir nesse intervalo. Portanto, proteger somente o SETEX do produtor não demonstra que o sinal final sempre será o mais recente.

**Classificação precisa:** lacuna residual relevante, mais exposta ao permitir corretamente duas atualizações legítimas da mesma partida. A ausência de sequenciamento já existia. A deduplicação antiga por partida suprimia indevidamente o segundo lado; revertê-la não é solução. O relatório original `docs/continuation/runtime_contracts_2026-09-07/RESULTADO.md:49` já declara expressamente que a correlação não certifica ordem temporal global, payload integral ou deduplicação de sinais. A reprodução confirma esse limite; não desmente a alegação restrita feita naquela entrega.

Antes de promover esse caminho, definir versão de estado/current-run e aceitação atômica coerente até o consumidor, incluindo resposta atrasada, reinício, replay e atualização parcial/completa. Relógio de parede sozinho não resolve igualdade, inversão de relógio ou ordem de revisão. Não implementei remendo nesta revisão; a integração Redis/Compose continua necessária.

### P2: claim consumido não significa processamento concluído

Referência: `kernel_daemon.py:267` até `:292`.

A reserva NX de 60 segundos precede cálculo, SETEX e PUBLISH. Se houver exceção no SETEX após a reserva, um retry imediato com o mesmo evento/inputs encontra a chave ocupada e retorna sem produzir resposta. Reproduzi essa sequência com falha de transporte sintética: nenhuma odd ou notificação é gravada, e o retry nem tenta um segundo SETEX.

Esse comportamento é **preexistente**, não foi criado pela validação nova. O reparo atual garante que uma entrada inválida não queime o claim; não promete recuperação de falha posterior, confirmação de entrega ou processamento exatamente uma vez. O TTL de 60 segundos tampouco constitui deduplicação permanente. Resolver recuperação exige distinguir trabalho pendente/concluído e tratar a incerteza de publicação; apagar a chave indiscriminadamente após erro também pode permitir duplicação. Manter como requisito explícito antes de operação, sem expandir silenciosamente o patch atual.

### P2: integração de transporte permanece sem evidência suficiente

Os testes .NET de identidade e correlação utilizam doubles. Configuração Compose resolvida, build e testes unitários não exercitam conexão WebSocket, serialização entre processos/containers, Redis Pub/Sub, recuperação ou ordenação sob concorrência. O relatório original registra corretamente 1 teste Python Redis, 13 WorkerRuntime e Compose E2E não executados; não repeti nem converti essas pendências em aprovação.

A configuração nova liga as variáveis externas aos nomes efetivamente lidos por `AddEnvironmentVariables(prefix: "LINEUP_")` e `Exchange:*`. Isso é correto. O default `wss://exchange.invalid/odds/ws` permanece um placeholder; o ajuste não fornece um adaptador funcional de uma exchange. `MarketOddsCache` ainda usa o formato de exemplo e timestamp de recebimento local. São limites prévios, não regressões do mapeamento.

## Ajustes que manteria

| Alteração | Julgamento após nova inspeção |
| --- | --- |
| `_parse_invoke` e validação antes do claim | Justificada pelo schema: campos exatos e obrigatórios, IDs string não vazia, números finitos, bool rejeitado, timestamp inteiro não negativo. `1.0` é aceito como integer conforme JSON Schema. Taxas não representáveis falham antes de Redis. Remover defaults de campos obrigatórios corrige aceitação indevida. |
| Identidade por evento serializado + inputs | Corrige a supressão de atualização parcial/completa. Todos os chamadores internos vigentes fornecem o argumento novo. A identidade é estável para os mesmos bytes/inputs; CapturedAt e ordem dos arrays alteram a chave, conforme já documentado. Não equivale a um ID canônico permanente do evento do provedor. |
| Correlação canal/notificação/chave | Corrige o consumo da chave de outra execução ou partida ao receber uma notificação. A chave continua sendo a fonte das odds. O reparo é válido dentro dessa garantia restrita. |
| `ReadOptionalOdd` no .NET | Preserva seleção indisponível enviada como JSON null pelo kernel, mantendo outras odds. Campo ausente continua null; tipo incompatível continua rejeitado. Sem alterar fórmulas/limiares. |
| Mapeamento Compose | Os nomes `LINEUP_Exchange__WebSocketUrl` e `LINEUP_Exchange__ApiKey` correspondem ao provider/configuração realmente usados. Não altera credenciais de origem nem aciona endpoint nesta revisão. |
| `ingest_sofascore.parse_xg` | Passa a exigir estatística exata de jogo completo, rejeitando xGOT, pares incompletos, conflitos, bool, negativos e valores não finitos. Duplicatas idênticas são toleradas; conflito não depende de ordem. Zeros, inclusive `(0,0)`, são preservados. Aceitar string numérica é coerente com o payload do provedor; a função não atesta proveniência. |
| `data/xg_quality.py` e `missingness_audit.py` | Funções puras de classificação e SELECT na conexão explicitamente fornecida. Separação de presença, numericidade e zero não atestado corrige a antiga equivalência indevida entre NOT NULL e observação certificada. Nenhuma imputação nem reescrita de histórico. Aliases antigos mantêm semântica de presença, agora explícita em schema v2. |

Não encontrei I/O implícito novo nos classificadores, chamadas de coleta no parser ou alteração de regra operacional de aposta nesses diffs. Não encontrei consumidor de `xg_coverage` no código Python do pacote que exija o schema v1; os testes foram adaptados ao v2. Não tratei ausência de bug encontrado como prova de ausência de qualquer bug.

## Limites de xG que não se resolvem com parsing

`(0,0)` não prova dado ausente. O classificador corretamente usa `ZERO_PAIR_UNATTESTED`; mesmo um par positivo permanece sem autenticação de fonte. A auditoria de uma tabela SQLite não consegue reconstruir se um valor original era bool ou string depois que a afinidade da coluna o converteu em número. Gols presentes delimitam a consulta de partidas jogadas, mas não atestam quando cada estatística ficou disponível. A auditoria não cria available_at nem completion timestamp.

A quarentena exploratória posterior é uma política de admissibilidade de outro estudo, não uma correção factual de todos os zeros do provedor. Os arquivos históricos anteriores devem permanecer preservados, e não devem receber null ou timestamps inventados. Não abri dados ou resultados adicionais nesta revisão.

## O que faria novamente e o que refaria

Faria novamente os reparos de contrato, odds nulas, configuração, parser e descrição honesta de cobertura, com regressões mínimas e execução isolada. A decisão de manter fórmulas, parâmetros, dependências, coortes e agendas fora desses reparos foi apropriada. Não há motivo técnico encontrado para desfazer essas correções.

Refaria mais cedo o teste de concorrência com duas invocações válidas e o teste de falha após claim, antes de encerrar a etapa do runtime. A documentação já reconhecia o limite, mas uma reprodução torna a pendência concreta e melhor priorizada. Separaria ainda mais claramente “aceitar corretamente cada mensagem” de “emitir sinal da versão atual da partida”, inclusive nos critérios de aceite.

No fluxo de dados, faria a inspeção de presença, massa de zeros e proveniência antes da primeira avaliação histórica do candidato. Não classificaria zeros como ausentes sem evidência; manteria o tratamento posterior identificado como exploratório. Essa mudança de ordem melhora o processo de investigação, não transforma resultados já vistos em validação independente.

Não usaria esta revisão para retunar parâmetros, reabrir estudos encerrados, colocar código em produção, criar ordens ou ampliar escopo de ingestão. O Worker ainda envia Elo 1500/1500 e o kernel lê theta VORP default zero, fatos anteriores ao diff: consertar o transporte por si só não prova utilidade preditiva do caminho. Alterá-los seria outra decisão, não um ajuste mecânico implícito.

## Evidência nova e reprodução

Arquivo: `work/whole_chat_review/test_runtime_characterization.py`.

Execução: Python operacional com `work/validation_runner.py whole_chat_runtime_characterization`, pytest dirigido a esse arquivo, `-q -p no:cacheprovider`. **2 testes passaram em 0,70 s.** São testes de caracterização: as asserções aprovadas demonstram os dois comportamentos problemáticos existentes. Não significam runtime corrigido.

Recibos: `work/validation/whole_chat_runtime_characterization.json` e `.log`. Cwd descartável `work/integration-repo`, ambiente por allowlist, bloqueio Python de rede externa e repositório vivo fora de `.venv`. Sem sockets ou banco. A grade matemática foi substituída apenas no processo de teste por uma grade sintética; não houve treino ou alteração de modelo.

Antes da execução, SHA-256 do kernel operacional e de sua cópia isolada eram iguais: `785bd1b55cd7557758762850551ed589083288f4131ec6cc89b6fd2762296f5a`.

Nenhum fonte operacional foi editado por este revisor. Não executei novamente a suíte geral, Redis, Docker, ingestão, backtests ou pagamentos. A conclusão é manter os reparos mecânicos e preservar os limites de operação e de evidência econômica.
