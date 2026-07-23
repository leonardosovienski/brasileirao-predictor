"""Frozen, sanitized stability criteria for selecting one H3/H5 bookmaker."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import json
import statistics
from pathlib import Path
from typing import Any

MIN_SMOKES = 3
MIN_SPAN_SECONDS = 24 * 60 * 60
MIN_PRESENCE_RATE = 0.80
MIN_EVENT_COVERAGE = 0.50
MAX_LAG_SECONDS = 15 * 60
EXCHANGES = frozenset({"betfair", "matchbook", "smarkets"})


def bookmaker_type(key: str) -> str:
    return "EXCHANGE" if key in EXCHANGES else "SPORTSBOOK"


def append_smoke(path: Path, rows: list[dict[str, Any]]) -> None:
    """Append one sanitized record per bookmaker; no API key/payload is stored."""
    with path.open("a", encoding="utf-8") as handle:
        for row in rows: handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def stability_report(path: Path) -> dict[str, Any]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
    smoke_ids = sorted({r["executed_at"] for r in records})
    by_book: dict[str, list[dict]] = defaultdict(list)
    for row in records: by_book[row["bookmaker_key"]].append(row)
    output = []
    for key, rows in sorted(by_book.items()):
        present = len({r["executed_at"] for r in rows}); seen = sum(int(r["events_seen"]) for r in rows)
        total_events = sum(int(r["events_with_totals"]) for r in rows)
        coverage = total_events / seen if seen else 0.0
        lag_ok = all(float(r["update_lag_seconds"]) <= MAX_LAG_SECONDS for r in rows)
        kind = bookmaker_type(key)
        span = (datetime.fromisoformat(smoke_ids[-1]) - datetime.fromisoformat(smoke_ids[0])).total_seconds() if len(smoke_ids) > 1 else 0
        if kind == "EXCHANGE": classification = "BOOKMAKER_REJECTED"
        elif present < MIN_SMOKES or span < MIN_SPAN_SECONDS: classification = "BOOKMAKER_CANDIDATE"
        elif present / len(smoke_ids) < MIN_PRESENCE_RATE: classification = "BOOKMAKER_INTERMITTENT"
        elif coverage < MIN_EVENT_COVERAGE: classification = "BOOKMAKER_INSUFFICIENT_COVERAGE"
        elif not lag_ok: classification = "BOOKMAKER_INTERMITTENT"
        else: classification = "BOOKMAKER_STABLE"
        output.append({"bookmaker_key": key, "bookmaker_type": kind, "smokes_observed": len(smoke_ids), "smokes_present": present, "presence_rate": round(present / len(smoke_ids), 4) if smoke_ids else 0.0, "event_coverage": round(coverage, 4), "totals_coverage": round(coverage, 4), "valid_quote_rate": 1.0, "median_update_lag_seconds": statistics.median(float(r["update_lag_seconds"]) for r in rows), "valid_quotes": sum(int(r["valid_quotes"]) for r in rows), "max_update_lag_seconds": max((float(r["update_lag_seconds"]) for r in rows), default=None), "classification": classification})
    stable = [r for r in output if r["classification"] == "BOOKMAKER_STABLE"]
    stable.sort(key=lambda r: (-r["presence_rate"], -r["event_coverage"], r["median_update_lag_seconds"], -r["valid_quotes"], r["bookmaker_key"]))
    recommendation = ("BOOKMAKER_RECOMMENDATION_READY" if stable else
                      "NO_STABLE_BOOKMAKER_FOUND" if len(smoke_ids) >= MIN_SMOKES else
                      "BOOKMAKER_STABILITY_PENDING")
    return {"schema_version": "bookmaker-stability/v1", "criteria": {"min_smokes": MIN_SMOKES, "min_span_seconds": MIN_SPAN_SECONDS, "min_presence_rate": MIN_PRESENCE_RATE, "min_event_coverage": MIN_EVENT_COVERAGE, "max_lag_seconds": MAX_LAG_SECONDS}, "smokes": len(smoke_ids), "bookmakers": output, "recommended_bookmaker": stable[0]["bookmaker_key"] if stable else None, "approved_alternatives": [r["bookmaker_key"] for r in stable[1:]], "recommendation": recommendation}
