# Branch-aware coverage

| Classificação | Coberto | Possível | Cobertura |
|---|---:|---:|---:|
| runtime_homologado | 1660 | 2043 | 81.25% |
| kernel | 229 | 281 | 81.49% |
| integracao_redis | 229 | 281 | 81.49% |
| providers | 308 | 369 | 83.47% |
| pesquisa | 89 | 2146 | 4.15% |
| migracao | 281 | 766 | 36.68% |
| legado | 1877 | 6197 | 30.29% |

Cobertura global branch-aware: **37.65%**.

Worker .NET (collector Cobertura): **85,15% linhas / 80,92% branches**.

A cobertura global inclui pesquisa, migração e legado sem exclusões silenciosas.

## Lacuna conhecida — venue/estádio

Os 32 erros diagnósticos de Internacional/Bahia em 2026 têm `matches.city`
vazio. A tabela não possui identidade de estádio e nenhum valor foi inferido.

Schema proposto para uma migração futura, sem aplicação nesta sessão:

- `matches.venue_id TEXT NULL`: identificador estável da fonte declarada;
- `matches.neutral INTEGER NOT NULL DEFAULT 0`: coluna já existente, preservar;
- `matches.actual_stadium TEXT NULL`: nome observado, com proveniência;
- metadados PIT em tabela de linhagem: `source`, `available_at`,
  `retrieved_at`, `source_event_id` e versão do mapping.

Critério de preenchimento: somente fonte explícita e auditável. Cidade, mando
nominal ou nome do clube não podem ser usados para inferir estádio.

## OddsPapi A1 — lacunas da PoC

No snapshot de Botafogo×Athletico-PR em 2026-08-24, a fonte retornou 185
bookmakers. Pinnacle, Betano BR, EstrelaBet, Superbet BR e KTO tinham 1X2
simultâneo. Sportingbet BR estava no evento, mas sem o mercado canônico `101`;
Pixbet não apareceu. OU2.5 e BTTS ainda não foram homologados e qualquer linha
detectada entra com `identity_status=unverified` até auditoria humana.

Reteste read-only de 2026-08-24: não existiam snapshots posteriores à PoC.
Logo, não há nova evidência sobre mercado 101 da Sportingbet BR nem presença
da Pixbet; as duas lacunas permanecem abertas, sem inferência por ausência.
