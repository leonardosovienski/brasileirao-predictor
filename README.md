# brasileirao-predictor

Pesquisa quantitativa e software de previsão para o Brasileirão Série A.
**Raiz local: C:/BRASILEIRAO. Projeto globalmente não pronto; lucro executável não demonstrado; capital bloqueado.**

## Comece aqui

A [revisão RI-20260909](docs/continuation/integral_review_2026-09-09/RESULTADO.md) conferiu o existente, corrigiu defeitos e validou o escopo permitido. Seus mapas distinguem software testado, dados admissíveis e bloqueios. H14/H15/H9/A1 permanecem protegidos; conclusão da revisão não significa realização do objetivo econômico.

1. [Estado atual](docs/ESTADO_ATUAL.md) e [retomada](docs/continuation/RETOMADA.md).
2. [Matriz de alegações](docs/continuation/integral_review_2026-09-09/ALEGACOES.md) e [problemas/correções](docs/continuation/integral_review_2026-09-09/PROBLEMAS.md).
3. [Mapa do sistema](docs/continuation/integral_review_2026-09-09/MAPA_SISTEMA.md), [dados](docs/DATA_MAP.md) e [índice documental](docs/INDICE_DOCUMENTACAO.md).
4. [Próximo prompt](docs/continuation/integral_review_2026-09-09/PROXIMO_PROMPT.md), [mandato](docs/continuation/MANDATO_LUCRO_2026-09-09.md) e [histórico](HANDOFF.md).

## Resultado e evidência

A RI corrigiu admissão de identidade/estado/clocks, JSON ambíguo, concorrência de publicação, agrupamento temporal e backtest de eventos. O simulador de Copa recusa liga antes de abrir banco; importar helpers de backtest não cria log operacional. O auditor independente da captura futura recebeu a versão testada, mantendo coletor, fixture, horário e agenda.

Foram reconferidos 177 históricos íntegros, 380 jogos de 2025 e três capturas de um evento. Zero execuções admitidas. A perda condicional já conhecida de 9,24 u foi reproduzida, sem novo holdout ou otimização de filtros. Hash/recibo atual não comprova oferta executável no passado. Referência independente sem margem não é probabilidade verdadeira.

Nos lotes isolados, 1.291 casos únicos têm último resultado aprovado e um foi pulado; não se trata da suíte integral. O pacote Python foi construído e sua ajuda da CLI funcionou; .NET 10 compilou, com 69 testes aprovados e 41 pulados. Ruff no escopo CI e tipagem padrão/explicitamente ampliada passaram. [Evidências e limites](docs/continuation/integral_review_2026-09-09/REPRODUZIR.md).

## Instalação e operação são estados diferentes

| Componente | Estado conferido na RI |
| --- | --- |
| Repo e histórico | C:/BRASILEIRAO/brasileirao-predictor, main; base inicial ac22c56, integração no recibo de auditoria |
| Ambiente de pesquisa completo | C:/BRASILEIRAO/work/revisao-integral-2026-09-09/venv; Python 3.13.12, Core 3.2.0/Ops 4.1.0 e extras fixados |
| SDK .NET portátil | C:/BRASILEIRAO/work/revisao-integral-2026-09-09/dotnet-sdk; 10.0.401, build em cópia isolada |
| Ambiente mínimo da captura | C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv; preservado |
| Dados e recibos DC | C:/BRASILEIRAO/work/data-completion-2026-09-09; sem reescrever raws |
| Entrega RI | C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_RI_20260909 |
| Redis/Compose/serving operacional | Não iniciados ou integralmente validados; Docker não localizado no host |
| Agenda independente | Existente na tarefa anterior; estado atual não legível na consulta RI. Não duplicar; protocolo DC preservado |

## Desenvolvimento e continuidade

Use a [reprodução isolada RI](docs/continuation/integral_review_2026-09-09/REPRODUZIR.md). O serving legado aproxima odds/cache e não é caminho admissível para decisão financeira. O simulador implementa Copa, não temporada de liga. Mocks de WebSocket/Redis, testes e melhora preditiva não demonstram execução comercial.

A captura fixa de 11/09/2026, antes da decisão às 23:00 UTC, é descrita em [CONTINUIDADE DC](docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md), com atualização RI no estado/retomada. Não repetir lotes, mudar janela, buscar resultado do fixture ou acionar coortes para preencher a revisão.

Nenhuma aposta, login/cadastro de apostas, compra, movimentação de capital, avaliação protegida ou alteração de dependência da coleta está autorizada. Dados e configurações privados permanecem fora do Git e dos processos de pesquisa. [Migração](docs/MIGRACAO_WINDOWS.md) e [documentos históricos](docs/history/antes_consolidacao_2026-09-09/README.md) mantêm seu escopo datado. [Publicação anterior](docs/continuation/publication_2026-09-09/README.md) não é CI ou recibo das alterações RI.
