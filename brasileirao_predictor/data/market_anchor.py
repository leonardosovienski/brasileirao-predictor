"""Market-derived baselines for residual research; no betting decisions."""

from __future__ import annotations

import math
import statistics as st
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
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


def consensus_anchor(rows: Iterable[dict[str, Any]], *, market: str, offered_by: str | None = None) -> dict[str, Any]:
    """Diagnostic no-vig consensus plus the best observed price per selection.

    A bookmaker contributes only when all selections for its market/line are
    present at the same captured timestamp. This prevents mixing stale sides.
    """
    grouped: dict[tuple, dict[str, float]] = defaultdict(dict)
    eligible = [row for row in rows if row.get("market") == market]
    identities = {(row.get("source"), row.get("source_event_id"), row.get("line")) for row in eligible}
    if len(identities) != 1 or any(not source or not event for source, event, _ in identities):
        raise ValueError("consensus requires exactly one source event and line")
    clocks = set()
    for row in eligible:
        captured = datetime.fromisoformat(str(row.get("odds_captured_at")))
        if captured.tzinfo is None or captured.utcoffset() is None:
            raise ValueError("capture must have timezone")
        clocks.add(captured.astimezone(UTC))
        if len(clocks) > 1:
            raise ValueError("diagnostic consensus requires one capture; state history needs explicit as-of selection")
        if not isinstance(row.get("bookmaker"), str) or not row["bookmaker"].strip():
            raise ValueError("bookmaker required")
        key = (row.get("bookmaker"), row.get("odds_captured_at"), row.get("line"))
        odd = row.get("decimal_odds")
        if not isinstance(odd, (int, float)):
            continue
        selection = str(row.get("selection"))
        if selection in grouped[key] and grouped[key][selection] != odd:
            raise ValueError("conflicting duplicate selection")
        grouped[key][selection] = float(odd)
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
    reference = [item for item in complete if item[0] != offered_by]
    if not reference:
        raise ValueError("no independent reference after excluding offering bookmaker")
    probabilities = {selection: st.median(item[4][selection] for item in reference) for selection in sorted(expected)}
    total = sum(probabilities.values())
    probabilities = {selection: value / total for selection, value in probabilities.items()}
    best_odds = {selection: max(item[3][selection] for item in complete) for selection in sorted(expected)}
    return {
        "market": market,
        "line": complete[0][2],
        "books": sorted({item[0] for item in reference}),
        "book_count": len({item[0] for item in reference}),
        "fair_probabilities": probabilities,
        "best_odds": best_odds,
        "method": "median-proportional-devig/v2",
        "excluded_offering_bookmaker": offered_by,
        "reference_independent_of_offering_bookmaker": offered_by is not None,
        "economic_evidence_eligible": False,
        "price_status": "OBSERVED_ONLY_NOT_EXECUTABLE",
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
