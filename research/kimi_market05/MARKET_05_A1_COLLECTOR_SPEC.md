# MARKET-05 — Gate A1: Spec do Coletor de Snapshots de Odds

**Status:** congelado antes de qualquer coleta
**Data:** 2026-08-24
**Escopo:** somente coleta e validação de integridade/coverage.
**Proibido neste gate:** ROI, picks, stake, capital, execução de apostas,
alimentar `structural_edge.py` com dados não homologados.

O coletor e o detector são sistemas separados por contrato: o coletor comprova
integridade e coverage; o detector (`structural_edge.py`) só consome snapshots
com `homologated = true` após o Gate A1 PASS.

---

## 1. Fontes permitidas

### 1.1 Referência ("verdade")
| Fonte | Papel | Observação |
|---|---|---|
| Pinnacle (via API agregadora nomeada) | referência primária | fechamento e snapshots intraday |
| Betfair Exchange (back, mercados líquidos) | referência de fallback | ativa se Pinnacle indisponível > 24h |

### 1.2 Casas soft (alvo)
Mínimo de 5, preferência por 8–10, dentre as casas reguladas no Brasil
(licença SPA/MF). Lista inicial declarada ex ante e versionada:

| Casa | Acesso | Status |
|---|---|---|
| bet365 | agregador de odds | a confirmar |
| Betano | agregador de odds | a confirmar |
| Sportingbet | agregador de odds | a confirmar |
| EstrelaBet | agregador de odds | a confirmar |
| Superbet | agregador de odds | a confirmar |
| (reservas) KTO, Novibet, Betfair SB | agregador | a confirmar |

Regras:
- Toda fonte deve ser nomeada e versionada (`source_id` + `source_version`).
- SofaScore agregado permanece `DIAGNOSTIC_ONLY` e **jamais** entra neste pipeline.
- Se uma fonte exigir scraping não oficial, ela entra como candidata separada e
  só é promovida após 7 dias de estabilidade observada.

## 2. Mercados e linhas aceitos (v1)

| Mercado | Linhas | Seleções |
|---|---|---|
| 1X2 | — | home, draw, away |
| Over/Under | 1.5, 2.5, 3.5 | over, under |
| BTTS | — | yes, no |
| Dupla chance | — | 1X, 12, X2 |

Fora de escopo na v1: handicaps asiáticos, escanteios, cartões, props, live.
Qualquer mercado novo exige emenda a este documento e novo período de homologação.

## 3. Schema append-only do snapshot

Armazenamento: JSONL append-only (um arquivo por dia, imutável após rollover),
com hash-chain igual ao ledger prospectivo. Schema canônico:

```json
{
  "snapshot_id": "sha256 dos campos canônicos",
  "event_id": "identidade canônica do evento (ver §4)",
  "bookmaker": "pinnacle|bet365|...",
  "market": "1X2|OU|BTTS|DC",
  "line": 2.5,
  "selection": "over",
  "odd": 1.95,
  "captured_at": "2026-08-24T18:00:00Z (UTC, obrigatório)",
  "kickoff_at": "2026-08-24T19:00:00Z (UTC, obrigatório)",
  "source_id": "odds_api_v4",
  "mapping_version": "2026-08-24.v1",
  "market_status": "open|suspended",
  "hash_prev": "primeiros 16 hex do hash da linha anterior"
}
```

Invariantes (testadas por contrato):
1. `captured_at < kickoff_at` (PIT estrito), timezone-aware obrigatório.
2. `odd` finita e `> 1.0`.
3. Append-only: nenhuma linha é editada; correções são novas linhas com
   `supersedes: <snapshot_id>`.
4. Rollover diário sela o arquivo do dia anterior (SHA-256 do arquivo registrado).

## 4. Identidade canônica

### 4.1 Evento
`event_id = f"{league}|{season}|{canonical_home}|{canonical_away}|{kickoff_date}"`
- Tabela de aliases de times versionada (`mapping_version`); todo nome vindo de
  fonte passa pelo alias table. Alias desconhecido → snapshot entra em
  quarentena (`identity_status: unresolved`), nunca no fluxo principal.
- Nenhum matching fuzzy automático no caminho principal. Fuzzy pode
  *sugerir* alias para revisão humana, nunca decidir.

### 4.2 Mercado/linha/seleção
- Enumeração fechada por fonte → vocabulário canônico (tabela versionada).
- Linha é `float` obrigatório para OU (`null` só em 1X2/BTTS/DC).
- Seleções no vocabulário canônico (`home|draw|away|over|under|yes|no|1X|12|X2`).

