"""Local, secret-safe readiness audit for prospective A1 operation."""

import json
import os
from collections.abc import Mapping
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


def assess_operational_readiness(root: Path, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    environment = env if env is not None else os.environ
    data = root / "data"
    checks: dict[str, dict[str, Any]] = {}

    try:
        CanonicalTeamResolver(data / "team_aliases.json", data / "teams_brasileirao.json")
        checks["identity_catalog"] = {"status": "PASS"}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        checks["identity_catalog"] = {"status": "FAIL", "reason": str(exc)}

    db_exists = (data / "matches.db").exists()
    checks["operational_database"] = {"status": "PASS" if db_exists else "BLOCKED", "exists": db_exists}
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

    blockers = [name for name, check in checks.items() if check["status"] != "PASS"]
    return {
        "schema_version": "operational-readiness/v1",
        "status": "READY_FOR_HUMAN_REVIEW" if not blockers else "BLOCKED",
        "checks": checks,
        "blockers": blockers,
        "capital_enabled": False,
        "secrets_exposed": False,
    }
