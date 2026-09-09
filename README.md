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

A [rodada de preços de 09/09/2026](docs/continuation/price_feasibility_2026-09-09/RESULTADO.md)
examinou 380 jogos de 2025: 374 vetores 1X2 numéricos e nenhum par de preços
admissível para replay executável, por falta de casa/clocks. A melhoria de
cotação necessária foi 7,83% na mediana sob referência proporcional do próprio
vetor e custo hipotético de 2%. Nenhuma oferta independente dessa magnitude
foi observada. Foram 380 abstenções, sem labels avaliados ou lucro demonstrado.

Passaram 80 testes da rodada e 1.870 relações em conferência Decimal separada.
Isso valida o diagnóstico delimitado, não a instalação operacional completa.
Novos ajustes de xG perderam prioridade para preços e execução verificáveis.

## O que está instalado e preservado

| Componente | Situação em 09/09/2026 |
| --- | --- |
| Código e histórico Git | `C:/BRASILEIRAO/brasileirao-predictor`, branch `main` |
| Dados migrados | Extração verificada em `C:/BRASILEIRAO/DADOS_PRESERVADOS` |
| Pacotes originais | Preservados em `C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS` |
| Entrega da pesquisa | `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_PF_20260909` |
| Ambiente de pesquisa | Python 3.13.12, isolado em `C:/BRASILEIRAO/work/price-feasibility-2026-09-09` |
| Aplicação operacional | Não instalada/ativada nesta máquina pelas sessões atuais |

O lock do projeto fixa Core 3.2.0 / Ops 4.1.0. O ambiente de pesquisa contém
somente as ferramentas necessárias à rodada. Dependências declaradas, ambiente
instalado e operação efetiva são estados diferentes.

## Usar e desenvolver

A [reprodução offline da pesquisa](docs/continuation/price_feasibility_2026-09-09/REPRODUZIR.md)
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
