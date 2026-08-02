# Modernization and migration

## Runtime architecture

The domain remains scientifically isolated from operations. The installable Python package owns the CLI and scientific code; `predictor_core` 2.1.x supplies shared contracts and measurement primitives; `predictor_ops` 2.0.x supplies the portable scheduler/runner. Redis is ephemeral coordination only. Sports and market SQLite files have different required absolute paths and are never merged. PostgreSQL and Object Storage are future adapters, not implicit migrations.

The Redis protocol is `brasileirao.redis/1`, defined in `contracts/redis-protocol-v1.schema.json`. Every invocation carries `job_id`, `run_id`, `match_id`, and `idempotency_key`. Claims expire after 60 seconds; fair odds expire after 5 seconds. Replays of a claimed key are ignored. Redis AOF uses `everysec`; consumers reconnect and fail closed when ephemeral fair odds are absent.

## Script inventory

- Runtime: `prever.py`, `sombra.py`, `sombra_diaria.py`, `sombra_diaria_payload.py`, collectors, settlement, `odds_shop.py`, `record_*`, `sync_matches_from_sofascore.py`.
- Research: backtests, calibration, diagnostics, H4 sweeps, simulation, mechanism and VORP studies.
- Migration/bootstrap: `seed_test_fixtures.py`, `init_compose_data.py`, `bootstrap_calibration_window.py`, `ingest_api_football_history.py`.
- Legacy/platform-specific: `install_closing_snapshot_task.ps1`. It is retained for compatibility; new scheduling uses `predictor_ops` and is portable.

No legacy script or data was deleted. Only the obsolete `vendor/predictor_core` copy and duplicate requirements manifests were removed after the suite passed against installed wheels.

## Data migration safety

No production database is changed by this modernization. To adopt the new runtime, back up and verify `matches.db`, configure distinct absolute `SPORTS_DB_PATH` and `MARKET_DB_PATH`, start Compose against copies, compare counts and hashes, and only then switch the scheduler. PostgreSQL/Object Storage preparation is intentionally interface-only until schemas, reconciliation, restore testing, and operator authorization exist.

## Distribution blocker

`predictor_core` 2.1.0 and the pipe-cleanup release `predictor_ops` 2.0.1 were validated from wheels outside their source checkouts. They are not available from public PyPI, and the public repository commits do not yet expose build metadata. CI/container installation therefore requires the canonical wheels to be published to an authenticated package index or stable release URLs. Vendoring or copying their implementation back into this domain is prohibited.
