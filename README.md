# brasileirao-predictor

Pesquisa quantitativa e software de previsão para o Brasileirão Série A.
**Raiz local: `C:/BRASILEIRAO`. Rentabilidade executável não demonstrada;
capital bloqueado.**

## Comece aqui

Próxima sessão: [revisão integral do projeto e resolução das lacunas](docs/continuation/REVISAO_INTEGRAL_2026-09-09.md).
Conferir primeiro o existente, suas alegações e premissas; depois corrigir e completar.
O roteiro está preparado; a revisão integral ainda não foi executada.

1. [Estado atual verificado](docs/ESTADO_ATUAL.md): código, ambiente, dados e operação.
2. [Retomada](docs/continuation/RETOMADA.md): sequência para a próxima sessão.
3. [Mandato vigente](docs/continuation/MANDATO_LUCRO_2026-09-09.md): objetivo e restrições.
4. [Mapa de dados](docs/DATA_MAP.md) e [índice de todos os Markdown](docs/INDICE_DOCUMENTACAO.md).
5. [Histórico de checkpoints](HANDOFF.md): resultados e protocolos de cada época.

## Resultado mais recente

A [continuação ER-20260909](docs/continuation/execution_readiness_2026-09-09/RESULTADO.md)
corrigiu cinco falhas da rotina futura e confirmou contratos públicos de
limite, moeda, coleta e tributação. Passaram **153 testes**, Ruff e tipagem
explícita dos dois executores alterados. As versões testadas foram colocadas
nos caminhos da captura já agendada para 11/09 antes das 20:00 de São Paulo.

`bookmakerIsActive=false` indica principalmente falta de coleta ativa pelo
agregador para a casa/jogo. Rejeitar esse feed continua correto, mas o campo
não prova suspensão da oferta pela própria Bet365. Capacidade pessoal, custo
total e validação futura permanecem pendentes; lucro executável não demonstrado.

A [rodada DC anterior](docs/continuation/data_completion_2026-09-09/RESULTADO.md)
preserva 177 históricos, CSV de 380 jogos de 2025 e três capturas de um evento.
O closing condicional perdeu 9,24u com referência comprometida; não é ROI
executável. [Continuidade](docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md)
diária às 19:57, sem ativar coortes ou aplicação operacional completa.

## O que está instalado e preservado

| Componente | Situação em 09/09/2026 |
| --- | --- |
| Código e histórico Git | `C:/BRASILEIRAO/brasileirao-predictor`, branch `main` |
| Dados migrados | Extração verificada em `C:/BRASILEIRAO/DADOS_PRESERVADOS` |
| Pacotes originais | Preservados em `C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS` |
| Entregas da pesquisa | `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_ER_20260909`, DC e PF anteriores |
| Correções e contratos ER | `C:/BRASILEIRAO/work/execution-readiness-2026-09-09` |
| Novos dados e recibos | `C:/BRASILEIRAO/work/data-completion-2026-09-09` |
| Ambiente de pesquisa | Python 3.13.12, isolado em `C:/BRASILEIRAO/work/price-feasibility-2026-09-09` |
| Aplicação operacional | Não instalada/ativada nesta máquina pelas sessões atuais |

O lock do projeto fixa Core 3.2.0 / Ops 4.1.0. O ambiente de pesquisa contém
somente as ferramentas necessárias à rodada. Dependências declaradas, ambiente
instalado e operação efetiva são estados diferentes.

## Usar e desenvolver

A [reprodução offline da pesquisa atual](docs/continuation/execution_readiness_2026-09-09/REPRODUZIR.md)
usa entradas explícitas e diretórios novos. Para uma futura instalação completa,
consulte [migração e instalação](docs/MIGRACAO_WINDOWS.md) e os contratos do
runtime em [MODERNIZATION.md](docs/MODERNIZATION.md). Essa instalação exige
validação própria; não execute comandos de coleta/governança como inicialização.

O código possui modelos Elo/xG/gols, pesquisa PIT, scanner de preços e runtime
Python/Redis/.NET. Esses componentes são meios de investigação, não evidência
de lucro. Sofascore alimenta o histórico; outras integrações têm contratos,
quotas e reservas específicos. Fontes e relógios precisam ser demonstrados.

H14/H15/H9/A1, claims, agendas e dependências de coleta continuam protegidos.
Nenhum resultado intermediário, avaliador oficial, renovação de atestado ou
ação financeira está autorizado pela organização dos arquivos. CLV e métricas
probabilísticas isolados não autorizam capital.

Os [textos anteriores a esta consolidação](docs/history/antes_consolidacao_2026-09-09/README.md)
foram preservados, assim como todos os estudos e contratos congelados. Use o
estado atual para caminhos e situação do host; use documentos históricos para
reproduzir a época em que foram escritos.
