# Auditoria de produtores de escalação — somente leitura

Data: 2026-09-08. Repositório inspecionado: `C:/Users/Superleo13/projetos/brasileirao-predictor`.

## Conclusão

Não foi encontrado produtor interno real que ainda publique escalações em `lineups:*` e precise de migração para a inbox. No código atual, o canal antigo é uma entrada de compatibilidade deliberada do Worker; suas publicações encontradas são fixtures de testes. O único chamador de `enqueue_lineup` fora dos testes é o smoke sintético, que já utiliza a stream.

A frase “produtores devem migrar” no relatório anterior descreve uma condição para integrar produtores externos ou futuros. Não identifica um capturador interno já ligado ao Pub/Sub que tenha ficado sem correção. Esta auditoria não demonstra que exista ou esteja ativo qualquer produtor fora do repositório.

## Evidência por caminho

Os caminhos abaixo são relativos ao repositório inspecionado; linhas conferidas no código vigente.

| Caminho | Evidência e classificação |
| --- | --- |
| `dotnet/LineupWorker/Worker.cs:33` | Define `LINEUP_CHANNEL_PATTERN = "lineups:*"`; o fluxo faz `SubscribeAsync` para receber eventos. É consumidor legado, não produtor. |
| `dotnet/LineupWorker.Tests/WorkerRuntimeTests.cs:366` | Publica mensagens vazias, inválidas e eventos sintéticos em `lineups:home_away` nas linhas 366–370; a linha 440 também exercita a entrada legada. São testes intencionais de compatibilidade. |
| `brasileirao_scripts/lineup_inbox.py:5` | Define `lineup:v2:inbox`; o Lua na linha 13 usa XADD e o helper `enqueue_lineup` começa na linha 17. É o produtor genérico de armazenamento durável, sem coleta implícita. |
| `brasileirao_scripts/hotpath_smoke.py:36` | `register_synthetic_lineup` fabrica identidades/equipes/jogadores para ambiente descartável e chama `enqueue_lineup` na linha 54. Esse chamador já foi migrado. A publicação na linha 86 apenas acorda uma solicitação kernel já registrada no canal v2; não publica escalações legadas. |
| `brasileirao_scripts/capture_sofascore_event.py:63` | Obtém escalação do provedor para um envelope de captura. As linhas 91–94 preservam confirmação/designação/jogadores; as linhas 121 e 163 escrevem arquivos/ledger. Não há chamada Redis ou publicação de `LineupEvent`. Não é produtor legado a migrar. |
| `brasileirao_predictor/ingest_sofascore.py:436` | `parse_ratings` processa dados de jogadores; a chamada a `event_lineups` na linha 519 alimenta essa ingestão de ratings. Não envia eventos para o Worker por Redis. |
| `dotnet/LineupWorker/Services/LineupStreamConsumer.cs:12` | Define a entrada canônica `lineup:v2:inbox`; seu consumo e recuperação pertencem ao Worker. |

Um adaptador de capturas para a inbox seria uma integração nova: exigiria definir identificação de partida/jogadores e política de emissão da escalação confirmada. Não foi inventado nem implementado nesta auditoria.

## Escopo e método

Foram lidos o checkpoint mais recente de `HANDOFF.md`, a abertura de `docs/continuation/RETOMADA.md`, o prompt atual, o contrato Redis v2 e `outputs/PENDENCIAS_CORRIGIDAS/RESULTADO.md` da pasta desta tarefa. Checkpoints históricos não foram tratados como fila atual.

As buscas usaram `rg` em código Python, C#, Go, JavaScript/TypeScript, shell/PowerShell e configuração YAML. Foram procurados `lineups:`, `lineup:v2:inbox`, `enqueue_lineup`, construção de `LineupEvent`, publicação Redis e XADD. Houve pesquisa dirigida em `brasileirao_predictor`, `brasileirao_scripts`, `dotnet`, `scripts` e `.github`, seguida de busca nos arquivos de código do repositório, excluindo `docs`, `data`, backups e testes quando necessário para separar produção de fixtures. O contexto das ocorrências foi lido antes da classificação.

Não houve enumeração de dados operacionais, leitura de bancos/coortes/ledgers, alteração de código, edição de arquivo protegido, reescrita de arquivos históricos, execução de suíte, nova pesquisa econômica ou comunicação com provedores. As únicas escritas desta subtarefa são esta nota na área de trabalho.

## Pendências de integração delimitadas

Não foi identificada outra migração interna de produtor concretamente pendente. Build/inicialização do Compose e CI remoto continuam sendo as verificações de ambiente citadas no checkpoint; o root está tratando o host separadamente.

O endpoint padrão do Compose é deliberadamente inerte (`exchange.invalid`), e `MarketOddsCache` documenta um formato genérico a adaptar por provedor. Isso é uma fronteira de integração externa já explicitada no relatório, não evidência de um feed operacional que esta auditoria possa completar sem um contrato de provedor. Não foi criada integração externa nem executor de apostas.
