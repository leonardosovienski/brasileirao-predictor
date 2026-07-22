"""Read-only, sanitized readiness check for The Odds API prospective source."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
from predictor_core.data.contracts import DataUnavailableError
from src.data.the_odds_api_provider import ADAPTER_VERSION, SOURCE, SPORT, TheOddsApiProvider


def report(rows: list[dict], region: str) -> dict:
    events = defaultdict(list)
    for row in rows: events[row["source_event_id"]].append(row)
    books = Counter(row["bookmaker"] for row in rows)
    return {"schema_version": "odds-source-smoke/v1", "source": SOURCE,
            "adapter_version": ADAPTER_VERSION, "sport": SPORT, "region": region,
            "events_with_ou25": len(events), "quotes_ou25": len(rows),
            "bookmakers": [{"key": key, "quotes": books[key], "events": len({r["source_event_id"] for r in rows if r["bookmaker"] == key})} for key in sorted(books)],
            "timestamps_utc": all(str(r["odds_captured_at"]).endswith("+00:00") for r in rows),
            "totals_present": bool(rows), "recommendation": "HUMAN_DECISION_REQUIRED",
            "persistence": "none", "cohort_started": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only, sanitized The Odds API smoke.")
    parser.add_argument("--region", default="eu")
    args = parser.parse_args(argv)
    try:
        rows = TheOddsApiProvider(regions=args.region).fetch_ou25()
    except DataUnavailableError as exc:
        print(json.dumps({"source": SOURCE, "region": args.region, "status": "BLOCKED_BY_PROVIDER_CONFIGURATION", "message": str(exc), "cohort_started": False}, ensure_ascii=False))
        return 2
    print(json.dumps(report(rows, args.region), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
