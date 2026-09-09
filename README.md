# brasileirao-predictor

Pesquisa quantitativa e software de previsão para o Brasileirão Série A.
**Raiz local: `C:/BRASILEIRAO`. Rentabilidade executável não demonstrada;
capital bloqueado.**

## Comece aqui

1. [Estado atual verificado](docs/ESTADO_ATUAL.md): código, ambiente, dados e operação.
2. [Retomada](docs/continuation/RETOMADA.md): sequência para a próxima sessão.
3. [Mandato vigente](docs/continuation/MANDATO_LUCRO_2026-09-09.md): objetivo e restrições.
4. [Mapa de dados](docs/DATA_MAP.md) e [índice de todos os Markdown](docs/INDICE_DOCUMENTACAO.md).
5. [Histórico de checkpoints](HANDOFF.md): resultados e protocolos de cada época.

## Resultado mais recente

A [rodada DC-20260909](docs/continuation/data_completion_2026-09-09/RESULTADO.md)
recuperou e verificou timelines de 177/177 partidas de Jan–Jun/2026, o CSV
oficial de 380 jogos de 2025 e três capturas atuais de um evento. Os históricos
não demonstram recebimento e disponibilidade na época; no piloto, a Bet365
Brasil estava inativa no estado do bookmaker. Nenhum par foi admitido para execução.

O replay closing estritamente condicional perdeu 9,24u sobre banca de 100u e
custo hipotético de 2%. A própria fonte avisa desatualização da referência
Pinnacle no período de todas as 32 seleções. Esse saldo preservado não é
validação econômica. Custos reais, capacidade e validação futura continuam pendentes.

Passaram 138 testes delimitados, Ruff, tipagem dos três novos módulos e uma
conferência aritmética separada. O acompanhamento diário às 19:57 de São Paulo
prepara uma [captura antes de T−60 em 11/09](docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md).
Isso não ativa a aplicação operacional nem as coortes protegidas. A
[rodada PF anterior](docs/continuation/price_feasibility_2026-09-09/RESULTADO.md)
permanece preservada. Novos ajustes de xG continuam sem prioridade.

## O que está instalado e preservado

| Componente | Situação em 09/09/2026 |
| --- | --- |
| Código e histórico Git | `C:/BRASILEIRAO/brasileirao-predictor`, branch `main` |
| Dados migrados | Extração verificada em `C:/BRASILEIRAO/DADOS_PRESERVADOS` |
| Pacotes originais | Preservados em `C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS` |
| Entregas da pesquisa | `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_DC_20260909` e rodada PF anterior |
| Novos dados e recibos | `C:/BRASILEIRAO/work/data-completion-2026-09-09` |
| Ambiente de pesquisa | Python 3.13.12, isolado em `C:/BRASILEIRAO/work/price-feasibility-2026-09-09` |
| Aplicação operacional | Não instalada/ativada nesta máquina pelas sessões atuais |

O lock do projeto fixa Core 3.2.0 / Ops 4.1.0. O ambiente de pesquisa contém
somente as ferramentas necessárias à rodada. Dependências declaradas, ambiente
instalado e operação efetiva são estados diferentes.

## Usar e desenvolver

A [reprodução offline da pesquisa atual](docs/continuation/data_completion_2026-09-09/REPRODUZIR.md)
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
