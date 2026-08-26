# LIVE_FEASIBILITY_01 — Gate L0 de dados para backtest live

Estado congelado em 2026-08-24: **`HOLD_NO_LIVE_VIABILITY_GO`**.

Esta é pesquisa documental, não teste de modelo. Nenhuma assinatura, coleta,
compra, treino, pick ou execução foi realizada. `CAPITAL_GATE: LOCKED`.

## Critério e orçamento

Um backtest live honesto exige, para os mesmos jogos do Brasileirão e por pelo
menos duas temporadas: eventos point-in-time, odds realmente in-play, estados
de suspensão/reabertura, delay de aceitação e preço disponível depois do
delay. “Produto disponível” não equivale a coverage comprovada.

Teto declarado para projeto pessoal: **USD 600/ano no total**, incluindo
eventos e odds. Preço sob consulta não é tratado como compatível até existir
proposta escrita abaixo desse teto.

## Eventos históricos

| Fornecedor | O que existe | Brasileirão e temporadas | Tempo/formato | Custo público | L0 |
| --- | --- | --- | --- | --- | --- |
| Sportradar Soccer | Timeline histórica, live timeline e push events; gols, cartões e substituições dependem do tier de coverage | A documentação diz, como regra geral, temporada atual + 2 anteriores, podendo chegar a 2007; a matriz/Season Info precisa confirmar Série A e profundidade por temporada | JSON/XML; eventos incluem UTC `time`, minuto e `match_clock` com segundos | não público/contato comercial | **não comprovado** |
| Stats Perform / Opta | Feeds estruturados históricos e live, eventos on-ball e produtos enriquecidos | licenciamento pode ser por competição/país, mas não há matriz pública que prove duas temporadas da Série A no pacote proposto | API/feed proprietário; granularidade de evento rica | orçamento customizado; produto orientado a organizações | **não comprovado** |
| API-Football | Fixtures Events, lineups, statistics, livescore e in-play odds; Série A aparece na lista de coverage | coverage “pode variar por temporada/fixture”; a página pública não prova completude de duas temporadas nem arquivo histórico de odds live | JSON; eventos usam relógio de jogo/minuto, não foi comprovado timestamp UTC de segundo por evento | Free USD 0; Pro USD 19/mês; Ultra USD 29; Mega USD 39 | **PoC possível, evidência insuficiente** |
| FootyStats | resultados e agregados de gols, cartões, escanteios e xG | Série A listada, mas atualização declarada a cada 20 minutos e foco em agregados | JSON; não é timeline PIT de eventos | Hobby GBP 29,99/mês; Serious GBP 69,99 | **não serve para L0** |
| StatsBomb Open Data | JSON de matches, lineups, events e 360 para competições selecionadas | `competitions.json` não contém Brasileirão Série A | JSON de eventos detalhados | gratuito com atribuição | **não** |

