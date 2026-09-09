# Mapa de dados — C:/BRASILEIRAO

Atualizado em 09/09/2026. [Estado atual](ESTADO_ATUAL.md) e
[migração](MIGRACAO_WINDOWS.md) distinguem preservação, ambiente e operação.
O detalhamento anterior do schema e das coletas está
[arquivado](history/antes_consolidacao_2026-09-09/docs/DATA_MAP.md); seus números
de linhas e estados datados não foram recalculados nesta etapa.

## Armazenamento atual

| Área | Conteúdo e regra |
| --- | --- |
| `C:/BRASILEIRAO/brasileirao-predictor` | Checkout e histórico Git atual; código, contratos, testes e documentação |
| `C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS` | ZIP e bundle originais, checksums, manifesto e recibos da origem; preservar |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS` | Extração integral verificada, sem execução ou ajuste dos arquivos |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/projetos/brasileirao-predictor` | Dados, relatórios e configurações recebidos do projeto na origem |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/projetos/brasileirao-predictor-sessoes` | Insumos, saídas e evidências das sessões antigas |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/externos` | Dados externos e backups incluídos; não são novas fontes de pesquisa autorizadas |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/tarefa` | Evidências selecionadas da tarefa anterior |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/dados_recuperados_de_zips_mistos` | Dados únicos separados de ZIPs mistos na origem |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/migracao` | Configurações privadas e 27 definições de tarefas; não importadas |
| `C:/BRASILEIRAO/DADOS_PRESERVADOS/snapshots_sqlite` | Cinco snapshots consistentes, sem consultas de conteúdo nesta etapa |
| `C:/BRASILEIRAO/work` | Ambientes, scripts e insumos de pesquisa/organização desta máquina |
| `C:/BRASILEIRAO/ENTREGAS` | Entregas completas copiadas com igualdade de hash |
| `C:/BRASILEIRAO/INSTRUCOES` | Mandato original recebido, com hash preservado |
| `C:/BRASILEIRAO/AUDITORIA` | Completude, integridade, mapa dos Markdown e verificação de backup |

O banco operacional não foi instalado em `brasileirao-predictor/data/matches.db`.
A presença de arquivos versionados em `data/` não significa existência de
serving ou de banco populado no checkout. Credenciais e dados privados não
devem ser copiados para o Git, para a área executável de pesquisa ou para logs.

## Como resolver caminhos antigos

| Prefixo histórico | Local preservado nesta máquina |
| --- | --- |
| `C:/Users/Superleo13/projetos/brasileirao-predictor` | Código atual: `C:/BRASILEIRAO/brasileirao-predictor`; dados da captura: `C:/BRASILEIRAO/DADOS_PRESERVADOS/projetos/brasileirao-predictor` |
| `C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes` | `C:/BRASILEIRAO/DADOS_PRESERVADOS/projetos/brasileirao-predictor-sessoes` |
| `C:/Users/Superleo13/Documents/Codex/2026-09-07/le` | Consulte o sufixo de sessão sob `DADOS_PRESERVADOS/projetos/brasileirao-predictor-sessoes/2026-09-07`; entradas selecionadas também estão sob `DADOS_PRESERVADOS/tarefa` |
| `C:/predictor/data` | `C:/BRASILEIRAO/DADOS_PRESERVADOS/externos/predictor-data` |
| Entrega da conversa atual `...le/outputs/BRASILEIRAO_PF_20260909` | `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_PF_20260909` |

O manifesto é a referência para cada arquivo exato; não assumir que a troca
de prefixo basta para um insumo excluído do pacote. Código histórico excluído
do ZIP permanece no Git/bundle e nas fontes arquivadas versionadas.

## Snapshots SQLite

O campo `snapshot_restore_map` de
`C:/BRASILEIRAO/DADOS_PRESERVADOS/MANIFESTO_SHA256.json` associa os cinco snapshots
a `matches.db`, `odds_operational.db`, `research/prospective.db`,
`binance_spot_microstructure.sqlite3` e `feature_store.db`.
O recibo de extração conferiu seus hashes sem consultar tabelas.

Em eventual restauração operacional, usar o snapshot correspondente e nunca
misturá-lo com WAL/SHM brutos antigos. Dados de pesquisa protegida, ledgers,
travas/claims e calendários mantêm seus contratos; ter cópia não autoriza
consultar resultados ou avaliar coortes. Nenhum snapshot foi promovido a banco
operacional por esta consolidação.

## Verificação e limites

O recibo `AUDITORIA/verificacao_migracao_2026-09-09.json` confirma 12.423
entradas mais o manifesto, SHA-256/CRC e 9.477.623.208 bytes descompactados.
O inventário final confere também as cópias da entrega e arquivos Markdown.
Os dados refletem a captura de 08/09: alterações posteriores em outro PC
precisariam ser fornecidas para serem incluídas e verificadas.
