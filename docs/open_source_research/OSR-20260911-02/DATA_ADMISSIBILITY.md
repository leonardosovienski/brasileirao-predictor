# Fontes finalistas — inspeção documental

Não foram baixadas amostras reais: não havia um subconjunto comprovadamente fora das linhagens protegidas e admitido. Cobertura anunciada não equivale a cobertura inspecionada. UNKNOWN permanece desconhecido. Fontes web abaixo foram consultadas nesta rodada, exceto R058 explicitamente herdada.

| ID | Fonte | Uso possível | Lacuna material |
|---|---|---|---|
| R021 | Football-Data.co.uk | Descrição/esquema. Fechamento não substitui T−60. BE 2012–24 permanece protegido. | Faltam vintage T−60, relógios observados e autorização de coorte. Não resolver redownloadando BE. |
| R022 | football-data.org | Calendário/contexto prospectivo condicionado; histórico PIT não comprovado. | Faltam temporadas, odds nominais/vintages, relógios e termos aplicáveis ao uso concreto. |
| R051 | The Odds API | Possível replay histórico condicionado; não automaticamente admissão temporal estrita. | Faltam cobertura nominal brasileira, versão imutável, relógios verificáveis, licença aplicada e coorte autorizada. |
| R052 | Sportmonks | Candidato prospectivo condicionado; não presumir backfill de anos. | Janela curta de histórico, cobertura e direitos não comprovados; nenhum arquivo retrospectivo próprio admissível. |
| R058 | CBF / calendário | Documentação contextual; descanso/contexto já possuem implementação local. | Faltam versões e disponibilidade históricas, autorização e mapeamento. |

## R021 — Football-Data.co.uk

coverage: Brasil anunciado desde 2012/13; página Brasil atualizada em 08/09/2026. Inspeção documental, nenhum CSV nesta rodada.

fields: Data/hora do jogo, nomes, placar/resultado e odds de fechamento; máximas/médias não são bookmaker nominal.

identity: Nomes/data; mapeamento canônico e ID histórico UNKNOWN.

clocks: Hora do jogo não é publicação/captura de odds; revisão histórica UNKNOWN.

access: Downloads gratuitos; sem chamada nem nova amostra.

rights: Uso anunciado para previsão de partidas; licença ampla de redistribuição não estabelecida.

cost: Gratuito na página; quota UNKNOWN.

action: Obter documentação de clocks e autorização de subconjunto independente antes de amostra.

[Documentação 1](https://football-data.co.uk/brazil.php); [Documentação 2](https://football-data.co.uk/data.php); [Documentação 3](https://football-data.co.uk/notes.txt)

## R022 — football-data.org

coverage: Série A anunciada no free tier; cobertura de odds para Brasil/temporadas não verificada.

fields: Fixtures/resultados e IDs na documentação; histórico de revisões/publicação por campo UNKNOWN.

identity: IDs de provedor; vínculo canônico e inversão de mando precisam ser auditados.

clocks: lastUpdated não prova recebimento histórico nem conhecimento de cada campo.

access: Chave/registro requeridos; não autenticado.

rights: Termos servidos em /about, datados 01/06/2018: chave para uma aplicação, atribuição; restrições após cancelamento e direitos separados de logos.

cost: Free €0/10 chamadas por minuto; ML Light €29/mês, dez temporadas, 20/min; odds add-on €15/mês com plano regular, sujeito a cobertura/VAT.

action: Solicitar matriz documental Brasil/temporada e esquema histórico; não contratar ou consumir chave nesta autorização.

[Documentação 1](https://www.football-data.org/coverage); [Documentação 2](https://www.football-data.org/pricing); [Documentação 3](https://www.football-data.org/documentation/quickstart); [Documentação 4](https://www.football-data.org/about)

## R051 — The Odds API

coverage: Histórico anunciado desde 06/06/2020; 10 min, desde setembro/2022 5 min. Brasil/bookmaker/temporada exatos UNKNOWN.

fields: event id, sport_key, commence_time, home/away, bookmaker, market, outcomes price, last_update e envelope timestamp/previous/next.

identity: ID do evento e nomes; mapa canônico/versionado não fornecido nesta rodada.

clocks: Consulta devolve snapshot anterior ou igual à data. Timestamp do arquivo não é nosso receipt antigo; revisões e autenticidade precisam de evidência.

access: Histórico somente pago; nenhuma API chamada.

rights: Termos de 31/08/2026 permitem retenção, pesquisa/ML e derivados; proíbem redistribuição/revenda de feed bruto ou produto de download bruto.

cost: Histórico: 10 créditos × mercados × regiões; plano/quotas disponíveis UNKNOWN.

action: Obter catálogo e metadados de arquivo sem quota; amostra somente após autorização específica de acesso e linhagem.

[Documentação 1](https://the-odds-api.com/liveapi/guides/v4/); [Documentação 2](https://the-odds-api.com/terms-and-conditions.html)

## R052 — Sportmonks

coverage: Histórico de odds documentado até sete dias após kickoff; Brasil/temporada/bookmaker UNKNOWN.

fields: Odds premium com abertura/mudanças e last_updated; starting_at/fixture ID. Payload real não inspecionado.

identity: Mapeamento e revisões de fixture UNKNOWN.

clocks: last_updated não é receipt; FAQ do feed padrão admite atrasos até 20 min, não generalizar a todo premium.

access: Premium depende de plano pago; não ativado.

rights: Licença contratual para o uso pretendido não inspecionada: UNKNOWN.

cost: Preço/quota do contrato pretendido UNKNOWN.

action: Obter especificação contratual/cobertura; coleta prospectiva só com autorização própria, sem alterar agendamento atual.

[Documentação 1](https://www.sportmonks.com/faq/); [Documentação 2](https://www.sportmonks.com/glossary/premium-odds-feed/); [Documentação 3](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints)

## R058 — CBF / calendário

coverage: Referência de calendário 2026 da rodada anterior; não recertificada nesta rodada.

fields: Calendário/contexto; clocks históricos, revisão e direitos UNKNOWN.

identity: Vínculo canônico precisa de evidência.

clocks: Não confundir data de calendário com disponibilidade por revisão.

access: Nenhuma consulta de resultado ou amostra.

rights: UNKNOWN para redistribuição.

cost: UNKNOWN para extração pretendida.

action: Resolver linhagem de contexto existente antes de adicionar fonte/feature.



A página Football-Data alerta que odds Pinnacle estão sistematicamente desatualizadas desde 23/07/2025 e foram excluídas dos agregados indicados. Isso é alerta documental sobre aquela fonte; não diagnóstico de toda oferta Pinnacle. Uso descritivo, replay condicionado e admissão temporal são estados distintos. Nenhuma fonte obteve admissão para N05 nesta rodada.
