# MARKET-05 — Gate A1 Collector Spec

Versão congelada reconstruída em 2026-08-24 a partir do protocolo fornecido
pelo operador. Fonte v1: `oddspapi_v4`; torneio 325; modo `SHADOW_ONLY`;
`CAPITAL_GATE: LOCKED`.

## 1. Invariantes

O coletor não importa nem chama `structural_edge.py`. Toda linha possui
`homologated=false`; ROI, EV operacional, pick, stake e execução são proibidos.
A chave existe somente em `ODDSPAPI_KEY`. SofaScore agregado e endpoints
históricos são proibidos. O coletor escreve apenas sob
`data/odds_snapshots/`, `data/odds_quarantine/`, `data/collector_state/` e
`data/collector_metrics/`. `matches.db`, serving e caches são intocados.

## 2. Fonte e escopo

- descoberta: `GET /v4/fixtures?sportId=10&tournamentId=325&from=...&to=...`;
- captura: `GET /v4/odds?fixtureId=...`;
- referência: Pinnacle;
- softs: Betano BR, EstrelaBet, Sportingbet BR, Superbet BR, KTO e Pixbet;
- mercados: 1X2 canônico; OU2.5/BTTS entram como `unverified` até auditoria;
- nenhum timestamp com `captured_at >= kickoff_at` é aceito.

## 3. Identidade

`data/team_aliases.json` é versionado. Nome desconhecido vai para quarentena;
fuzzy matching apenas sugere revisão humana. O identificador é
`br-serie-a|2026|{home}|{away}|{kickoff_date}`. Evento reagendado recebe novo
ID pela nova data. Linha/seleção/mercado nunca são inferidos entre eventos.

## 4. Persistência

Cada seleção é uma linha conforme `schemas/odds_snapshot_v1.json`, com
`additionalProperties=false`. Arquivos JSONL são diários e append-only;
`hash_prev`/`hash_self` formam uma cadeia verificável. Rollover diário gera
`.seal.json` com SHA-256. Repetição byte-semântica é deduplicada; mesma
identidade com valor diferente é conflito em quarentena. Correções futuras
somente por nova linha com `supersedes`; nunca há update destrutivo.

## 5. Cadência e orçamento

O free tier declarado tem 250 requests/mês. A cadência completa de 15 min e
5 min em T-1h é incompatível. O modo econômico usa quatro snapshots por
evento (T-24h/T-6h/T-1h/T-10m) e descoberta semanal:

`4 × 60 fixtures + 5 descobertas = 245 requests/mês`.

Portanto ele só cabe até aproximadamente 61 fixtures/mês e deve monitorar a
cota. O job local pode rodar a cada 15 min porque só chama `/odds` quando uma
janela ainda não capturada vence; descoberta é uma tarefa semanal separada.
Este modo é ensaio de pipeline e **não mede continuity**.

## 6. Métricas

O job diário grava event coverage, market coverage, continuity, freshness,
identity resolution rate, conflict rate, fontes e contagens mínimas. No modo
econômico, `continuity=null` por construção.

## 7. Gate A1

O avaliador mecânico exige simultaneamente:

1. Pinnacle + pelo menos cinco softs;
2. sete dias consecutivos;
3. nenhum gap maior que uma hora;
4. event coverage >=90%;
5. market coverage >=95%;
6. continuity >=95%;
7. identity resolution >=99%;
8. conflict rate <0,1%;
9. auditoria humana de 50 eventos e testes contratuais verdes.

Falha em qualquer item produz `FAIL_RESTART_CLOCK`. Qualquer dia econômico
produz `REHEARSAL_ONLY`, nunca PASS. Capital continua bloqueado mesmo após
PASS; homologação apenas permite conectar o detector em mudança posterior.

## 8. Fase 0 OU2.5 sem labels

O contrato `contracts/a1-ou25-phase0-policy.json` e o runner
`scripts/a1_phase0.py` governam a calibração operacional anterior a qualquer
coorte econômica. A fase é fingerprinted e append-only, aceita somente
cobertura, disponibilidade, latência e sensibilidade da referência e rejeita
resultado, closing, CLV, ROI, P&L e settlement em qualquer nível do payload.
O procedimento completo está em `docs/A1_OU25_PHASE0_RUNBOOK.md`.
