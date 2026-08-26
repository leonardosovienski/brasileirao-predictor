# bet_engine — Motor de Edge Estrutural

## O que é
Pipeline completo de detecção e validação de edge estrutural em apostas:
comparar Pinnacle (devig = "verdade") contra casas soft BR. Sem modelo preditivo —
o edge vem da estrutura do mercado, não de prever futebol.

## Arquivos
- `bet_engine.py` — devig (proporcional/power/shin), detector +EV, detector de arb,
  power analysis, PSR/DSR, ROI com IC bootstrap
- `paper_ledger.py` — ledger imutável (hash-chain) de paper-trading com CLV obrigatório
  e gate de capital (DSR ≥ 0.95 + CLV > 0 + IC ROI > 0 → ELIGIBLE_FOR_REVIEW)
- `test_bet_engine.py` — 13 testes (pytest)

## Validação executada (dados sintéticos retrospectivos)
| Cenário | Resultado |
|---|---|
| Casa lenta com edge real 8–18% | detectada: ROI +13,7%, CLV +9,8%, DSR 0,999 |
| Casa justa (controle) | 0/200 falsos positivos; detector silencia |
| Ledger com edge 5%, n=400 | CLV +2,6% (100% positivas) + CAPITAL_LOCK (comportamento correto) |
| Shin em zebra pesada | favorito 74,6% → 81,6% (correção FLB como na literatura) |

## Integração com o projeto
1. Copiar para `src/research/bet_engine/` no clone local.
2. O coletor de odds grava snapshots (Pinnacle + casas BR) com timestamp PIT.
3. Runner compara snapshots via `detect_ev` por evento/mercado/seleção.
4. Alertas entram no `PaperLedger` ANTES do kickoff (assert embutido).
5. Fechamento Pinnacle registrado no apito inicial → CLV.
6. `ledger.relatorio()` a cada rodada. Capital só quando CAPITAL_GATE = ELIGIBLE_FOR_REVIEW.

## Regras invioláveis (não remover)
- flat stake no paper-trading
- assert ts_capture < kickoff (PIT)
- liquidar sem closing_odd é proibido (CLV obrigatório)
- trials_declarados ex ante no ledger (alimenta o DSR)
- threshold EV inicial: 3% (declarado; mudança = novo trial registrado)
- staleness máximo da linha Pinnacle: 300s

## Próximos passos (ordem)
1. Coletor: 5+ casas BR + Pinnacle, snapshot 15min, 7 dias de shadow → Gate A1
2. Auditoria manual de 50 alertas (mapping/staleness) → Gate A2
3. Paper-trading → Gate A3 (DSR ≥ 0,95 + CLV > 0)
4. Motor B (arbs/promos): `detect_arb` já pronto, começa junto com o coletor
