# Dados, fontes e recuperação

A documentação foi atualizada para a situação comprovada; não há comprovação de que todos os dados estejam completos ou atualizados até a data corrente. Esta publicação não realiza nova pesquisa econômica, não consulta desfechos protegidos e não rebaixa recebimento tardio a informação conhecida no passado.

| Conjunto / fonte | Verificação e uso permitido | Recuperação |
| --- | --- | --- |
| Football-Data, CSV original | Hash e tamanho reconferidos em `evidence/source-metadata.json`; bytes iguais ao acervo congelado. A amostra BE é 2012–2024; máximas anônimas não comprovam oferta nominal. | `C:/BRASILEIRAO/work/data-completion-2026-09-09/public_sources/football_data_bra_origin_csv.csv`; backup DC. |
| OddsPapi, timelines históricas | 177 arquivos de Jan–Jun/2026 foram recebidos após os cortes. Mantidos, sem ler seus desfechos. A verificação semântica anterior e limitações permanecem datadas. | Work DC/raw e `BACKUPS/DC-20260909-dados-e-recibos.zip`. |
| Piloto e captura futura DC | Hashes dos dois helpers reconferidos; presença de tentativa/recibo/captura verificada sem abrir resultados. Corte congelado: 11/09/2026 23:00 UTC. | Helpers DC nos caminhos originais e cópias em archive/local-helpers; próximos passos abaixo. |
| Fontes Sportmonks/API-Football/The Odds API | Contratos e limites documentais mantidos em CPL/CLO/DC; publicação desconhecida continua null. Não significa conta autenticada nem calendário completo atualizado. | Mapas e recibos de fontes nas etapas anteriores, acessíveis pelo índice documental. |
| Ofertas simultâneas, aceitação, capacidade e custos pessoais | Não recebidos em forma suficiente para demonstrar lucro executável. Falhas de acesso preservadas não provam inexistência de oportunidade. | CPL-P26/RCA-P10 no registro corrente. Não preencher lacunas com estimativas apresentadas como fatos. |
| Acervo recebido da máquina anterior | Manifesto de extração: 12.423 entradas e 9.477.623.208 bytes. Esses números são do recibo histórico, não uma nova inspeção de conteúdo protegido. | `C:/BRASILEIRAO/DADOS_PRESERVADOS` e `MIGRACAO_DADOS`. Cinco snapshots não equivalem a restauração operacional. |
| H14/H15/H9/A1 | Apenas contratos/metadados permitidos. Não ler resultados, liquidar, renovar claims/atestados, reiniciar ou alterar agendas. | Preservar acervo e serviços; RCA-P11/CPL-P22. |

O repositório é público. `.gitignore` já excluía bancos, segredos e relatórios com linhas derivadas de fornecedores cuja redistribuição não foi estabelecida. Essa fronteira foi mantida. GitHub armazena código, documentação, registries já versionados, evidências autorizadas, instruções e roteiros; o inventário não transfere licenças nem transforma dados locais em públicos.

O clone novo é uma prova de recuperação do conteúdo versionado. Para continuidade com dados locais, preserve **toda a pasta C:/BRASILEIRAO**, especialmente DADOS_PRESERVADOS, work/data-completion, work/economic-search, BACKUPS, ENTREGAS e AUDITORIA. Apagar esta conversa não apaga esses arquivos. Apagar a pasta, a conta do GitHub ou a tarefa que possui a automação é outra operação e não está coberto pela recuperação do chat.

Fontes canônicas, URLs, datas, schemas, tentativas e limitações: [mapa RCA](../reconciliation_2026-09-10/MAPA_DADOS.md), [mapa CPL](../completion_2026-09-10/MAPA_DADOS.md), [contratos RES](../resolution_2026-09-10/CONTRATOS.md), [resultado BE](../economic_search_2026-09-10/RESULTADO.md). Hash comprova igualdade de bytes, não autenticidade comercial, atualidade ou aceitação.
