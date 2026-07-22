# Registro de fontes históricas

| Fonte | Origem/licença | Cobertura | Odds PIT/bookmaker | Estado | Limitação |
|---|---|---|---|---|---|
| Sofascore | API/cache operacional do projeto; termos do provedor | Brasileirão 2024–2026 | odds de jogo vivas; fechamento conforme contrato local | `SOURCE_ACCEPTED` para pipeline vivo | histórico não deve ser reconstruído a partir de tabela final |
| API-Football | API opt-in `v3.football.api-sports.io`; licença/plano dependentes da conta | Série A 2022–2024 no plano usado | fixtures e placares; sem captura/bookmaker/closing suficiente | `SOURCE_QUARANTINED` | válida para cobertura de resultados, não para ROI/CLV |
| Sportmonks | API opt-in `api.sportmonks.com`; licença/plano dependentes da conta | depende do token e liga acessível | não confirmado | `SOURCE_PENDING_REVIEW` | sem credencial e sem auditoria de odds |
| CSVs públicos genéricos | origens variadas | variável | normalmente sem `available_at`/bookmaker | `SOURCE_REJECTED` | volume não substitui proveniência point-in-time |

Uma fonte só pode mudar para `SOURCE_ACCEPTED` econômica após evidenciar
bookmaker, odds brutas, timestamps e definição de closing reproduzível.