### 4.3 Deduplicação e conflitos
- Mesma `(event_id, bookmaker, market, line, selection, captured_at)` → dedupe
  mantendo o primeiro (append-only).
- Mesma chave com odd diferente no mesmo segundo → manter ambos e marcar
  `conflict: true`; conflitos são excluídos do cálculo de coverage e sinalizados.

## 5. Timestamps, cadência e janela

- Cadência de coleta: **1 snapshot por fonte a cada 15 minutos** por evento;
  janela: de T-72h até kickoff (sem coleta pós-kickoff na v1).
- Staleness máxima da referência para futura detecção: **300s** (já congelado
  no detector; o coletor deve garantir cadência compatível nos últimos 60 min
  pré-kickoff: sugerido 5 min nesse intervalo).
- Todo timestamp é UTC no armazenamento; conversão de fuso da fonte acontece
  na ingestão e é testada (casos: BRT, BST/horário de verão, fontes em UTC+0).

## 6. Suspensão, mudança de linha e odds inválidas

| Evento | Tratamento |
|---|---|
| `market_status: suspended` | snapshot registrado normalmente; excluído de coverage "operável" |
| Linha some e reaparece com outro valor | são linhas distintas (2.5 ≠ 3.0); nunca reescrever |
| Odd fora de [1.01, 1000] | rejeitada na ingestão, logada em quarentena |
| Evento reagendado (kickoff muda) | novo `event_id`; o antigo recebe `superseded_by` |
| Fonte retorna mercado incompleto (ex.: falta "draw") | snapshot parcial permitido, mas evento não conta como completo para coverage |

## 7. Métricas de coverage e continuidade

Por dia e agregado no período de homologação:
- **event_coverage**: % de eventos da Série A com ≥ 1 snapshot completo por
  casa (alvo: ≥ 90% por casa);
- **market_coverage**: % dos pares evento×mercado v1 com as seleções completas;
- **continuity**: % das janelas de 15 min com snapshot presente entre T-6h e
  kickoff (alvo: ≥ 95%);
- **freshness**: distribuição de `now - captured_at` no fechamento;
- **identity_resolution_rate**: % de snapshots fora de quarentena (alvo ≥ 99%);
- **conflict_rate**: alvo < 0,1%.

## 8. Auditoria humana (50 eventos)

Após 7 dias de coleta contínua:
1. Amostra aleatória (seed registrada) de **50 eventos** com todos os mercados v1.
2. Para cada evento, verificar manualmente contra os sites das casas:
   - identidade (times, data, kickoff);
   - odds de abertura e de fechamento (±1 tick);
   - nomes de mercado/linha/seleção corretamente mapeados.
3. Critério: **≥ 48/50 corretos e zero erro de identidade**. Erro de identidade
   é falha fatal independentemente da contagem.
4. Resultado registrado em `docs/experiments/MARKET_05_A1_AUDIT.md` com evidências.

## 9. Critérios exatos do Gate A1

**PASS exige TODOS:**
- [ ] ≥ 5 casas soft + 1 referência (Pinnacle ou fallback ativado e documentado);
- [ ] 7 dias contínuos de coleta sem gap > 1h;
- [ ] event_coverage ≥ 90% em cada casa;
- [ ] market_coverage ≥ 95% nos mercados v1;
- [ ] continuity ≥ 95% (T-6h → kickoff);
- [ ] identity_resolution_rate ≥ 99%;
- [ ] conflict_rate < 0,1%;
- [ ] auditoria humana: ≥ 48/50 e zero erro de identidade;
- [ ] testes contratuais verdes; schema congelado com hash registrado.

**FAIL em qualquer item** → corrigir a causa e reiniciar os 7 dias de homologação
(o relógio não continua de onde parou).

**Após PASS:** snapshots passam a receber `homologated: true` e só então podem
alimentar `structural_edge.py` em modo shadow. Gate A2 (auditoria de alertas)
continua exigido antes de qualquer paper-trading.

## 10. Proibições deste gate

- Nenhum cálculo de ROI, EV operacional, pick ou stake.
- Nenhuma execução de aposta ou automação contra casas.
- Nenhuma tática de evasão de limitação.
- Nenhum dado pós-kickoff entra no pipeline v1.
- Nenhum uso de SofaScore agregado como fonte.
