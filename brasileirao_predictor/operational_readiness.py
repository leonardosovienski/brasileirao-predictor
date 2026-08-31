"""Local, secret-safe readiness audit for prospective A1 operation."""

import json
import os
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .identity import CanonicalTeamResolver


def _jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        json.loads(line)
        count += 1
    return count


def assess_operational_readiness(
    root: Path, env: Mapping[str, str] | None = None, *, now: datetime | None = None
) -> dict[str, Any]:
    environment = env if env is not None else os.environ
    checked_at = (now or datetime.now(UTC)).astimezone(UTC)
    data = root / "data"
    checks: dict[str, dict[str, Any]] = {}

    try:
        CanonicalTeamResolver(data / "team_aliases.json", data / "teams_brasileirao.json")
        checks["identity_catalog"] = {"status": "PASS"}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        checks["identity_catalog"] = {"status": "FAIL", "reason": str(exc)}

    operational_db = data / "odds_operational.db"
    required_tables = {"odds_event_versions", "odds_snapshot_facts"}
    present_tables: set[str] = set()
    if operational_db.exists():
        try:
            with sqlite3.connect(operational_db) as connection:
                query = "SELECT name FROM sqlite_master WHERE type='table'"
                present_tables = {row[0] for row in connection.execute(query)}
        except sqlite3.DatabaseError:
            present_tables = set()
    db_ready = required_tables <= present_tables
    checks["operational_database"] = {
        "status": "PASS" if db_ready else "BLOCKED",
        "exists": operational_db.exists(),
        "required_tables_present": db_ready,
    }
    key_configured = bool(str(environment.get("ODDSPAPI_KEY", "")).strip())
    checks["oddspapi_credential"] = {"status": "PASS" if key_configured else "BLOCKED", "configured": key_configured}

    try:
        snapshot_rows = sum(_jsonl_rows(path) for path in sorted((data / "odds_snapshots").glob("*.jsonl")))
        checks["a1_snapshots"] = {"status": "PASS" if snapshot_rows else "PENDING", "rows": snapshot_rows}
    except (OSError, json.JSONDecodeError) as exc:
        checks["a1_snapshots"] = {"status": "FAIL", "reason": str(exc)}

    verdict_path = data / "collector_metrics" / "gate_a1_verdict.json"
    formal_pass = False
    if verdict_path.exists():
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
            formal_pass = verdict.get("verdict") == "PASS"
        except json.JSONDecodeError:
            pass
    checks["gate_a1"] = {"status": "PASS" if formal_pass else "PENDING", "formal_pass": formal_pass}

    heartbeat_specs = {"collector": 45 * 60, "discovery": 8 * 24 * 3600, "metrics": 26 * 3600}
    for name, maximum_age in heartbeat_specs.items():
        heartbeat_path = data / "collector_state" / f"{name}_heartbeat.json"
        heartbeat_age: float | None = None
        heartbeat_status = None
        try:
            heartbeat = json.loads(heartbeat_path.read_text(encoding="utf-8"))
            heartbeat_at = datetime.fromisoformat(str(heartbeat["checked_at"]).replace("Z", "+00:00")).astimezone(UTC)
            heartbeat_age = (checked_at - heartbeat_at).total_seconds()
            heartbeat_status = heartbeat.get("status", "PASS")
            heartbeat_ok = 0 <= heartbeat_age <= maximum_age and heartbeat_status == "PASS"
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            heartbeat_ok = False
        checks[f"{name}_heartbeat"] = {
            "status": "PASS" if heartbeat_ok else "BLOCKED",
            "reported_status": heartbeat_status,
            "age_seconds": heartbeat_age,
            "maximum_age_seconds": maximum_age,
        }

    blockers = [name for name, check in checks.items() if check["status"] != "PASS"]
    return {
        "schema_version": "operational-readiness/v1",
        "status": "READY_FOR_HUMAN_REVIEW" if not blockers else "BLOCKED",
        "checks": checks,
        "blockers": blockers,
        "capital_enabled": False,
        "secrets_exposed": False,
    }
