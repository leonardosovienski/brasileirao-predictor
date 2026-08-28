"""Executa descoberta ou captura econômica do coletor A1 OddsPapi."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.a1_phase0 import Phase0Ledger, policy_fingerprint
from src.collector_a1 import (
    OddsPapiClient,
    QuotaGuard,
    SnapshotStore,
    TeamAliases,
    build_snapshots,
    parse_utc,
    quota_status,
    utc_text,
)

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "collector_state"
FIXTURES = STATE / "fixtures.json"
CAPTURES = STATE / "captures.json"
SNAPSHOTS = ROOT / "data" / "odds_snapshots"
METRICS = ROOT / "data" / "collector_metrics"
TARGET_MINUTES = (1440, 360, 60, 10)
PHASE0 = ROOT / "data" / "a1_phase0"
PHASE0_POLICY = ROOT / "contracts" / "a1-ou25-phase0-policy.json"
PHASE0_CODE = [
    ROOT / "src" / "a1_phase0.py",
    ROOT / "src" / "collector_a1.py",
    Path(__file__),
    ROOT / "schemas" / "odds_snapshot_v1.json",
    ROOT / "data" / "team_aliases.json",
]
QUOTA_STATE = STATE / "quota_guard.json"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_heartbeat(name: str, now: datetime, status: str) -> None:
    write_json(STATE / f"{name}_heartbeat.json", {"checked_at": utc_text(now), "status": status})


def discover(client: OddsPapiClient, now: datetime) -> dict[str, object]:
    policy = json.loads(PHASE0_POLICY.read_text(encoding="utf-8"))
    reserve = int(policy["quota_policy"]["minimum_monthly_reserve"])
    request_count, request_limit = quota_status(client.account())
    if request_limit - request_count <= reserve:
        raise RuntimeError("quota mensal na reserva; discovery bloqueado")
    fixtures = client.fixtures(utc_text(now), utc_text(now + timedelta(days=8)))
    eligible = [item for item in fixtures if item.get("fixtureId") and parse_utc(str(item["startTime"])) > now]
    payload = {
        "discovered_at": utc_text(now),
        "fixtures": eligible,
        "quota": {
            "request_count_before_discovery": request_count,
            "request_limit": request_limit,
            "reserve": reserve,
        },
    }
    write_json(FIXTURES, payload)
    write_heartbeat("discovery", now, "PASS")
    return {
        "mode": "discover",
        "fixtures": len(eligible),
        "requests": 1,
        "errors": 0,
        "quota_request_count_before": request_count,
        "quota_request_limit": request_limit,
        "quota_reserve": reserve,
    }


def due_label(kickoff: datetime, now: datetime, completed: set[str], *, mode: str = "economic") -> str | None:
    remaining = (kickoff - now).total_seconds() / 60
    if remaining <= 0:
        return None
    if mode == "full" and remaining <= 8 * 24 * 60:
        label = f"F-{now.strftime('%Y%m%dT%H')}"
        return None if label in completed else label
    for target in TARGET_MINUTES:
        label = f"T-{target}m"
        if label not in completed and remaining <= target:
            return label
    return None


def capture_complete(
    snapshots: list[dict[str, object]], quarantine: list[dict[str, object]], results: Sequence[str]
) -> bool:
    """Only close a capture window when every produced row was retained or already present."""
    return (
        bool(snapshots)
        and not quarantine
        and bool(results)
        and all(result in {"written", "duplicate"} for result in results)
    )


def append_phase0_observation(log: dict[str, object]) -> bool:
    """Attach operational counters only when an initialized fingerprint still matches."""
    fingerprint_path = PHASE0 / "fingerprint.json"
    if not fingerprint_path.exists():
        return False
    initialized = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    current = policy_fingerprint(PHASE0_POLICY, PHASE0_CODE)
    if initialized.get("fingerprint") != current["fingerprint"]:
        raise RuntimeError("A1 phase0 fingerprint changed; re-review and reinitialize before collection")
    ledger_path = PHASE0 / f"operational_observations-{str(current['fingerprint'])[:12]}.jsonl"
    Phase0Ledger(ledger_path, str(current["fingerprint"])).append(log)
    return True


def collect(client: OddsPapiClient, now: datetime, *, mode: str = "economic") -> dict[str, object]:
    if not FIXTURES.exists():
        raise RuntimeError("manifesto ausente; rode --discover primeiro")
    manifest = json.loads(FIXTURES.read_text(encoding="utf-8"))
    capture_state = json.loads(CAPTURES.read_text(encoding="utf-8")) if CAPTURES.exists() else {}
    aliases = TeamAliases(ROOT / "data" / "team_aliases.json")
    store = SnapshotStore(
        SNAPSHOTS,
        ROOT / "schemas" / "odds_snapshot_v1.json",
        operational_db=ROOT / "data" / "odds_operational.db",
    )
    for closed_day in SNAPSHOTS.glob("????-??-??.jsonl"):
        if closed_day.stem < now.date().isoformat() and not closed_day.with_suffix(".seal.json").exists():
            store.seal(closed_day)
    policy = json.loads(PHASE0_POLICY.read_text(encoding="utf-8"))
    quota_policy = policy["quota_policy"]
    guard = QuotaGuard(
        QUOTA_STATE,
        reserve=int(quota_policy["minimum_monthly_reserve"]),
        max_attempts=int(quota_policy["maximum_attempts_per_fixture_window"]),
        backoff_minutes=int(quota_policy["retry_backoff_minutes"]),
    )
    counters = {
        "snapshots": 0,
        "quarantined": 0,
        "conflicts": 0,
        "duplicates": 0,
        "errors": 0,
        "requests": 0,
        "quota_blocked": 0,
        "backoff_skips": 0,
    }
    account_count: int | None = None
    account_limit: int | None = None
    for fixture in manifest["fixtures"]:
        fixture_id = str(fixture["fixtureId"])
        completed = set(capture_state.get(fixture_id, []))
        label = due_label(parse_utc(str(fixture["startTime"])), now, completed, mode=mode)
        if label is None:
            continue
        try:
            if account_count is None or account_limit is None:
                account_count, account_limit = quota_status(client.account())
            allowed, reason = guard.allow(fixture_id, label, now, account_count, account_limit)
            if not allowed:
                counters["backoff_skips" if reason == "backoff" else "quota_blocked"] += 1
                continue
            guard.record(fixture_id, label, now)
            payload = client.odds(fixture_id)
            counters["requests"] += 1
            account_count += 1
            path = SNAPSHOTS / f"{now.date().isoformat()}.jsonl"
            previous = None
            if path.exists() and path.stat().st_size:
                previous = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])["hash_self"]
            snapshots, quarantine = build_snapshots(payload, aliases, now, previous)
            for item in quarantine:
                store.quarantine(str(item["reason"]), item)
                counters["quarantined"] += 1
            results = store.append_batch(snapshots)
            for result in results:
                counters["snapshots" if result == "written" else result + "s"] += 1
            if capture_complete(snapshots, quarantine, results):
                capture_state.setdefault(fixture_id, []).append(label)
        except Exception as exc:
            counters["errors"] += 1
            store.quarantine("source_or_parse_error", {"fixture_id": fixture_id, "error": type(exc).__name__})
    write_json(CAPTURES, capture_state)
    log = {
        "captured_at": utc_text(now),
        "mode": "full" if mode == "full" else "economic_budgeted",
        "quota_request_count": account_count,
        "quota_request_limit": account_limit,
        "quota_reserve": int(quota_policy["minimum_monthly_reserve"]),
        **counters,
    }
    METRICS.mkdir(parents=True, exist_ok=True)
    with (METRICS / "collector_daily_log.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(log, sort_keys=True) + "\n")
    append_phase0_observation(log)
    write_heartbeat("collector", now, "PASS" if counters["errors"] == 0 else "DEGRADED")
    return log


def main() -> int:
    parser = argparse.ArgumentParser(description="OddsPapi A1, SHADOW_ONLY")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--discover", action="store_true")
    group.add_argument("--collect", action="store_true")
    parser.add_argument("--mode", choices=("economic", "full"), default="economic")
    args = parser.parse_args()
    try:
        client = OddsPapiClient()
        result = (
            discover(client, datetime.now(UTC)) if args.discover else collect(client, datetime.now(UTC), mode=args.mode)
        )
    except Exception as exc:
        # RuntimeError messages created by OddsPapiClient are sanitized at the
        # source. Never print arbitrary transport exception text: requests can
        # embed the query string (and therefore the API key) in its message.
        detail = str(exc) if type(exc) is RuntimeError else None
        print(
            json.dumps(
                {"status": "FAILED_CLOSED", "error": type(exc).__name__, "safe_detail": detail},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"status": "SHADOW_ONLY", "homologated": False, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
