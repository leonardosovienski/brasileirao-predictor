"""Audit retrospective provider states without inventing point-in-time receipts.

No IO, labels, provider clients or protected-cohort imports. The existing live
scanner's input contract cannot be satisfied by these historical payloads.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

SIDES = {"home": "101", "draw": "102", "away": "103"}
MISSING_EXECUTION = (
    "historical_available_at",
    "historical_received_at",
    "point_in_time_fixture_schedule",
    "bookmaker_region_mapping",
    "acceptance_slippage_and_capacity",
    "actual_costs_and_settlement",
)


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp_not_string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp_without_timezone")
    return parsed.astimezone(UTC)


def number(value: Any, *, minimum: float) -> bool:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return False
    try:
        return math.isfinite(value) and value > minimum
    except OverflowError:
        return False


def latest_state(timeline: Any, cutoff: datetime) -> dict[str, Any]:
    """Rank every state before checking active; suspensions cannot resurrect odds."""
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("cutoff_without_timezone")
    if not isinstance(timeline, list):
        return {"valid": False, "reason": "missing_or_malformed_history"}
    eligible = []
    for row in timeline:
        if not isinstance(row, dict):
            return {"valid": False, "reason": "malformed_state"}
        try:
            at = timestamp(row.get("createdAt"))
        except (ValueError, TypeError, OverflowError):
            return {"valid": False, "reason": "unorderable_state_timestamp"}
        if at <= cutoff:
            eligible.append((at, row))
    if not eligible:
        return {"valid": False, "reason": "no_state_at_cutoff"}
    at = max(at for at, _ in eligible)
    rows = [r for t, r in eligible if t == at]
    base = {"state_created_at": at.isoformat(), "state_age_seconds": (cutoff - at).total_seconds()}
    active = {str(type(r.get("active"))) + repr(r.get("active")) for r in rows}
    if len(active) != 1:
        return {**base, "valid": False, "reason": "conflicting_latest_state"}
    if rows[0].get("active") is not True:
        reason = "inactive_latest_state" if rows[0].get("active") is False else "unverified_latest_active"
        return {**base, "valid": False, "reason": reason}
    if any(not number(r.get("price"), minimum=1) for r in rows):
        return {**base, "valid": False, "reason": "invalid_latest_price"}
    if len({float(r["price"]) for r in rows}) != 1:
        return {**base, "valid": False, "reason": "conflicting_latest_state"}
    limits = [float(r["limit"]) if number(r.get("limit"), minimum=-1) and r["limit"] >= 0 else None for r in rows]
    limit = limits[0] if all(v == limits[0] for v in limits) else None
    return {
        **base,
        "valid": True,
        "reason": "last_recorded_active_state",
        "price": float(rows[0]["price"]),
        "reported_limit": limit,
        "limit_currency": None,
        "limit_is_accepted_fill": False,
    }


def audit_history(payload: Any, fixture: dict[str, Any], received_at: str) -> dict[str, Any]:
    """Coverage and strictly labelled conditional price diagnostic for one fixture."""
    kickoff, receipt = timestamp(fixture["kickoff_at"]), timestamp(received_at)
    if not datetime(2026, 1, 1, tzinfo=UTC) <= kickoff < datetime(2026, 7, 1, tzinfo=UTC):
        raise ValueError("outside_allowlisted_exploratory_window")
    decision = kickoff - timedelta(hours=1)
    result: dict[str, Any] = {
        "fixture_id": fixture["fixture_id"],
        "kickoff_at": kickoff.isoformat(),
        "decision_at": decision.isoformat(),
        "actual_archive_received_at": receipt.isoformat(),
        "archive_received_after_decision": receipt > decision,
        "execution_admitted": False,
        "missing_execution_evidence": list(MISSING_EXECUTION),
        "conditional_status": "REJECTED",
        "conditional_selection": None,
        "bookmakers": {},
    }
    if not isinstance(payload, dict) or payload.get("fixtureId") != fixture["fixture_id"]:
        result["reason"] = "payload_fixture_identity_mismatch"
        return result
    books = payload.get("bookmakers")
    if not isinstance(books, dict):
        result["reason"] = "malformed_bookmakers"
        return result
    for book in ("pinnacle", "bet365"):
        legs = {}
        for side, outcome_id in SIDES.items():
            try:
                timeline = books[book]["markets"]["101"]["outcomes"][outcome_id]["players"]["0"]
            except (KeyError, TypeError):
                timeline = None
            legs[side] = latest_state(timeline, decision)
        complete = all(leg["valid"] for leg in legs.values())
        fresh = complete and all(leg["state_age_seconds"] <= 120 for leg in legs.values())
        result["bookmakers"][book] = {"legs": legs, "complete_active": complete, "within_120s": fresh}
    if not all(book["complete_active"] for book in result["bookmakers"].values()):
        result["reason"] = "incomplete_active_pair"
        return result
    if not all(book["within_120s"] for book in result["bookmakers"].values()):
        result["reason"] = "last_change_age_over_120s_not_network_freshness"
        return result
    all_legs = [leg for b in result["bookmakers"].values() for leg in b["legs"].values()]
    clocks = [timestamp(leg["state_created_at"]) for leg in all_legs]
    skew = (max(clocks) - min(clocks)).total_seconds()
    result["state_change_skew_seconds"] = skew
    if skew > 30:
        result["reason"] = "state_change_skew_over_30s"
        return result
    pin = result["bookmakers"]["pinnacle"]["legs"]
    bet = result["bookmakers"]["bet365"]["legs"]
    total = sum(1 / leg["price"] for leg in pin.values())
    result["reference_overround_sum"] = total
    if total <= 1:
        result["reason"] = "reference_sum_not_above_one"
        return result
    evs = {side: (1 / pin[side]["price"]) / total * bet[side]["price"] - 1 - 0.02 for side in SIDES}
    choices = sorted(((-ev, side) for side, ev in evs.items() if 0 < ev <= 0.15))
    result.update(conditional_status="TEMPORAL_STATE_DIAGNOSTIC_ONLY", net_ev_scenario_by_side=evs)
    if choices:
        neg_ev, side = choices[0]
        result.update(conditional_selection=side, conditional_net_ev=-neg_ev, reason="conditional_price_discrepancy")
    else:
        result["reason"] = "no_conditional_selection"
    return result
