"""Acquire the frozen 30-event discovery sample once, with private raw bytes."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from collect_fixture_metadata import BASE, END, START, _get, _key, _unique_number, canonical

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "history_acquisition_manifest.json"
EXPECTED_SELECTION_SHA = "447a8ccd2e3cb895de23c4bbc68f27c9b95407ce47db250018f48536121a45db"
EXPECTED_UNIVERSE_SHA = "cf507b1968b47d27ae5a65878304d6c2c5f01d62e83ac150e2925b5e2b766eaf"


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def save_manifest(state: dict[str, Any]) -> None:
    temporary = MANIFEST.with_suffix(".tmp")
    temporary.write_bytes(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    temporary.replace(MANIFEST)


def validate_frozen_inputs() -> tuple[dict[str, Any], bytes, list[dict[str, Any]]]:
    plan_bytes = (ROOT / "price_discovery_plan.json").read_bytes()
    plan = json.loads(plan_bytes)
    selection_bytes = (ROOT / "fixture_selection_30.json").read_bytes()
    universe = json.loads((ROOT / "fixture_universe_jan_jun_2026.json").read_bytes())
    selection = json.loads(selection_bytes)
    if hashlib.sha256(selection_bytes).hexdigest() != EXPECTED_SELECTION_SHA:
        raise ValueError("selection_hash_mismatch")
    if plan["selection_file_sha256"] != EXPECTED_SELECTION_SHA:
        raise ValueError("plan_selection_hash_mismatch")
    if plan["universe_canonical_sha256"] != EXPECTED_UNIVERSE_SHA:
        raise ValueError("plan_universe_hash_mismatch")
    if hashlib.sha256(canonical(universe)).hexdigest() != EXPECTED_UNIVERSE_SHA:
        raise ValueError("universe_hash_mismatch")
    if plan["bookmakers"] != ["pinnacle", "bet365"] or plan["requests"]["historical_free_max"] != 30:
        raise ValueError("plan_request_scope_mismatch")
    if plan["requests"]["minimum_historical_cooldown_seconds"] != 5.1:
        raise ValueError("plan_cooldown_mismatch")
    if len(selection) != 30 or len({row["fixture_id"] for row in selection}) != 30:
        raise ValueError("selection_count_mismatch")
    for row in selection:
        kickoff = datetime.fromisoformat(row["kickoff_at"].replace("Z", "+00:00"))
        if kickoff.tzinfo is None or not START <= kickoff < END:
            raise ValueError("fixture_outside_authorized_period")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", row["fixture_id"]):
            raise ValueError("unsafe_fixture_id")
    return plan, plan_bytes, selection


def main() -> int:
    if MANIFEST.exists():
        print(json.dumps({"status": "STOP_EXISTING_ACQUISITION_MANIFEST", "no_request_sent": True}))
        return 2
    state: dict[str, Any] = {"schema": "price-discovery-history-acquisition/1", "records": []}
    try:
        plan, plan_bytes, selection = validate_frozen_inputs()
        key = _key()
        raw_dir = ROOT / "raw"
        raw_dir.mkdir(exist_ok=True)
        if any(raw_dir.iterdir()):
            raise ValueError("raw_directory_not_empty")
        state.update(
            {
                "status": "RUNNING",
                "started_at": utc_now(),
                "plan_id": plan["id"],
                "plan_file_sha256_before_first_request": hashlib.sha256(plan_bytes).hexdigest(),
                "selection_file_sha256": EXPECTED_SELECTION_SHA,
                "universe_canonical_sha256": EXPECTED_UNIVERSE_SHA,
                "bookmakers": plan["bookmakers"],
                "max_requests": 30,
                "cooldown_seconds": 5.1,
                "raw_private": True,
                "automatic_retries": False,
                "billable_endpoints_called": [],
            }
        )
        save_manifest(state)  # Durable plan fingerprint before any historical request.
        last_start = None
        for ordinal, fixture in enumerate(selection, start=1):
            if (
                hashlib.sha256((ROOT / "price_discovery_plan.json").read_bytes()).hexdigest()
                != state["plan_file_sha256_before_first_request"]
            ):
                raise ValueError("plan_changed_during_acquisition")
            if last_start is not None:
                time.sleep(max(0.0, 5.1 - (time.monotonic() - last_start)))
            row: dict[str, Any] = {
                "ordinal": ordinal,
                "fixture_id": fixture["fixture_id"],
                "kickoff_at": fixture["kickoff_at"],
                "attempted_at": utc_now(),
                "status": "ATTEMPTED",
            }
            state["records"].append(row)
            save_manifest(state)  # An interrupted request is never silently retried.
            last_start = time.monotonic()
            try:
                response = requests.get(
                    f"{BASE}/historical-odds",
                    params={"fixtureId": fixture["fixture_id"], "bookmakers": "pinnacle,bet365", "apiKey": key},
                    timeout=60,
                )
                row["http_status"] = response.status_code
                if response.status_code == 200:
                    raw_bytes = response.content
                    if key.encode() in raw_bytes:
                        row["status"] = "REJECT_CREDENTIAL_IN_BODY"
                    else:
                        payload = response.json()
                        if not isinstance(payload, dict) or payload.get("fixtureId") != fixture["fixture_id"]:
                            row["status"] = "REJECT_FIXTURE_IDENTITY"
                        else:
                            destination = raw_dir / f"{fixture['fixture_id']}.json"
                            destination.write_bytes(raw_bytes)
                            row.update(
                                {
                                    "status": "SAVED_PRIVATE_RAW",
                                    "file": f"raw/{fixture['fixture_id']}.json",
                                    "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                                    "bytes": len(raw_bytes),
                                }
                            )
                        del payload
                else:
                    row["status"] = "HTTP_FAILURE_NO_RETRY"
            except Exception as exc:
                row["status"] = "EXCEPTION_NO_RETRY"
                row["error_class"] = type(exc).__name__
            row["finished_at"] = utc_now()
            save_manifest(state)
            if ordinal % 5 == 0:
                print(
                    json.dumps(
                        {
                            "progress": ordinal,
                            "total": 30,
                            "saved": sum(r["status"] == "SAVED_PRIVATE_RAW" for r in state["records"]),
                            "failures": sum(r["status"] != "SAVED_PRIVATE_RAW" for r in state["records"]),
                        }
                    ),
                    flush=True,
                )
        try:
            status, account = _get("account", key)
            state["account_after_http_status"] = status
            if status == 200:
                state["quota_after"] = {
                    "request_count": _unique_number(account, "request_count"),
                    "request_limit": _unique_number(account, "request_limit"),
                }
            del account
        except Exception as exc:
            state["account_after_error_class"] = type(exc).__name__
        del key
        state["finished_at"] = utc_now()
        state["status"] = "COMPLETE_NO_RETRIES"
        state["saved_count"] = sum(r["status"] == "SAVED_PRIVATE_RAW" for r in state["records"])
        state["failure_count"] = 30 - state["saved_count"]
        state["raw_hash_manifest_sha256"] = hashlib.sha256(
            canonical([{k: row[k] for k in ("fixture_id", "status", "sha256") if k in row} for row in state["records"]])
        ).hexdigest()
        save_manifest(state)
        print(json.dumps({k: value for k, value in state.items() if k != "records"}), flush=True)
        return 0
    except Exception as exc:
        state.update({"status": "FAIL_CLOSED", "error_class": type(exc).__name__, "finished_at": utc_now()})
        save_manifest(state)
        print(json.dumps({"status": "FAIL_CLOSED", "error_class": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
