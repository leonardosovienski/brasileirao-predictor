"""Audit independently received API observations, preserving every parent state.

Receipt clocks establish when the API response was available to this collector.
They do not establish bookmaker publication time or acceptance of a wager.
"""

from __future__ import annotations

from typing import Any

from .historical_admission import SIDES, number, timestamp


def audit_capture(payload: Any, receipt: dict[str, Any], expected_fixture: str) -> dict[str, Any]:
    started = timestamp(receipt["requested_at"])
    received = timestamp(receipt["received_at"])
    if received < started:
        raise ValueError("receipt_before_request")
    result: dict[str, Any] = {
        "fixture_id": expected_fixture,
        "received_at": received.isoformat(),
        "round_trip_seconds": (received - started).total_seconds(),
        "clock_semantics": "actual_collector_API_receipt_not_bookmaker_publication",
        "execution_admitted": False,
        "bookmakers": {},
        "missing_execution_evidence": ["accepted_price_and_stake", "offer_capacity", "costs", "future_validation"],
    }
    if not isinstance(payload, dict) or payload.get("fixtureId") != expected_fixture:
        result["reason"] = "fixture_identity_mismatch"
        return result
    kickoff = timestamp(payload.get("startTime"))
    result["kickoff_at"] = kickoff.isoformat()
    if type(payload.get("statusId")) is not int or payload["statusId"] != 0 or received >= kickoff:
        result["reason"] = "not_pre_game"
        return result
    for name in ("pinnacle", "bet365.bet.br"):
        reasons = []
        books = payload.get("bookmakerOdds", {})
        book = books.get(name, {}) if isinstance(books, dict) else {}
        if not isinstance(book, dict):
            book = {}
        if book.get("bookmakerIsActive") is not True:
            reasons.append("bookmaker_not_active")
        if book.get("suspended") is not False:
            reasons.append("bookmaker_suspended_or_unverified")
        markets = book.get("markets", {})
        market = markets.get("101", {}) if isinstance(markets, dict) else {}
        if not isinstance(market, dict):
            market = {}
        if market.get("marketActive") is not True:
            reasons.append("market_not_active")
        legs = {}
        for side, outcome in SIDES.items():
            try:
                row = market["outcomes"][outcome]["players"]["0"]
                if not isinstance(row, dict):
                    raise TypeError
            except (KeyError, TypeError):
                reasons.append(side + ":missing_selection")
                continue
            if row.get("active") is not True or not number(row.get("price"), minimum=1):
                reasons.append(side + ":invalid_or_inactive_selection")
                continue
            clocks = {}
            for field in ("changedAt", "bookmakerChangedAt"):
                if row.get(field) is None:
                    clocks[field] = None
                    continue
                try:
                    at = timestamp(row[field])
                    clocks[field] = at.isoformat()
                    if at > received:
                        reasons.append(side + ":future_change_timestamp")
                except (ValueError, TypeError, OverflowError):
                    reasons.append(side + ":invalid_change_timestamp")
            limit = row.get("limit")
            legs[side] = {
                "price": float(row["price"]),
                "change_clocks": clocks,
                "reported_limit": limit
                if isinstance(limit, int | float) and number(limit, minimum=-1) and limit >= 0
                else None,
                "limit_currency": None,
            }
        result["bookmakers"][name] = {
            "api_state_admitted": not reasons and len(legs) == 3,
            "reasons": reasons,
            "bookmakerIsActive": book.get("bookmakerIsActive"),
            "suspended": book.get("suspended"),
            "marketActive": market.get("marketActive"),
            "legs": legs,
        }
    result["pair_api_state_admitted"] = all(b["api_state_admitted"] for b in result["bookmakers"].values())
    result["reason"] = "API_OBSERVATION_ONLY" if result["pair_api_state_admitted"] else "INACTIVE_OR_UNVERIFIED_PAIR"
    return result
