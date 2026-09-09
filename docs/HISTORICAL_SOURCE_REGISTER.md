# Registro de fontes históricas

## Verificação DC-20260909 — 09/09/2026

Aceitação de uma fonte para um uso técnico não significa aceitação econômica
de todos os seus dados. Contratos, captura, estado e período são avaliados
por observação. [Resultado e recibos](continuation/data_completion_2026-09-09/RESULTADO.md).

| Fonte verificada | Aquisição e cobertura | Estado para esta rodada | Pendência decisiva |
| --- | --- | --- | --- |
| [OddsPapi histórico](https://oddspapi.io/us/docs/get-historical-odds) | 177/177 timelines Jan–Jun/2026, Pinnacle e Bet365; conta existente e histórico sem incremento de quota | Histórico exploratório adquirido | Sem receipt histórico local, calendário PIT e prova de disponibilidade contínua |
| [OddsPapi atual](https://oddspapi.io/us/docs/get-odds) | Três capturas reais, Pinnacle / bet365.bet.br | Oferta rejeitada por bookmakerIsActive=false | Nova observação ativa antes do corte; limite/custos não demonstrados |
| [Football-Data Brasil](https://football-data.co.uk/brazil.php) | BRA.csv oficial recuperado sem www; 380 jogos de 2025, 158 pares closing numéricos | Cenário condicional com referência comprometida | [Aviso oficial](https://football-data.co.uk/data) de Pinnacle desatualizada desde 23/07/2025; clocks e execução ausentes |
| [The Odds API histórico](https://the-odds-api.com/historical-odds-data/) | Documentação pública; API autenticada não consumida | Alternativa paga, não adquirida | Plano, acesso e custo não autorizam compra nesta rodada |
| [Odds-API.io gratuito](https://odds-api.io/pricing/free) | Documentação pública; sem nova conta | Alternativa não adquirida | Restrições de casas sharp no plano gratuito |
| [Betfair histórico](https://betfair-datascientists.github.io/data/usingHistoricDataSite/) | Guia público; basic com preço negociado, níveis superiores com mais dados | Download não realizado | Login necessário; preço negociado não equivale a ladder executável com volume |

As fontes novas não fornecem por si só limites pessoais, slippage, confirmação
de aceite, custo total ou amostra prospectiva de validação. Campos ausentes
permanecem desconhecidos. Não reutilizar resultados H14/H15/H9/A1 para completá-los.

## Registro anterior preservado

Os estados abaixo são a classificação histórica do projeto. Não comprovam
configuração, cobertura, disponibilidade ou operação ativa nesta máquina.

| Fonte | Origem/licença | Cobertura | Odds PIT/bookmaker | Estado | Limitação |
|---|---|---|---|---|---|
| The Odds API v4 | chave opt-in; plano e termos do fornecedor | catálogo inclui `soccer_brazil_campeonato` | `bookmakers[].key`, `last_update`, totals e ID de evento | `SOURCE_ACCEPTED_REQUIRES_CONFIGURATION` | exige `ODDS_API_KEY`, confirmar cobertura/bookmaker da região na primeira chamada; histórico pago |
| Sofascore | API/cache operacional do projeto; termos do provedor | Brasileirão 2024–2026 | odds de jogo vivas; fechamento conforme contrato local | `SOURCE_ACCEPTED` para pipeline vivo | histórico não deve ser reconstruído a partir de tabela final |
| Sofascore lineups cache | cache operacional imutável por evento | jogadores 2021–2026 | posição e estatísticas pós-jogo, com `available_at` | `SOURCE_ACCEPTED` para agregado de temporada | só é PIT-seguro depois de `available_at`; não usar o total final dentro da própria temporada |
| API-Football | API opt-in `v3.football.api-sports.io`; licença/plano dependentes da conta | Série A 2022–2024 no plano usado | fixtures e placares; sem captura/bookmaker/closing suficiente | `SOURCE_QUARANTINED` | válida para cobertura de resultados, não para ROI/CLV |
| Sportmonks | API opt-in `api.sportmonks.com`; licença/plano dependentes da conta | depende do token e liga acessível | não confirmado | `SOURCE_PENDING_REVIEW` | sem credencial e sem auditoria de odds |
| CSVs públicos genéricos | origens variadas | variável | normalmente sem `available_at`/bookmaker | `SOURCE_REJECTED` | volume não substitui proveniência point-in-time |

Uma fonte só pode mudar para `SOURCE_ACCEPTED` econômica após evidenciar
bookmaker, odds brutas, timestamps e definição de closing reproduzível.
