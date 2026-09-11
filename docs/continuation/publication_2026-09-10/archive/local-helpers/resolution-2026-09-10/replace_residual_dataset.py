from pathlib import Path

path = Path('C:/BRASILEIRAO/brasileirao-predictor/brasileirao_predictor/research/residual_dataset.py')
source = '''"""Fixed-house, independent-reference materialization for conditional research.

Only full-time binary half-goal totals are implemented. Missing inputs remain
explicit abstentions; neither bookmaker availability nor acceptance is certified.
"""
from __future__ import annotations

import statistics as st
from collections import defaultdict
from datetime import timedelta
from numbers import Integral
from typing import Any

from brasileirao_predictor.data.market_anchor import remove_overround
from brasileirao_predictor.research.residual_features import build_residual_features
from brasileirao_predictor.research.shadow_portfolio import finite, utc


def materialize_total_market_records(
    observations: list[dict[str, Any]], results: list[dict[str, Any]], *, offer_bookmaker: str,
    horizon_hours: float = 24.0, max_pair_skew_seconds: float = 60.0,
    max_quote_age_seconds: float = 120.0, total_line: float = 2.5,
    context: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """The caller fixes the offer house and line before evaluating performance.

    The universe is every supplied event observed in that market, including
    pending results and unavailable prices. Events never supplied cannot be
    recovered from this function. Legacy last-update-only rows are inadmissible.
    """
    if not isinstance(offer_bookmaker, str) or not offer_bookmaker.strip():
        raise ValueError("offer_bookmaker must be fixed explicitly")
    horizon_hours = finite(horizon_hours, "horizon_hours")
    max_pair_skew_seconds = finite(max_pair_skew_seconds, "max_pair_skew_seconds")
    max_quote_age_seconds = finite(max_quote_age_seconds, "max_quote_age_seconds")
    total_line = finite(total_line, "total_line")
    if horizon_hours <= 0 or max_pair_skew_seconds < 0 or max_quote_age_seconds <= 0 or total_line < 0 or total_line % 1 != 0.5:
        raise ValueError("positive horizon/age and a binary half-goal line are required")
    result_by_event = {}
    for row in results:
        event = str(row["source_event_id"])
        if event in result_by_event:
            raise ValueError("duplicate result event; reconcile revisions before materialization")
        for key in ("home_goals", "away_goals"):
            value = row.get(key)
            if value is not None and (isinstance(value, bool) or not isinstance(value, Integral) or value < 0):
                raise ValueError("goals must be nonnegative integer counts")
        result_by_event[event] = row
    market = f"ou{total_line:g}"
    events = defaultdict(list)
    for row in observations:
        if row.get("market") == market and row.get("line") == total_line:
            event = row.get("source_event_id")
            if isinstance(event, bool) or not isinstance(event, (str, int)) or not str(event).strip():
                raise ValueError("source_event_id is required")
            events[str(event)].append(row)
    records = []
    for event, rows in sorted(events.items()):
        kickoffs = {utc(row["kickoff_at"]) for row in rows}
        if len(kickoffs) != 1:
            raise ValueError("conflicting kickoff revisions require an as-of fixture snapshot")
        kickoff = kickoffs.pop()
        cutoff = kickoff - timedelta(hours=horizon_hours)
        result = result_by_event.get(event, {})
        outcome, settled = None, None
        if result.get("home_goals") is not None and result.get("away_goals") is not None:
            settled = utc(result["settled_at"])
            if settled <= kickoff:
                raise ValueError("result settlement must follow kickoff")
            outcome = int(result["home_goals"] + result["away_goals"] > total_line)
        record = {"event_id": event, "market": market, "period": "FT", "line": total_line,
                  "kickoff_at": kickoff.isoformat(), "predicted_at": cutoff.isoformat(),
                  "settled_at": settled.isoformat() if settled else None, "outcome": outcome,
                  "features": None, "market_probability": None, "best_odds": None,
                  "best_odds_by_selection": None, "offer_bookmaker": offer_bookmaker,
                  "reference_books": [], "book_count": 0, "data_status": "ABSTAIN_DATA",
                  "abstention_reason": "NO_ADMISSIBLE_OFFER_OR_REFERENCE",
                  "scientific_state": "COLLECTION_ONLY", "capital_enabled": False,
                  "economic_evidence": False, "input_scope": "caller_declared_clocks_and_status"}
        if result.get("label_available_at") is not None:
            record["label_available_at"] = result["label_available_at"]
        latest, invalid_books = {}, set()
        for row in rows:
            book, side = row.get("bookmaker"), row.get("selection")
            if not isinstance(book, str) or not book.strip() or side not in {"over", "under"}:
                continue
            try:
                received = utc(row["retrieved_at"])
                if received > cutoff:
                    continue
                observed, available = utc(row["observed_at"]), utc(row["available_at"])
                if observed > available or available > received or row.get("period") != "FT":
                    raise ValueError("invalid quote clocks or period")
                if row.get("published_at") is not None and utc(row["published_at"]) > available:
                    raise ValueError("publication unavailable at declared availability")
            except (ValueError, KeyError, TypeError):
                invalid_books.add(book)
                continue
            key = (book, side)
            if key not in latest or received > latest[key][0]:
                latest[key] = (received, row, False)
            elif received == latest[key][0] and row != latest[key][1]:
                latest[key] = (received, row, True)
        pairs, fair_by_book = {}, {}
        for book in sorted({key[0] for key in latest} - invalid_books):
            pair = [latest.get((book, side)) for side in ("over", "under")]
            if any(item is None or item[2] or item[1].get("status") != "ACTIVE" for item in pair):
                continue
            source = pair[0][1].get("source")
            if not isinstance(source, str) or not source.strip() or pair[1][1].get("source") != source:
                continue
            observed = [utc(item[1]["observed_at"]) for item in pair]
            if (max(observed) - min(observed)).total_seconds() > max_pair_skew_seconds or (cutoff - min(observed)).total_seconds() > max_quote_age_seconds:
                continue
            try:
                prices = {side: finite(item[1]["decimal_odds"], "decimal_odds") for side, item in zip(("over", "under"), pair)}
                if any(price <= 1 for price in prices.values()):
                    raise ValueError("invalid decimal odds")
                probabilities = remove_overround(prices)
            except (ValueError, KeyError, TypeError):
                continue
            pairs[book], fair_by_book[book] = prices, probabilities["over"]
        references = sorted(set(fair_by_book) - {offer_bookmaker})
        if offer_bookmaker in pairs and references:
            probabilities = [fair_by_book[book] for book in references]
            record.update(reference_books=references, book_count=len(references))
            ctx = (context or {}).get(event)
            record["abstention_reason"] = "MISSING_OR_UNAVAILABLE_FEATURE_CONTEXT"
            if ctx is not None and utc(ctx["available_at"]) <= cutoff:
                current, expected = ctx.get("current_starters"), ctx.get("expected_starters")
                if not isinstance(current, list) or not isinstance(expected, list) or any(not isinstance(player, str) or not player for player in current + expected):
                    raise ValueError("feature context requires explicit starter lists")
                if len(current) > 11 or len(expected) > 11 or len(set(current)) != len(current) or len(set(expected)) != len(expected):
                    raise ValueError("starter lists must be unique and contain at most eleven players")
                features = build_residual_features(book_probabilities=probabilities, captured_at=cutoff.isoformat(),
                    kickoff_at=kickoff.isoformat(), current_starters=set(current), expected_starters=set(expected),
                    xg_form_delta=finite(ctx["xg_form_delta"], "xg_form_delta"), rest_days_delta=finite(ctx["rest_days_delta"], "rest_days_delta"))
                record.update(features=features, features_available_at=ctx["available_at"], market_probability=st.median(probabilities),
                    best_odds=pairs[offer_bookmaker]["over"], best_odds_by_selection=pairs[offer_bookmaker],
                    data_status="READY_FOR_CONDITIONAL_REPLAY", abstention_reason=None)
        records.append(record)
    return sorted(records, key=lambda row: (row["predicted_at"], row["event_id"]))
'''
path.write_text(source, encoding='utf-8')
