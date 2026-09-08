"""Acquire each frozen historical ID once; no billable endpoints or raw output."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "selection_reanalysis/price_history"))
from collect_fixture_metadata import BASE, _get, _key, _unique_number

PLAN_SHA = "c02666646fdbe39dee9ab0b614a2077d8d3dca073a2b9ff5c88af4475990d9fd"
SELECTION_SHA = "5da96f38349b1b7535cf11109e84071dc1ae0b351b0cf986c4d3b5822c7cca6a"
MANIFEST = ROOT / "acquisition_manifest.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def save(state):
    temporary = MANIFEST.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(MANIFEST)


def quota(key):
    status, account = _get("account", key)
    if status != 200:
        raise ValueError("account_unavailable")
    result = {"request_count": _unique_number(account, "request_count"),
              "request_limit": _unique_number(account, "request_limit")}
    if not 0 <= result["request_count"] < result["request_limit"]:
        raise ValueError("invalid_or_exhausted_quota")
    return result


def main():
    if MANIFEST.exists():
        print(json.dumps({"status": "STOP_EXISTING_MANIFEST", "no_request_sent": True}))
        return 2
    state = {"status": "PRECHECK", "started_at": now(), "records": [], "max_requests": 51,
             "plan_file_sha256_before_first_request": PLAN_SHA,
             "selection_file_sha256": SELECTION_SHA, "billable_endpoints_called": [],
             "raw_private": True, "automatic_retries": False}
    try:
        if sha(ROOT / "plan.json") != PLAN_SHA or sha(ROOT / "selection.json") != SELECTION_SHA:
            raise ValueError("frozen_hash_mismatch")
        plan = json.loads((ROOT / "plan.json").read_text(encoding="utf-8"))
        selection = json.loads((ROOT / "selection.json").read_text(encoding="utf-8"))
        if plan["requests"]["bookmakers"] != ["pinnacle"] or len(selection) != 51:
            raise ValueError("unexpected_scope")
        if len({r["fixture_id"] for r in selection}) != 51:
            raise ValueError("duplicate_fixture")
        if any(not re.fullmatch(r"[A-Za-z0-9_-]+", r["fixture_id"]) for r in selection):
            raise ValueError("unsafe_fixture_id")
        raw_dir = ROOT / "raw"
        raw_dir.mkdir(exist_ok=True)
        if any(raw_dir.iterdir()):
            raise ValueError("nonempty_raw_directory")
        save(state)
        key = _key()
        state["quota_before"] = quota(key)
        if state["quota_before"]["request_limit"] - state["quota_before"]["request_count"] < 20:
            raise ValueError("reserve_not_available")
        state["status"] = "RUNNING"
        save(state)
        consecutive_429 = 0
        for ordinal, fixture in enumerate(selection, 1):
            if sha(ROOT / "plan.json") != PLAN_SHA or sha(ROOT / "selection.json") != SELECTION_SHA:
                raise ValueError("frozen_inputs_changed")
            row = {"ordinal": ordinal, "fixture_id": fixture["fixture_id"],
                   "kickoff_at": fixture["kickoff_at"], "attempted_at": now(), "status": "ATTEMPTED"}
            state["records"].append(row)
            save(state)
            try:
                response = requests.get(f"{BASE}/historical-odds",
                                        params={"fixtureId": fixture["fixture_id"], "bookmakers": "pinnacle", "apiKey": key},
                                        timeout=60)
                row["http_status"] = response.status_code
                if response.status_code == 200:
                    raw = response.content
                    if key.encode() in raw:
                        raise ValueError("credential_in_body")
                    payload = response.json()
                    if not isinstance(payload, dict) or payload.get("fixtureId") != fixture["fixture_id"]:
                        raise ValueError("fixture_identity_mismatch")
                    destination = raw_dir / (fixture["fixture_id"] + ".json")
                    destination.write_bytes(raw)
                    row.update(status="SAVED_PRIVATE_RAW", file="raw/" + destination.name,
                               sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
                    del payload, raw
                else:
                    row["status"] = "HTTP_FAILURE_NO_RETRY"
            except Exception as exc:
                row["status"] = "EXCEPTION_NO_RETRY"
                row["error_class"] = type(exc).__name__
            row["finished_at"] = now()
            consecutive_429 = consecutive_429 + 1 if row.get("http_status") == 429 else 0
            save(state)
            if ordinal % 5 == 0 or row.get("http_status") != 200:
                print(json.dumps({"attempted": ordinal, "selected": 51,
                                  "saved": sum(r["status"] == "SAVED_PRIVATE_RAW" for r in state["records"]),
                                  "last_http_status": row.get("http_status")}), flush=True)
            if row.get("http_status") in (401, 402, 403) or consecutive_429 >= 3:
                state["status"] = "STOP_PROVIDER_ERROR_NO_RETRY"
                break
            if ordinal < 51:
                time.sleep(30 if row.get("http_status") == 429 else 7)
        if state["status"] == "RUNNING":
            state["status"] = "COMPLETE_NO_RETRIES"
        try:
            state["quota_after"] = quota(key)
        except Exception as exc:
            state["account_after_error_class"] = type(exc).__name__
        del key
        state["finished_at"] = now()
        state["saved_count"] = sum(r["status"] == "SAVED_PRIVATE_RAW" for r in state["records"])
        state["attempted_count"] = len(state["records"])
        state["unattempted_count"] = 51 - len(state["records"])
        save(state)
        print(json.dumps({k: v for k, v in state.items() if k != "records"}), flush=True)
        return 0
    except Exception as exc:
        state.update(status="FAIL_CLOSED", error_class=type(exc).__name__, finished_at=now())
        save(state)
        print(json.dumps({"status": "FAIL_CLOSED", "error_class": type(exc).__name__}), flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
