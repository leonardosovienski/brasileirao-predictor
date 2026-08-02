"""Fetch and append sanitized bookmaker stability observations; never emits picks."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from predictor_core.data.contracts import DataUnavailableError

from src.data.bookmaker_stability import append_smoke, bookmaker_type, stability_report
from src.data.the_odds_api_provider import ADAPTER_VERSION, SOURCE, TheOddsApiProvider

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "odds_source_smokes.jsonl"


def collect(rows: list[dict], region: str, executed_at: str) -> list[dict]:
    per_book = defaultdict(list)
    for row in rows:
        per_book[row["bookmaker"]].append(row)
    output = []
    for key, quotes in sorted(per_book.items()):
        updates = [datetime.fromisoformat(q["odds_captured_at"]) for q in quotes]
        now = datetime.fromisoformat(executed_at)
        output.append(
            {
                "executed_at": executed_at,
                "region": region,
                "bookmaker_key": key,
                "bookmaker_type": bookmaker_type(key),
                "events_seen": len({q["source_event_id"] for q in rows}),
                "events_with_totals": len({q["source_event_id"] for q in quotes}),
                "valid_quotes": len(quotes),
                "rejected_quotes": 0,
                "earliest_last_update": min(updates).isoformat(timespec="seconds"),
                "latest_last_update": max(updates).isoformat(timespec="seconds"),
                "update_lag_seconds": max(0.0, (now - max(updates)).total_seconds()),
                "adapter_version": ADAPTER_VERSION,
                "payload_hash": quotes[0]["raw_payload_hash"],
                "source": SOURCE,
            }
        )
    return output


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="eu")
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    if args.report:
        print(json.dumps(stability_report(args.ledger), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    try:
        rows = TheOddsApiProvider(regions=args.region).fetch_ou25()
    except DataUnavailableError as exc:
        print(json.dumps({"status": "BLOCKED_BY_PROVIDER_CONFIGURATION", "message": str(exc)}))
        return 2
    executed = datetime.now(UTC).isoformat(timespec="seconds")
    append_smoke(args.ledger, collect(rows, args.region, executed))
    print(
        json.dumps(
            {
                "status": "SMOKE_RECORDED",
                "bookmakers": len({r["bookmaker"] for r in rows}),
                "quotes": len(rows),
                "picks_persisted": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
