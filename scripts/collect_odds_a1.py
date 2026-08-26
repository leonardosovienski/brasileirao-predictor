"""Executa descoberta ou captura econômica do coletor A1 OddsPapi."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.collector_a1 import OddsPapiClient, SnapshotStore, TeamAliases, build_snapshots, parse_utc, utc_text

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "collector_state"
FIXTURES = STATE / "fixtures.json"
CAPTURES = STATE / "captures.json"
SNAPSHOTS = ROOT / "data" / "odds_snapshots"
METRICS = ROOT / "data" / "collector_metrics"
TARGET_MINUTES = (1440, 360, 60, 10)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def discover(client: OddsPapiClient, now: datetime) -> dict[str, object]:
    fixtures = client.fixtures(utc_text(now), utc_text(now + timedelta(days=8)))
    eligible = [item for item in fixtures if item.get("fixtureId") and parse_utc(str(item["startTime"])) > now]
    payload = {"discovered_at": utc_text(now), "fixtures": eligible}
    write_json(FIXTURES, payload)
    return {"mode": "discover", "fixtures": len(eligible), "requests": 1, "errors": 0}


def due_label(kickoff: datetime, now: datetime, completed: set[str]) -> str | None:
    remaining = (kickoff - now).total_seconds() / 60
    if remaining <= 0:
        return None
    for target in TARGET_MINUTES:
        label = f"T-{target}m"
        if label not in completed and remaining <= target:
            return label
    return None


def collect(client: OddsPapiClient, now: datetime) -> dict[str, object]:
    if not FIXTURES.exists():
        raise RuntimeError("manifesto ausente; rode --discover primeiro")
    manifest = json.loads(FIXTURES.read_text(encoding="utf-8"))
    capture_state = json.loads(CAPTURES.read_text(encoding="utf-8")) if CAPTURES.exists() else {}
    aliases = TeamAliases(ROOT / "data" / "team_aliases.json")
    store = SnapshotStore(SNAPSHOTS, ROOT / "schemas" / "odds_snapshot_v1.json")
    for closed_day in SNAPSHOTS.glob("????-??-??.jsonl"):
        if closed_day.stem < now.date().isoformat() and not closed_day.with_suffix(".seal.json").exists():
            store.seal(closed_day)
    counters = {"snapshots": 0, "quarantined": 0, "conflicts": 0, "duplicates": 0, "errors": 0, "requests": 0}
    for fixture in manifest["fixtures"]:
        fixture_id = str(fixture["fixtureId"])
        completed = set(capture_state.get(fixture_id, []))
        label = due_label(parse_utc(str(fixture["startTime"])), now, completed)
        if label is None:
            continue
        try:
            payload = client.odds(fixture_id)
            counters["requests"] += 1
            path = SNAPSHOTS / f"{now.date().isoformat()}.jsonl"
            previous = None
            if path.exists() and path.stat().st_size:
                previous = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])["hash_self"]
            snapshots, quarantine = build_snapshots(payload, aliases, now, previous)
            for item in quarantine:
                store.quarantine(str(item["reason"]), item)
                counters["quarantined"] += 1
            for item in snapshots:
                result = store.append(item)
                counters["snapshots" if result == "written" else result + "s"] += 1
            if snapshots and not quarantine:
                capture_state.setdefault(fixture_id, []).append(label)
        except Exception as exc:
            counters["errors"] += 1
            store.quarantine("source_or_parse_error", {"fixture_id": fixture_id, "error": type(exc).__name__})
    write_json(CAPTURES, capture_state)
    log = {"captured_at": utc_text(now), "mode": "economic", **counters}
    METRICS.mkdir(parents=True, exist_ok=True)
    with (METRICS / "collector_daily_log.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(log, sort_keys=True) + "\n")
    return log


def main() -> int:
    parser = argparse.ArgumentParser(description="OddsPapi A1, SHADOW_ONLY")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--discover", action="store_true")
    group.add_argument("--collect", action="store_true")
    args = parser.parse_args()
    try:
        client = OddsPapiClient()
        result = discover(client, datetime.now(UTC)) if args.discover else collect(client, datetime.now(UTC))
    except Exception as exc:
        print(json.dumps({"status": "FAILED_CLOSED", "error": type(exc).__name__}), file=sys.stderr)
        return 1
    print(json.dumps({"status": "SHADOW_ONLY", "homologated": False, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
