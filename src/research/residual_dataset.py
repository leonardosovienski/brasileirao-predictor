"""Materialize strict point-in-time rows from market snapshots and results."""

from __future__ import annotations

import statistics as st
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from src.data.market_anchor import remove_overround
from src.research.residual_features import build_residual_features


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def materialize_total_market_records(
    observations: list[dict[str, Any]],
    results: list[dict[str, Any]],
    *,
    horizon_hours: float = 24.0,
    context: dict[str, dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    """Create one ``over`` research row per event/total line at a fixed horizon."""
    if horizon_hours <= 0:
        raise ValueError("horizon_hours must be positive")
    result_by_event = {str(row["source_event_id"]): row for row in results}
    by_event_market: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        market, line = str(row.get("market", "")), row.get("line")
        if not market.startswith("ou") or market.endswith("_1h") or not isinstance(line, (int, float)):
            continue
        by_event_market[(str(row.get("source_event_id")), market, float(line))].append(row)
    records = []
    for (event_id, market, line), rows in by_event_market.items():
        result = result_by_event.get(event_id)
        if result is None or result.get("home_goals") is None or result.get("away_goals") is None:
            continue
        kickoff = _utc(str(rows[0]["kickoff_at"]))
        cutoff = kickoff - timedelta(hours=horizon_hours)
        latest: dict[tuple[str, str], tuple[datetime, dict[str, Any]]] = {}
        for row in rows:
            captured = _utc(str(row["odds_captured_at"]))
            if captured > cutoff:
                continue
            key = (str(row.get("bookmaker")), str(row.get("selection")))
            if key not in latest or captured > latest[key][0]:
                latest[key] = (captured, row)
        fair_by_book, best_odds = {}, 0.0
        for bookmaker in {key[0] for key in latest}:
            pair = {
                selection: latest[(bookmaker, selection)][1]
                for selection in ("over", "under")
                if (bookmaker, selection) in latest
            }
            if set(pair) != {"over", "under"}:
                continue
            try:
                fair = remove_overround({selection: float(row["decimal_odds"]) for selection, row in pair.items()})
            except (KeyError, TypeError, ValueError):
                continue
            fair_by_book[bookmaker] = fair["over"]
            best_odds = max(best_odds, float(pair["over"]["decimal_odds"]))
        if not fair_by_book:
            continue
        probabilities = list(fair_by_book.values())
        anchor = st.median(probabilities)
        ctx = (context or {}).get(event_id, {})
        features = build_residual_features(
            book_probabilities=probabilities,
            captured_at=cutoff.isoformat(),
            kickoff_at=kickoff.isoformat(),
            xg_form_delta=float(ctx.get("xg_form_delta", 0.0)),
            rest_days_delta=float(ctx.get("rest_days_delta", 0.0)),
        )
        total = int(result["home_goals"]) + int(result["away_goals"])
        records.append(
            {
                "event_id": event_id,
                "market": market,
                "line": line,
                "kickoff_at": kickoff.isoformat(),
                "predicted_at": cutoff.isoformat(),
                "settled_at": str(result["settled_at"]),
                "features": features,
                "market_probability": anchor,
                "best_odds": best_odds,
                "outcome": int(total > line),
                "book_count": len(fair_by_book),
                "scientific_state": "COLLECTION_ONLY",
            }
        )
    return sorted(records, key=lambda row: (row["kickoff_at"], row["event_id"], row["line"]))