Fontes: [Sportradar Historical Data](https://developer.sportradar.com/soccer/docs/soccer-ig-historical-data),
[Sportradar Sport Event Timeline](https://developer.sportradar.com/soccer/reference/soccer-sport-event-timeline),
[Stats Perform — produtos e feeds](https://www.statsperform.com/faqs/stats-perform-faqs-opta-brand-data-products/),
[Stats Perform — preço/licença](https://www.statsperform.com/pt-br/faqs/stats-perform-faqs-pricing-licensing/),
[API-Football coverage](https://www.api-football.com/coverage),
[API-Football pricing](https://www.api-football.com/pricing),
[FootyStats API](https://footystats.org/api),
[StatsBomb Open Data](https://github.com/hudl/open-data) e
[catálogo StatsBomb](https://raw.githubusercontent.com/hudl/open-data/master/data/competitions.json).

### xG

Nenhuma fonte pessoal acima comprovou xG histórico point-in-time publicado no
instante de cada evento para duas temporadas da Série A. xG pós-jogo ou
agregado não pode ser recarimbado como PIT. Sportradar/Opta podem oferecer
camadas avançadas por contrato; isso permanece não verificado.

## Odds live históricas

| Fonte | Histórico e granularidade | Série A | Suspensão/delay | Custo | L0 |
| --- | --- | --- | --- | --- | --- |
| Betfair Historical Data — Exchange | dados desde abril/2015; ADVANCED contém best back/lay e volume; `pt` é epoch em milissegundos | catálogo autenticado permite filtrar, mas não há prova pública anexável de duas temporadas completas da Série A e mercados requeridos | `status` OPEN/SUSPENDED/CLOSED, `inPlay`, mudanças de market definition e `betDelay` | Soccer ADVANCED GBP 69/mês ou GBP 699/ano; PRO GBP 230/mês ou GBP 2.299/ano | **candidato mais forte, coverage não comprovada** |
| The Odds API | histórico desde 2020; 10 min até set/2022 e 5 min depois; Série A e Pinnacle aparecem na oferta geral | Série A é coberta, mas a documentação histórica não garante que snapshots arquivados sejam in-play; 5 min não resolve suspensão pós-gol | não fornece semântica de aceitação/suspensão equivalente ao Exchange | histórico a partir de USD 30/mês | **não** |
| Pinnacle in-play | preços in-play existem operacionalmente | não foi encontrado arquivo histórico oficial self-service para replay | política e histórico de suspensão/delay não publicados como dataset | não público | **não** |
| API-Football in-play odds | endpoint live incluído em todos os planos | Série A listada | não foi comprovado arquivo histórico timestamped de odds/suspensão | USD 19–39/mês | **não** |
| FootyStats e agregadores baratos | estatísticas/agregados; não ladder ou snapshots executáveis | variável | ausente | GBP 29,99+/mês | **não** |

Fontes: [Betfair — conteúdo do Historical Data](https://support.developer.betfair.com/hc/en-us/articles/360002407732-What-data-is-provided-by-the-Historical-Data-service),
[especificação do feed](https://historicdata.betfair.com/files/Betfair-Historical-Data-Feed-Specification.pdf),
[preço anual Betfair](https://support.developer.betfair.com/hc/en-us/articles/360019984158-Are-bulk-purchase-discounts-available),
[The Odds API historical](https://the-odds-api.com/historical-odds-data/) e
[preços/cobertura The Odds API](https://the-odds-api.com/).

## Delay, suspensão e margem

- Betfair informa delay in-play usual de 1–12 segundos e expõe o valor real em
  `betDelay`; em 2026, a empresa informou que 95% dos jogos de futebol estavam
  em 5 segundos, sem garantir o mesmo para a Série A.
- No futebol Exchange, gol, pênalti e expulsão são “Material Events”; falha de
  suspensão pode levar a void retrospectivo. VAR também pode anular negócios
  no intervalo afetado.
- O feed histórico ADVANCED preserva mudanças de status e preços, permitindo
  replay do Exchange. Isso não documenta delay ou rejeição de casas BR.
- Não existe “margem típica” congelável como constante. No Exchange há
  comissão e spread/liquidez; em fixed odds o overround deve ser medido em cada
  timestamp. Assumir margem pré-jogo ou custo zero invalida o backtest.

Fontes: [Betfair — bet delay](https://support.developer.betfair.com/hc/en-us/articles/360002825652-Why-do-you-have-a-delay-on-placing-bets-on-a-market-that-is-in-play),
[Betfair — regras in-play e Material Events](https://support.betfair.com/app/answers/detail/a_id/10620/) e
[Betfair Exchange newsletter 2026](https://betting.betfair.com/betfair-announcements/exchange-news/betfair-exchange-april-newsletter-asian-handicap-corners-and-the-return-of-the-ipl-250326-1392.html).

## Custo mínimo plausível

Combinação self-service mais barata que merece PoC: API-Football Pro
(`USD 228/ano`) + Betfair Soccer ADVANCED (`GBP 699/ano`), antes de impostos,
câmbio, armazenamento e eventual licença específica. Ela já excede o teto de
USD 600/ano e ainda não prova o join completo evento↔mercado para a Série A.
Opta/Sportradar têm preço sob consulta e portanto não passam o gate de custo.

## Gate L0

- [ ] **(a) NÃO** — não há evidência anexável de eventos timestamped completos
  por pelo menos duas temporadas do Brasileirão sob uma licença compatível.
- [ ] **(b) NÃO** — Betfair é tecnicamente adequado, mas a coverage Série A
  por duas temporadas/mercados não foi comprovada; os demais não oferecem
  histórico in-play com suspensão e granularidade adequada.
- [ ] **(c) NÃO** — o mínimo plausível excede USD 600/ano.
- [x] **(d) SIM, somente Betfair Exchange** — `pt`, status, suspensão e
  `betDelay` permitem simulação documentada; casas BR continuam sem contrato.

Como há respostas NÃO: **`HOLD_NO_LIVE_VIABILITY_GO`**. Nenhum L1, modelo de
estado, treino ou backtest live pode ser iniciado.

## Próxima ação única recomendada

Executar uma PoC gratuita/de catálogo, limitada a comprovar coverage: obter do
Betfair Historical Data a lista de mercados de uma temporada da Série A e
confirmar `MATCH_ODDS`, `OVER_UNDER_25`, `inPlay`, `pt`, `status` e `betDelay`,
sem comprar pacote completo. Se essa prova não for possível sem pagamento,
não gastar: priorizar o **Motor A / coletor Pinnacle×soft, Gate A1**.

