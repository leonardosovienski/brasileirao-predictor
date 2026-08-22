# Registro de fontes históricas

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
