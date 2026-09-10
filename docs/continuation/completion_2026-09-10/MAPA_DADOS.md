# Fontes, campos e lacunas CPL

| Conjunto/fonte | Local/versão/semântica | Situação para a finalidade |
| --- | --- | --- |
| CSV Football-Data 2012–2024/BE | public_sources/football_data_bra_origin_csv.csv em work/data-completion-2026-09-09; Season/Date/Home/Away/FTHG/FTAG/PSC/MaxC; placar é label, preço decimal, máximo anônimo |4.940 jogos e4.939 trios calculáveis conferidos em BE; nenhum novo download/label. Cenário exploratório; inadequado para simultaneidade/aceite |
|177 timelines OddsPapi/DC | raw/Jan–Jun2026; fixture/participantes/torneio/season, bookmaker/selection, changedAt e recibo de aquisição |623.271.596B previamente íntegros; recebidos depois das decisões. Integridade não prova PIT; nenhum novo join de desfecho |
|3 capturas DC/1 fixture | prospective_pilot; última09/09 20:17:30.413563UTC; identidade congelada | Par API anteriormente rejeitado; estado comercial desconhecido. Não repetir piloto para fabricar amostra |
| Captura futura DC | decisão11/09 23:00UTC; kickoff12/09 00:00UTC; Pinnacle/bet365.bet.br | Dependente da coleta futura na janela; reserva20, quota/idempotência e helpers intocados |
| The Odds API v4 | https://the-odds-api.com/liveapi/guides/v4/; docs200; raw/hash em sources | Confirma endpoints/mercados/clocks; paid historical exige plano/quotas. Nenhuma chamada autenticada; históricos nominais ainda ausentes |
| Sportmonks paginação | https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/introduction/pagination.md | Cursor atual/has_more; cada página consome consulta; per_page não acompanha cursor. Código agora respeita orçamento e desconhece completude sem metadata |
| Sportmonks request/UTC | https://docs.sportmonks.com/v3/welcome/making-your-first-request.md e https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/introduction/set-your-time-zone.md | UTC padrão e parâmetro timezone confirmados. Raw timezone3731B SHA d0e7dc228de208a555ff3d89e173dafac415d760d6e2fb6aa1d5b07b81cf51ba. URL anterior timezones.md retornou200/Page Not Found; não contar como evidência |
| API-Football | documentation-v3 HTTPError sem status salvo no primeiro helper; guia oficial alternativo HTTP403 | Limitação do recibo antigo mantida. Não inventar o status faltante; não contornar bloqueio. Recebimento local não é publicação |
| Novo envelope Odds API | brasileirao_predictor/data/odds_api_snapshot.py; source_event_id, sport, home/away, bookmaker, market/line/selection/price, changed/received/published | Estrutura/identidade/hash testados; vazio/inválido preservados. published=null e comercial UNKNOWN; execução ABSTAIN. Não está integrado a H9 |
| Bitemporal | charter+entity+source+event/published/ingested+payload hash | Clocks UTC, versões em empate recusadas. Novo schema; schema anterior exige migração isolada explícita, não automática |
| Arquivos operacionais preservados | C:/BRASILEIRAO/DADOS_PRESERVADOS | Só metadados/contratos permitidos; nenhum conteúdo usado para pesquisa/validação CPL |

Campos de resultado entram apenas como labels nos estudos autorizados; suas revisões exigem recibo próprio. Features de escalação exigem ingestão antes do corte e vintage compatível. Preços agregados do serving ainda se associam aproximadamente por nome/data; não substituem IDs e oferta contemporânea. Ausência, suspensão e resposta inválida não autorizam recuperar uma cotação anterior favorável. Custos, limites, moeda, liquidez e capacidade desconhecidos permanecem desconhecidos.

Recuperação:7 GETs documentais diretos dentro do orçamento12; nenhuma cotação nova, API limitada, login, pagamento ou consumo da reserva. Os antigos bloqueios OddsPortal/Betfair em BE continuam registrados, sem repetição idêntica. Documentação foi integrada aos contratos/testes; não foi fabricada uma série de preços com base em exemplos.

Dependência decisiva: observação nominal simultânea e condições de preenchimento/custo. Os recursos atuais não estabelecem esse requisito. Sem ele, a conclusão de lucro executável continua impedida. A documentação [Scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app) não verifica o estado particular da automação; a consulta do aplicativo só produziu cartão de UI.
