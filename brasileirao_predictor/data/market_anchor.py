"""Market-derived baselines for residual research; no betting decisions."""

from __future__ import annotations

import math
import statistics as st
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from brasileirao_predictor.data.bookmaker_odds import persist_snapshots


def remove_overround(odds: dict[str, float]) -> dict[str, float]:
    """Return proportional no-vig probabilities for one complete book market."""
    if len(odds) < 2:
        raise ValueError("mercado incompleto")
    implied = {}
    for selection, odd in odds.items():
        if not isinstance(odd, (int, float)) or not math.isfinite(odd) or odd <= 1:
            raise ValueError(f"odd invalida para {selection}")
        implied[selection] = 1.0 / float(odd)
    overround = sum(implied.values())
    if overround <= 1.0:
        raise ValueError("mercado sem margem positiva nao e sportsbook auditavel")
    return {selection: value / overround for selection, value in implied.items()}


def consensus_anchor(rows: Iterable[dict[str, Any]], *, market: str) -> dict[str, Any]:
    """Median no-vig consensus plus the best executable price per selection.

    A bookmaker contributes only when all selections for its market/line are
    present at the same captured timestamp. This prevents mixing stale sides.
    """
    grouped: dict[tuple, dict[str, float]] = defaultdict(dict)
    eligible = [row for row in rows if row.get("market") == market]
    for row in eligible:
        key = (row.get("bookmaker"), row.get("odds_captured_at"), row.get("line"))
        odd = row.get("decimal_odds")
        if not isinstance(odd, (int, float)):
            continue
        grouped[key][str(row.get("selection"))] = float(odd)
    complete = []
    expected = {"home", "draw", "away"} if market in {"1x2", "1x2_1h"} else {"over", "under"}
    for (bookmaker, captured_at, line), odds in grouped.items():
        if set(odds) != expected:
            continue
        try:
            fair = remove_overround(odds)
        except ValueError:
            continue
        complete.append((bookmaker, captured_at, line, odds, fair))
    if not complete:
        raise ValueError("nenhum mercado completo e auditavel")
    probabilities = {selection: st.median(item[4][selection] for item in complete) for selection in sorted(expected)}
    total = sum(probabilities.values())
    probabilities = {selection: value / total for selection, value in probabilities.items()}
    best_odds = {selection: max(item[3][selection] for item in complete) for selection in sorted(expected)}
    return {
        "market": market,
        "line": complete[0][2],
        "books": sorted({item[0] for item in complete}),
        "book_count": len({item[0] for item in complete}),
        "fair_probabilities": probabilities,
        "best_odds": best_odds,
        "method": "median-proportional-devig/v1",
    }


def persist_market_observations(path, rows: list[dict[str, Any]]) -> int:
    """Persist normalized provider rows using the shared append-only ledger."""
    normalized = []
    for row in rows:
        normalized.append(
            {
                **row,
                "event_id": row.get("canonical_match_id") or row.get("source_event_id"),
                "odd": row.get("decimal_odds"),
                "scientific_state": "COLLECTION_ONLY",
            }
        )
    return persist_snapshots(path, normalized)
