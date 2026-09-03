# Evidence Registry — market incrementality

The 2025 holdout is consumed and is never described as blind. Historical SofaScore
aggregates are not a same-cutoff bookmaker baseline. The three claims below remain
separate so horizon selection cannot be hidden.

| Claim ID | Claim | State | L | Q | Evidence/effect/CI | Limitations | Selection path | Decision |
|---|---|---|---|---|---|---|---|---|
| CLAIM-BR-MARKET-001 | Model has incremental information vs market at H-24h | BLOCKED_PENDING_PIT_FEATURES | HISTORICAL_PIT | COVERAGE_AUDITED | no model comparison executed | 245/245 odds coverage in 2026; no multi-season odds; feature availability not proven; 3 snapshots older than 24h | EXP-001 → H24, fixed before results | no claim |
| CLAIM-BR-MARKET-002 | Model has incremental information vs market at H-6h | BLOCKED_PENDING_PIT_FEATURES | HISTORICAL_PIT | COVERAGE_AUDITED | no model comparison executed | 245/245 odds coverage in 2026; no multi-season odds; feature availability not proven; 4 snapshots older than 24h | EXP-001 → H6, fixed before results | no claim |
| CLAIM-BR-MARKET-003 | Model has incremental information vs market at H-1h | BLOCKED_PENDING_PIT_FEATURES | HISTORICAL_PIT | COVERAGE_AUDITED | no model comparison executed | 245/245 odds coverage in 2026; no multi-season odds; feature availability not proven; 3 snapshots older than 24h | EXP-001 → H1, fixed before results | no claim |

Pilot evidence is `reports/exp001_data_pilot_2026-09-02.json`; population coverage and
identity evidence are in `reports/exp001_coverage_audit_2026-09-02.json` and
`reports/exp001_coverage_identity_assessment_2026-09-02.json`. They prove 2026 market
coverage and overlap identity, not same-cutoff model features or incrementality. No AFE
value exists until the experiment is pre-registered and run.
