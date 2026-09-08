"""Read-only EXP-001 pilot: three historical Série A fixtures, Pinnacle 1X2.

Only the compact audit summary is persisted; raw provider data and credentials are not.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

BASE = "https://api.oddspapi.io/v4"
TOURNAMENT = 325
OUTCOMES = {"101": "home_odds", "102": "draw_odds", "103": "away_odds"}


def _get(path: str, key: str, **params: object) -> Any:
    response = requests.get(f"{BASE}/{path}", params={**params, "apiKey": key}, timeout=60)
    if response.status_code != 200:
        detail = response.text[:200].replace(key, "[REDACTED]")
        raise RuntimeError(f"provider HTTP {response.status_code}: {detail}")
    return response.json()


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _latest_at_cutoff(book: dict[str, Any], cutoff: datetime) -> dict[str, Any] | None:
    outcomes = book.get("markets", {}).get("101", {}).get("outcomes", {})
    selected: dict[str, Any] = {}
    timestamps: list[datetime] = []
    for outcome_id, label in OUTCOMES.items():
        timeline = outcomes.get(outcome_id, {}).get("players", {}).get("0", [])
        eligible = [row for row in timeline if _at(row["createdAt"]) <= cutoff and row.get("active", True)]
        if not eligible:
            return None
        latest = max(eligible, key=lambda row: _at(row["createdAt"]))
        selected[label] = latest["price"]
        timestamps.append(_at(latest["createdAt"]))
    returned = min(timestamps)
    return {
        **selected,
        "returned_snapshot_timestamp": returned.isoformat().replace("+00:00", "Z"),
        "snapshot_age_minutes": round((cutoff - returned).total_seconds() / 60, 3),
    }


def run(key: str) -> dict[str, Any]:
    fixtures = _get("fixtures", key, tournamentId=TOURNAMENT, statusId=2, **{"from": "2026-04-01", "to": "2026-08-31"})
    eligible = sorted(
        (row for row in fixtures if row.get("fixtureId") and row.get("statusName") == "Finished"),
        key=lambda row: row["startTime"],
    )
    if len(eligible) < 3:
        raise RuntimeError("fewer than three finished Série A fixtures")
    chosen = [eligible[0], eligible[len(eligible) // 2], eligible[-1]]
    rows: list[dict[str, Any]] = []
    for index, fixture in enumerate(chosen):
        if index:
            time.sleep(5.1)  # documented endpoint cooldown
        history = _get("historical-odds", key, fixtureId=fixture["fixtureId"], bookmakers="pinnacle")
        book = history.get("bookmakers", {}).get("pinnacle")
        kickoff = _at(fixture["startTime"])
        for hours in (24, 6, 1):
            cutoff = kickoff - timedelta(hours=hours)
            snapshot = _latest_at_cutoff(book, cutoff) if isinstance(book, dict) else None
            rows.append(
                {
                    "match_id": fixture["fixtureId"],
                    "match": f"{fixture.get('participant1Name')} x {fixture.get('participant2Name')}",
                    "kickoff": kickoff.isoformat().replace("+00:00", "Z"),
                    "requested_cutoff": f"H-{hours}h",
                    "bookmaker": "pinnacle",
                    "market": "1X2",
                    "missing": snapshot is None,
                    **(snapshot or {}),
                    "credits_or_query_cost": "free historical endpoint; 1 request per fixture",
                }
            )
    return {
        "schema_version": "exp001-data-pilot/1.0",
        "executed_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "provider": "OddsPapi v4",
        "requests_used": 4,
        "raw_data_persisted": False,
        "license_note": "research summary only; provider data must not be resold/repackaged/redistributed",
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    key = os.environ.get("ODDSPAPI_KEY", "").strip()
    if not key:
        parser.error("ODDSPAPI_KEY is required")
    result = run(key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "rows": len(result["rows"]), "requests_used": 4}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
