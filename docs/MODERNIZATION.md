# Modernization and migration

> **Versions updated 2026-09-06** to `predictor_core` 3.2.0 / `predictor_ops` 4.1.0.
> This file describes architecture in the present tense and carried 2.3.0/3.1.0
> — two major versions stale — until the adversarial audit closeout. The
> canonical current state is the first checkpoint of `HANDOFF.md`.

## Runtime architecture

The domain remains scientifically isolated from operations. The installable Python package owns the CLI and scientific code; `predictor_core` 3.2.x supplies shared contracts and measurement primitives; `predictor_ops` 4.1.x supplies the portable scheduler/runner. Redis is ephemeral coordination only. Sports and market SQLite files have different required absolute paths and are never merged. PostgreSQL and Object Storage are future adapters, not implicit migrations.

The runtime uses `brasileirao.redis/2`, documented in `contracts/redis-protocol-v2.md` and its v2 schemas. Invocations also carry a registered `state_version`; calculation and publication require the current immutable request, lineup snapshot and lease owner. Requests live for 60 seconds and processing leases for five seconds. Pending and ready indexes recover missed notifications; the accepted signal outbox and lineup inbox use Redis Streams. Worker health requires both active loops from the same session. Fair odds retain their original short validity. The v1 schema is historical and cannot be sent to the v2 runtime. Redis AOF uses `everysec`; missing or stale economic state prevents publication.

## Script inventory

- Runtime: `prever.py`, `sombra.py`, `sombra_diaria.py`, `sombra_diaria_payload.py`, collectors, settlement, `odds_shop.py`, `record_*`, `sync_matches_from_sofascore.py`.
- Research: backtests, calibration, diagnostics, H4 sweeps, simulation, mechanism and VORP studies.
- Migration/bootstrap: `seed_test_fixtures.py`, `init_compose_data.py`, `bootstrap_calibration_window.py`, `ingest_api_football_history.py`.
- Legacy/platform-specific: `install_closing_snapshot_task.ps1`. It is retained for compatibility; new scheduling uses `predictor_ops` and is portable.

No legacy script or data was deleted. Only the obsolete `vendor/predictor_core` copy and duplicate requirements manifests were removed after the suite passed against installed wheels.

## Data migration safety

No production database is changed by this modernization. To adopt the new runtime, back up and verify `matches.db`, configure distinct absolute `SPORTS_DB_PATH` and `MARKET_DB_PATH`, start Compose against copies, compare counts and hashes, and only then switch the scheduler. PostgreSQL/Object Storage preparation is intentionally interface-only until schemas, reconciliation, restore testing, and operator authorization exist.

## Distribution

`predictor_core` 3.2.0 and `predictor_ops` 4.1.0 are consumed from their canonical GitHub Release asset URLs (`[tool.uv.sources]` in `pyproject.toml`, hash-pinned in `uv.lock` and `constraints/shared-wheels.sha256`). The domain distribution requires Core >=3.2 because strict DSR and its exception type are not present in 3.1. Container builds retain locked exports, hash verification and installation of the domain wheel without resolving dependencies again. CI runs the integration checks; consult the receipt for the exact commit before claiming a run passed. Vendoring or copying their implementation back into this domain remains prohibited.
