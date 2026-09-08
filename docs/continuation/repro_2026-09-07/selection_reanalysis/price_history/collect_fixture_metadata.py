"""One-shot Jan-Jun 2026 metadata discovery; never requests odds or outcomes."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent
BASE = "https://api.oddspapi.io/v4"
START = datetime(2026, 1, 1, tzinfo=UTC)
END = datetime(2026, 7, 1, tzinfo=UTC)
PARAMS = {"tournamentId": 325, "statusId": 2, "from": "2026-01-01", "to": "2026-06-30"}
MARKER = ROOT / "fixture_metadata_request_attempt.json"


def canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def save(name: str, data: Any) -> None:
    (ROOT / name).write_bytes(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")


def _key() -> str:
    value = os.environ.get("ODDSPAPI_KEY", "").strip()
    if not value:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
            value = str(winreg.QueryValueEx(handle, "ODDSPAPI_KEY")[0]).strip()
    if not value:
        raise RuntimeError("key_absent")
    return value


def _unique_number(payload: Any, field: str) -> int:
    values = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            candidate = value.get(field)
            if isinstance(candidate, int) and not isinstance(candidate, bool):
                values.add(candidate)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    if len(values) != 1:
        raise ValueError("ambiguous_quota")
    return values.pop()


def _get(endpoint: str, api_key: str, params: dict[str, Any] | None = None) -> tuple[int, Any]:
    # No retries, request logging, response URL printing, or exception text.
    response = requests.get(f"{BASE}/{endpoint}", params={**(params or {}), "apiKey": api_key}, timeout=60)
    status = response.status_code
    if status != 200:
        return status, None
    return status, response.json()


def filter_metadata(payload: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not isinstance(payload, list):
        raise TypeError("fixture_payload_not_list")
    unique: dict[str, dict[str, Any]] = {}
    excluded = {"invalid": 0, "out_of_window": 0, "unfinished": 0, "duplicate_identical": 0}
    for item in payload:
        if not isinstance(item, dict) or not item.get("fixtureId") or not item.get("startTime"):
            excluded["invalid"] += 1
            continue
        try:
            kickoff = datetime.fromisoformat(str(item["startTime"]).replace("Z", "+00:00"))
            if kickoff.tzinfo is None:
                raise ValueError("naive_time")
            kickoff = kickoff.astimezone(UTC)
        except (ValueError, TypeError):
            excluded["invalid"] += 1
            continue
        if not START <= kickoff < END:
            excluded["out_of_window"] += 1
            continue
        if item.get("statusName") != "Finished" and item.get("statusId") != 2:
            excluded["unfinished"] += 1
            continue
        row = {
            "fixture_id": str(item["fixtureId"]),
            "kickoff_at": kickoff.isoformat().replace("+00:00", "Z"),
            "home": item.get("participant1Name"),
            "away": item.get("participant2Name"),
            "status": "Finished",
        }
        previous = unique.get(row["fixture_id"])
        if previous is not None:
            if previous != row:
                raise ValueError("duplicate_fixture_identity_conflict")
            excluded["duplicate_identical"] += 1
        unique[row["fixture_id"]] = row
    return sorted(unique.values(), key=lambda row: (row["kickoff_at"], row["fixture_id"])), excluded


def select_equidistant(rows: list[dict[str, Any]], n: int = 30) -> tuple[list[dict[str, Any]], list[int]]:
    if len(rows) < n:
        raise ValueError("insufficient_metadata_universe")
    indices = [(i * (len(rows) - 1)) // (n - 1) for i in range(n)]
    if len(set(indices)) != n:
        raise ValueError("selection_indices_not_unique")
    return [rows[i] for i in indices], indices


def main() -> int:
    state: dict[str, Any] = {"schema": "price-discovery-fixture-metadata/1", "odds_requested": False}
    if MARKER.exists():
        print(json.dumps({**state, "status": "STOP_EXISTING_BILLABLE_ATTEMPT"}))
        return 2
    try:
        key = _key()
        status, account = _get("account", key)
        if status != 200:
            print(json.dumps({**state, "status": "ACCOUNT_HTTP_FAILURE", "http_status": status}))
            return 2
        count = _unique_number(account, "request_count")
        limit = _unique_number(account, "request_limit")
        del account
        if count < 0 or limit < 1 or count > limit:
            raise ValueError("invalid_quota")
        state["quota_before"] = {"request_count": count, "request_limit": limit, "reserve": 20}
        if limit - count - 1 < 20:
            save("fixture_metadata_status.json", {**state, "status": "STOP_RESERVE"})
            print(json.dumps({**state, "status": "STOP_RESERVE"}))
            return 2
        state["retrieved_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        save(
            MARKER.name,
            {
                "attempted_at": state["retrieved_at"],
                "endpoint": "fixtures",
                "parameters": PARAMS,
                "max_billable_requests": 1,
            },
        )
        status, payload = _get("fixtures", key, PARAMS)
        del key
        state["fixture_http_status"] = status
        if status != 200:
            save("fixture_metadata_status.json", {**state, "status": "FIXTURE_HTTP_FAILURE"})
            print(json.dumps({**state, "status": "FIXTURE_HTTP_FAILURE"}))
            return 2
        rows, exclusions = filter_metadata(payload)
        del payload  # Unselected provider fields, including any score, are never persisted.
        selected, indices = select_equidistant(rows)
        save("fixture_universe_jan_jun_2026.json", rows)
        save("fixture_selection_30.json", selected)
        state.update(
            {
                "status": "METADATA_READY_NO_ODDS_OPENED",
                "parameters": PARAMS,
                "eligible_count": len(rows),
                "exclusions": exclusions,
                "selection_count": len(selected),
                "selection_rule": "sorted(kickoff_at,fixture_id), indices floor(i*(N-1)/29), i=0..29",
                "selection_indices": indices,
                "universe_canonical_sha256": hashlib.sha256(canonical(rows)).hexdigest(),
                "selection_canonical_sha256": hashlib.sha256(canonical(selected)).hexdigest(),
                "universe_file_sha256": hashlib.sha256(
                    (ROOT / "fixture_universe_jan_jun_2026.json").read_bytes()
                ).hexdigest(),
                "selection_file_sha256": hashlib.sha256((ROOT / "fixture_selection_30.json").read_bytes()).hexdigest(),
                "first_kickoff": rows[0]["kickoff_at"],
                "last_kickoff": rows[-1]["kickoff_at"],
                "bookmakers_proposed": ["pinnacle", "bet365"],
                "slug_source": "https://oddspapi.io/us/docs/get-historical-odds",
            }
        )
        save("fixture_metadata_status.json", state)
        print(json.dumps(state, ensure_ascii=False))
        return 0
    except Exception as exc:
        safe = {**state, "status": "FAIL_CLOSED", "error_class": type(exc).__name__}
        save("fixture_metadata_status.json", safe)
        print(json.dumps(safe))
        return 2


if __name__ == "__main__":
    sys.exit(main())
