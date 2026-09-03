"""Audit every available 2026 Série A fixture for Pinnacle 1X2 cutoff coverage.

The provider's raw timelines are never persisted. The output is a resumable compact
audit containing only fixture identity, cutoff availability, selected prices and age.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

from brasileirao_scripts.exp001_data_pilot import TOURNAMENT, _at, _get, _latest_at_cutoff


def _write(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _summary(rows: list[dict[str, Any]], fixture_count: int) -> dict[str, Any]:
    horizons: dict[str, Any] = {}
    for horizon in ("H-24h", "H-6h", "H-1h"):
        selected = [row for row in rows if row["requested_cutoff"] == horizon]
        covered = [row for row in selected if not row["missing"]]
        ages = [float(row["snapshot_age_minutes"]) for row in covered]
        horizons[horizon] = {
            "fixtures": fixture_count,
            "covered": len(covered),
            "missing": fixture_count - len(covered),
            "coverage": len(covered) / fixture_count if fixture_count else 0.0,
            "median_snapshot_age_minutes": median(ages) if ages else None,
            "max_snapshot_age_minutes": max(ages) if ages else None,
        }
    return horizons


def run(key: str, output: Path, *, cooldown: float = 5.1) -> dict[str, Any]:
    fixtures = _get(
        "fixtures",
        key,
        tournamentId=TOURNAMENT,
        statusId=2,
        **{"from": "2026-01-01", "to": "2026-09-02"},
    )
    fixtures = sorted(
        (row for row in fixtures if row.get("fixtureId") and row.get("statusName") == "Finished"),
        key=lambda row: row["startTime"],
    )
    document: dict[str, Any] = {
        "schema_version": "exp001-coverage-audit/1.0",
        "started_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "provider": "OddsPapi v4",
        "period": ["2026-01-01", "2026-09-02"],
        "bookmaker": "pinnacle",
        "market": "1X2",
        "raw_data_persisted": False,
        "fixture_count": len(fixtures),
        "requests_used": 1,
        "rows": [],
        "errors": [],
    }
    if output.is_file():
        previous = json.loads(output.read_text(encoding="utf-8"))
        if previous.get("schema_version") == document["schema_version"]:
            document["rows"] = previous.get("rows", [])
            document["errors"] = previous.get("errors", [])
            document["started_at"] = previous.get("started_at", document["started_at"])
            document["requests_used"] = int(previous.get("requests_used", 1)) + 1
    completed = {str(row["match_id"]) for row in document["rows"]}
    pending = [fixture for fixture in fixtures if str(fixture["fixtureId"]) not in completed]
    for index, fixture in enumerate(pending):
        if index or completed:
            time.sleep(cooldown)
        fixture_id = str(fixture["fixtureId"])
        try:
            document["requests_used"] += 1
            history = _get("historical-odds", key, fixtureId=fixture_id, bookmakers="pinnacle")
            book = history.get("bookmakers", {}).get("pinnacle")
            kickoff = _at(fixture["startTime"])
            for hours in (24, 6, 1):
                cutoff = kickoff - timedelta(hours=hours)
                snapshot = _latest_at_cutoff(book, cutoff) if isinstance(book, dict) else None
                document["rows"].append(
                    {
                        "match_id": fixture_id,
                        "home": fixture.get("participant1Name"),
                        "away": fixture.get("participant2Name"),
                        "kickoff": kickoff.isoformat().replace("+00:00", "Z"),
                        "requested_cutoff": f"H-{hours}h",
                        "missing": snapshot is None,
                        **(snapshot or {}),
                    }
                )
        except Exception as exc:  # provider failures belong in the coverage denominator
            document["errors"].append({"match_id": fixture_id, "error": str(exc)[:300]})
        document["summary"] = _summary(document["rows"], len(fixtures))
        document["completed_fixtures"] = len({str(row["match_id"]) for row in document["rows"]})
        completed_now = {str(row["match_id"]) for row in document["rows"]}
        document["errors"] = [error for error in document["errors"] if str(error["match_id"]) not in completed_now]
        document["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        _write(output, document)
        print(f"{document['completed_fixtures']}/{len(fixtures)}", flush=True)
    document["completed_at"] = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    document["summary"] = _summary(document["rows"], len(fixtures))
    _write(output, document)
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    key = os.environ.get("ODDSPAPI_KEY", "").strip()
    if not key:
        parser.error("ODDSPAPI_KEY is required")
    result = run(key, args.output)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
