"""Audit independently received API observations, preserving every parent state.

Receipt clocks establish when the API response was available to this collector.
They do not establish bookmaker publication time or acceptance of a wager.
"""

from __future__ import annotations

import json
import math
from typing import Any

from .historical_admission import SIDES, number, timestamp


def strict_json_loads(raw: str | bytes) -> Any:
    """Reject ambiguity before a JSON parser can discard a conflicting state."""

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate_json_key")
            value[key] = item
        return value

    def finite_float(value: str) -> float:
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("nonfinite_json_number")
        return result

    def reject_constant(value: str) -> Any:
        raise ValueError("nonfinite_json_number")

    return json.loads(raw, object_pairs_hook=object_pairs, parse_float=finite_float, parse_constant=reject_constant)


def audit_capture(
    payload: Any,
    receipt: dict[str, Any],
    expected_fixture: str,
    *,
    expected_identity: dict[str, int] | None = None,
) -> dict[str, Any]:
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
        "pair_api_state_admitted": False,
        "bookmakers": {},
        "missing_execution_evidence": ["accepted_price_and_stake", "offer_capacity", "costs", "future_validation"],
    }
    if not isinstance(payload, dict) or payload.get("fixtureId") != expected_fixture:
        result["reason"] = "fixture_identity_mismatch"
        return result
    if expected_identity is not None:
        fields = {"participant1Id", "participant2Id", "sportId", "tournamentId", "seasonId"}
        if set(expected_identity) != fields or any(type(v) is not int or v <= 0 for v in expected_identity.values()):
            raise ValueError("invalid_frozen_identity_contract")
        if expected_identity["participant1Id"] == expected_identity["participant2Id"]:
            raise ValueError("invalid_frozen_identity_contract")
        result["frozen_identity_admitted"] = all(
            type(payload.get(field)) is int and payload[field] == expected_identity[field] for field in fields
        )
        if not result["frozen_identity_admitted"]:
            result["reason"] = "frozen_fixture_identity_mismatch"
            return result
    result["fixture_identity_scope"] = "frozen_participants_and_competition" if expected_identity else "fixture_id_only"
    kickoff = timestamp(payload.get("startTime"))
    result["kickoff_at"] = kickoff.isoformat()
    if type(payload.get("statusId")) is not int or payload["statusId"] != 0 or received >= kickoff:
        result["reason"] = "not_pre_game"
        return result
    if payload.get("trueStartTime") is not None or payload.get("trueEndTime") is not None:
        result["reason"] = "actual_start_or_end_conflicts_with_pre_game"
        return result
    if payload.get("hasOdds") is not True:
        result["reason"] = "fixture_odds_absent_or_unverified"
        return result
    if payload.get("updatedAt") is not None:
        try:
            if timestamp(payload["updatedAt"]) > received:
                raise ValueError("future_fixture_update")
        except (ValueError, TypeError, OverflowError):
            result["reason"] = "invalid_or_future_fixture_update"
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
                    if field == "changedAt":
                        reasons.append(side + ":missing_change_timestamp")
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
