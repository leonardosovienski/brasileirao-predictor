# Mapa de dados — C:/BRASILEIRAO

Atualizado em 09/09/2026. [Estado atual](ESTADO_ATUAL.md) e
[migração](MIGRACAO_WINDOWS.md) distinguem preservação, ambiente e operação.
O detalhamento anterior do schema e das coletas está
[arquivado](history/antes_consolidacao_2026-09-09/docs/DATA_MAP.md); seus números
de linhas e estados datados não foram recalculados nesta etapa.


## Revisão RI-20260909: situação mais recente

A [revisão de campos/fontes](continuation/integral_review_2026-09-09/MAPA_DADOS.md) reconferiu os 177 históricos, CSV 2025 e piloto, sem reabrir bancos protegidos. Estado: arquivos íntegros, execução histórica inadmissível/insuficiente; lucro executável não mensurável. [Resultado](continuation/integral_review_2026-09-09/RESULTADO.md).

- `C:/BRASILEIRAO/work/revisao-integral-2026-09-09`: venv completo, SDK10 portátil, inventário, contratos públicos, ensaios, logs, conta independente e backups dos guias/helpers anteriores.
- `C:/BRASILEIRAO/brasileirao-predictor/docs/continuation/integral_review_2026-09-09`: registros centrais, mapas, protocolo, relatório, próximo prompt e evidências sanitizadas.
- `C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_RI_20260909`: cópia conferida da entrega RI.
- `C:/BRASILEIRAO/AUDITORIA/REVISAO_INTEGRAL_2026-09-09.json`: integração, hashes, diff, cópias e recuperação Git. Não é recuperação operacional dos dados protegidos.

Nenhum rawDC foi reescrito; apenas o auditor futuro independente foi atualizado com backup/hash. O estado atual da agenda não pôde ser lido pela ferramenta; TOML antigo é documental. O restante deste mapa descreve locais e recibos anteriores, com seu escopo/datamento preservado.

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

## Continuação ER-20260909

`C:/BRASILEIRAO/work/execution-readiness-2026-09-09` contém cinco novas fontes
públicas, contrato de condições, ensaios isolados, hashes de ativação e versões
anteriores das duas rotinas futuras. Os 177 históricos e payloads DC não foram
reescritos. Ensaios sintéticos não são novas observações de mercado.
[Resultado ER](continuation/execution_readiness_2026-09-09/RESULTADO.md) e
[reprodução](continuation/execution_readiness_2026-09-09/REPRODUZIR.md).

## Aquisição DC-20260909

Área canônica `C:/BRASILEIRAO/work/data-completion-2026-09-09`:

| Subárea | Conteúdo e limite |
| --- | --- |
| `raw` | 177 timelines OddsPapi Jan–Jun/2026, 623.271.596 bytes; exploração sem recibo PIT da época |
| `universe.json`, `acquisition.json`, `transport_repair.json` | Universo congelado, tentativas, reaproveitamento verificado, hashes e um reparo de conexão |
| `public_sources`, `extra_docs/public_sources` | CSV Football-Data, páginas oficiais e recibos HTTP; não versionar os corpos das páginas |
| `prospective_pilot` | Catálogos, fixture escolhido antes das odds, três capturas reais e recibos sanitizados |
| `closing-01` | Escolhas congeladas antes dos labels 2025 e liquidação exclusivamente condicional |
| `admission-01` | Auditoria de identidade/estado/clocks, qualidade closing e manifestos |
| `tests-05` | JUnit e log da execução de 138 testes isolados |
| `followup`, `followup_audit` | Saídas futuras, criadas somente quando houver tentativa/captura na janela |

Os 22 históricos reutilizados vieram de entradas antigas explicitamente
permitidas de Jan–Jun/2026; os demais 155 foram adquiridos. O universo de 177
fixtures tem SHA-256 `6264b2a1b795928fdf0dc6476e311535a42fbc96c12caf5cf881777b7779caba`.
O CSV bruto tem SHA-256 `ba3e9ea79ab4091b117a901f3914940cea07f1fe06de0deb57af5076f664ccb6`.
Somente linhas de 2025 foram usadas no replay de preços e labels; nenhum
resultado de 2026 ou de coorte protegida foi avaliado.

A configuração privada preservada foi consultada apenas pelos processos de
aquisição da API existente. Não há cópia de credenciais no checkout, nos
scripts, nos recibos públicos ou no processo de pesquisa offline. O fato de
um arquivo ter hash válido não comprova disponibilidade passada, autenticidade
da oferta, capacidade ou aceite.

Código, protocolos, resumos e recibos sanitizados ficam em
`docs/continuation/data_completion_2026-09-09`; entrega em
`C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_DC_20260909`. A automação do aplicativo
tem cópia de sua definição em `C:/BRASILEIRAO/AUDITORIA`.
[Resultado e lacunas](continuation/data_completion_2026-09-09/RESULTADO.md),
[reprodução](continuation/data_completion_2026-09-09/REPRODUZIR.md).

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
