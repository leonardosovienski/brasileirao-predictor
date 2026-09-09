"""Price-only break-even diagnostics, with no labels or execution claims.

These functions deliberately do not turn a legacy aggregate vector into
bookmaker snapshots. The proportional reference is a diagnostic estimate,
not the probability of an outcome or evidence of an independent reference.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime
from statistics import median
from typing import Any

SIDES = ("home", "draw", "away")
SCENARIO_COSTS = (0.0, 0.01, 0.02, 0.03, 0.05)


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"invalid_number:{name}")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"invalid_number:{name}") from exc
    if not math.isfinite(result):
        raise ValueError(f"invalid_number:{name}")
    return result


def break_even_decimal(probability: float, *, cost_per_unit: float, commission_on_profit: float = 0.0) -> float:
    """Invert p*(1+(o-1)*(1-commission))-1-cost = 0.

    Cost is charged per unit staked regardless of outcome. Commission is on
    each winning bet's profit, not on returned principal or a netted market.
    This does not encode taxes, capacity, slippage or bookmaker acceptance.
    """
    probability = _finite(probability, "probability")
    cost = _finite(cost_per_unit, "cost_per_unit")
    commission = _finite(commission_on_profit, "commission_on_profit")
    if not 0 < probability <= 1 or not 0 <= cost < 1 or not 0 <= commission < 1:
        raise ValueError("invalid_probability_or_friction_domain")
    required = 1 + ((1 + cost) / probability - 1) / (1 - commission)
    if not math.isfinite(required):
        raise ValueError("nonfinite_required_price")
    return required


def aggregate_price_hurdle(odds: list[float], *, cost_per_unit: float = 0.02) -> dict[str, Any]:
    """Measure a complete H/D/A aggregate; do not claim it is executable."""
    if not isinstance(odds, list) or len(odds) != 3:
        raise ValueError("incomplete_1x2_vector")
    prices = [_finite(value, "odds") for value in odds]
    if any(price <= 1 for price in prices):
        raise ValueError("decimal_odds_must_exceed_one")
    implied = [1 / price for price in prices]
    overround_sum = math.fsum(implied)
    probabilities = [value / overround_sum for value in implied]
    required = [break_even_decimal(p, cost_per_unit=cost_per_unit) for p in probabilities]
    own_gross_ev = [p * price - 1 for p, price in zip(probabilities, prices, strict=True)]
    uplift = [threshold / price - 1 for threshold, price in zip(required, prices, strict=True)]
    algebraic_ev = 1 / overround_sum - 1
    algebraic_uplift = overround_sum * (1 + cost_per_unit) - 1
    if not all(math.isclose(value, algebraic_ev, abs_tol=1e-12) for value in own_gross_ev):
        raise ArithmeticError("own_price_identity_mismatch")
    if not all(math.isclose(value, algebraic_uplift, abs_tol=1e-12) for value in uplift):
        raise ArithmeticError("price_uplift_identity_mismatch")
    return {
        "overround_sum": overround_sum,
        "margin_sign": "positive" if overround_sum > 1 else "zero" if overround_sum == 1 else "negative",
        "reference_kind": "PROPORTIONAL_SAME_AGGREGATE_DIAGNOSTIC_ONLY",
        "probabilities": dict(zip(SIDES, probabilities, strict=True)),
        "aggregate_odds": dict(zip(SIDES, prices, strict=True)),
        "own_price_gross_ev": algebraic_ev,
        "own_price_net_ev_scenario": algebraic_ev - cost_per_unit,
        "cost_per_unit_scenario": cost_per_unit,
        "break_even_odds_scenario": dict(zip(SIDES, required, strict=True)),
        "relative_price_uplift_to_break_even": algebraic_uplift,
        "executable": False,
    }


def _distribution(values: list[float]) -> dict[str, float | int] | None:
    if not values:
        return None
    ordered = sorted(values)
    # Nearest-rank p90, declared rather than dependent on a library default.
    return {
        "n": len(values),
        "min": ordered[0],
        "median": median(ordered),
        "p90": ordered[math.ceil(0.9 * len(ordered)) - 1],
        "max": ordered[-1],
    }


def audit_legacy_2025(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit the specific closed-study export. Never access result fields.

    2025 is fixed, already explored, and separate from protected cohorts. The
    source format supplies no quote clocks or bookmaker; every row is excluded
    from executable research even if a descriptive vector is numerically valid.
    Missing prices stay in the universe. Unexpected provenance fields fail
    closed, because this adapter has no authority to interpret a new schema.
    """
    if not isinstance(rows, list):
        raise ValueError("history_must_be_list")
    allowed = {"event_id", "home", "away", "kickoff", "date", "tournament", "city", "neutral", "result", "odds"}
    admitted = []
    identities: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("history_row_must_be_object")
        date = row.get("date")
        if not isinstance(date, str):
            raise ValueError("date_required_for_universe_filter")
        if not date.startswith("2025-"):
            continue
        if set(row) - allowed:
            raise ValueError("unexpected_legacy_schema")
        if row.get("tournament") != "Brasileirão Série A":
            raise ValueError("tournament_outside_universe")
        identity = row.get("event_id")
        if isinstance(identity, bool) or not isinstance(identity, str | int) or not str(identity).strip():
            raise ValueError("invalid_event_identity")
        key = str(identity)
        if key in identities:
            raise ValueError("duplicate_event_identity")
        identities.add(key)
        if not isinstance(row.get("home"), str) or not isinstance(row.get("away"), str):
            raise ValueError("missing_team_identity")
        if not row["home"].strip() or not row["away"].strip() or row["home"] == row["away"]:
            raise ValueError("conflicting_team_identity")
        kickoff = datetime.fromisoformat(row["kickoff"])
        if kickoff.tzinfo is None or kickoff.utcoffset() is None or kickoff.year != 2025:
            raise ValueError("kickoff_incompatible_with_universe")
        if kickoff.date().isoformat() != date:
            raise ValueError("date_kickoff_conflict")
        admitted.append(row)

    events = []
    price_reasons: Counter[str] = Counter()
    for row in sorted(admitted, key=lambda item: (item["kickoff"], str(item["event_id"]))):
        event: dict[str, Any] = {
            "event_id": str(row["event_id"]),
            "date": row["date"],
            "kickoff_supplied": row["kickoff"],
            "home": row["home"],
            "away": row["away"],
            "action": "ABSTAIN",
            "reason": "MISSING_BOOKMAKER_AND_QUOTE_TIMELINE",
            "executable": False,
            "missing_evidence": [
                "bookmaker",
                "quote_observed_at",
                "quote_available_at",
                "quote_received_at",
                "quote_status",
                "raw_quote_payload",
                "independent_reference",
                "execution_capacity",
            ],
        }
        try:
            market_prices = row.get("odds")
            vector = market_prices.get("1x2") if isinstance(market_prices, dict) else None
            event["price_diagnostic"] = aggregate_price_hurdle(vector)  # type: ignore[arg-type]
        except ValueError as exc:
            event["price_diagnostic"] = None
            event["price_rejection"] = str(exc)
            price_reasons[str(exc)] += 1
        events.append(event)

    valid = [event for event in events if event["price_diagnostic"] is not None]
    monthly: dict[str, list[float]] = defaultdict(list)
    for event in valid:
        monthly[event["date"][:7]].append(event["price_diagnostic"]["relative_price_uplift_to_break_even"])
    sums = [event["price_diagnostic"]["overround_sum"] for event in valid]
    return {
        "schema_version": "price-hurdle-audit/1",
        "status": "BLOCKED_MISSING_PRICE_PROVENANCE",
        "evaluation_year": 2025,
        "market": "1x2",
        "labels_accessed": False,
        "profitability_established": False,
        "execution_proven": False,
        "real_capital_enabled": False,
        "summary": {
            "universe_matches": len(events),
            "numeric_complete_vectors": len(valid),
            "matches_without_numeric_price": len(events) - len(valid),
            "executable_price_pairs": 0,
            "opportunities": None,
            "opportunities_reason": "NOT_MEASURABLE_WITHOUT_ADMISSIBLE_PRICE_PAIRS",
            "abstentions": len(events),
            "bets": 0,
            "stake_units": 0.0,
            "price_rejections": dict(price_reasons),
            "margin_sign_counts": dict(Counter(event["price_diagnostic"]["margin_sign"] for event in valid)),
            "overround_sum": _distribution(sums),
            "own_price_gross_ev": _distribution([1 / value - 1 for value in sums]),
            "relative_price_uplift_scenarios": {
                str(cost): _distribution([value * (1 + cost) - 1 for value in sums]) for cost in SCENARIO_COSTS
            },
            "monthly_relative_uplift_at_2pct_cost": {month: _distribution(v) for month, v in sorted(monthly.items())},
            "actual_execution_costs": None,
            "fixed_operating_costs": None,
        },
        "abstention_portfolio": {
            "initial_bankroll_scenario_units": 100.0,
            "final_bankroll_before_unknown_fixed_costs_units": 100.0,
            "contributions": 0.0,
            "stakes": 0.0,
            "liability": 0.0,
            "locked_capital": 0.0,
            "returned_principal": 0.0,
            "winning_profit": 0.0,
            "variable_execution_costs": 0.0,
            "net_betting_result": 0.0,
            "roi_on_stakes": None,
            "return_on_bankroll_before_fixed_costs": 0.0,
            "simultaneous_exposure": 0.0,
            "total_business_net_result": None,
        },
        "events": events,
    }
