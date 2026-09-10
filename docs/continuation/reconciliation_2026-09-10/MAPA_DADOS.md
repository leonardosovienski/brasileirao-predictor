# Dados, datas e fontes RCA

Não é correto afirmar que os dados, datas e fontes estejam todos atualizados, completos e validados. A checagem atual confirmou hashes/metadados específicos; os resultados e conteúdos econômicos permanecem congelados.

| Requisito / fonte | Local / universo | Estado atual para a finalidade |
| --- | --- | --- |
| Histórico Football-Data | work/data-completion-2026-09-09/public_sources/football_data_bra_origin_csv.csv | Hash atual igual ao congelado. BE usou 4.940 partidas de 2012–2024; o CSV inclui outros anos. Max é anônimo; não certifica preço executável. |
| Timelines OddsPapi | work/data-completion-2026-09-09/raw; 177 Jan–Jun/2026 | Integridade conferida em RI; não repetida nesta etapa. Todos recebidos depois dos cortes históricos. Não admissíveis como recibo da época. |
| Piloto prospectivo DC | prospective_pilot; três capturas de um fixture | Uma unidade de evento. Flag de coleta do agregador não é suspensão comercial da casa; sem aceite/limite pessoal. |
| Captura futura DC | helpers no mesmo work; decision 11/09/2026 23:00 UTC | Hashes atuais intactos. Às 19:17 UTC de 10/09, tentativa e recibo ausentes; janela futura. Não antecipada. Automação não verificável pelo texto retornado. |
| Publicação e recebimento | API-Football/Sportmonks/OddsPapi | Contratos sintéticos e algumas fontes oficiais conferidos; publicação desconhecida fica null. Não generalizar correção UTC para calendário completo ou API homologada. |
| Fonte/estado/linha/revisões | The Odds API decoder e curated/1 | Decoder preserva vazio/inválido; schema curated incompleto para closing/v2. RCA-P06. |
| Escalações e features históricas | lineup_archive, residual_features, legado xG/Elo | Arquivo de linhas não registra retirada/vazio; causalidade por feature/artefato ainda parcial. RCA-P07/CPL-P22. |
| Preços nominais simultâneos/aceite/custos | Fontes legítimas tentadas nas rodadas DC/RI/BE/CPL | Não recuperados em forma suficiente. Barreiras OddsPortal/OddsAgora, Betfair e API-Football documental registradas; nenhuma tentativa idêntica repetida sem condição nova. |
| Acervo migrado | C:/BRASILEIRAO/DADOS_PRESERVADOS e manifesto | Recebido e preservado; 12.423 entradas/9.477.623.208 bytes são contagens do recibo de extração, não nova leitura nesta etapa. Cinco snapshots não foram restaurados operacionalmente. |
| Coortes protegidas | Contratos H14/H15/H9/A1 | Não verificáveis empiricamente dentro das permissões atuais. Não usar como preenchimento de lacunas ou holdout. |

Datas de testes são sintéticas. Hashes provam igualdade dos bytes, não autenticidade, atualização, oferta ou aceitação. Não foram consultados resultados de 2026, calendário completo atual, APIs limitadas ou custos pessoais nesta etapa. Não afirmar ausência de dependências externas ou que todos os dados de outra máquina foram recebidos.

Fontes e tentativas oficiais datadas: [CPL](../completion_2026-09-10/MAPA_DADOS.md), [CLO](../closeout_2026-09-10/MAPA_DADOS.md), [DC](../data_completion_2026-09-09/RESULTADO.md), [BE](../economic_search_2026-09-10/RESULTADO.md). Recibos atuais: [metadados](evidence/data-metadata.json), [dependências](evidence/dependencies.json) e [extras](evidence/dependency-extras.json).
