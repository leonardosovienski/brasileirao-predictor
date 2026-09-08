"""Frozen, outcome-blind selection and flat-stake counterfactual accounting.

This module has no file, network or database access. Selection receives only
probabilities and quotes; match outcomes are passed to settlement afterwards.
All monetary results are in units. One unit is the same size for every event.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

MARKETS = ("1x2", "ou25", "btts")
SIDES = {"1x2": ("home", "draw", "away"), "ou25": ("over", "under"), "btts": ("yes", "no")}
ODDS_BOUNDS = {"1x2": (1.05, 20.0), "ou25": (1.2, 5.0), "btts": (1.2, 5.0)}


@dataclass(frozen=True)
class Policy:
    """Edge is p_model minus raw implied probability, in (min_edge,max_edge]."""

    min_edge: float = 0.02
    max_edge: float = 0.15
    cost_per_unit: float = 0.02
    min_overround: float = 1.0
    max_overround: float = 1.3

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not _is_number(value):
                raise ValueError(f"{name} must be a finite number")
        if not 0 <= self.min_edge <= self.max_edge <= 1:
            raise ValueError("Require 0 <= min_edge <= max_edge <= 1")
        if self.cost_per_unit < 0:
            raise ValueError("cost_per_unit cannot be negative")
        if not 0 < self.min_overround <= self.max_overround:
            raise ValueError("Invalid overround interval")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


DEFAULT_POLICY = Policy()


def _inside(value: float, lower: float, upper: float) -> bool:
    # Tolerance only resolves binary floating-point arithmetic at fixed bounds.
    return lower - 1e-12 <= value <= upper + 1e-12


def _probabilities(forecast: Mapping[str, Any], market: str) -> tuple[list[float] | None, str | None]:
    if market == "1x2":
        value = forecast.get("p_1x2")
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            return None, "missing_or_incomplete_probability_vector"
        if any(not _is_number(p) or not 0 <= p <= 1 for p in value):
            return None, "invalid_probability"
        if not math.isclose(math.fsum(value), 1.0, abs_tol=1e-6, rel_tol=0):
            return None, "probability_vector_does_not_sum_to_one"
        return list(value), None
    value = forecast.get("p_over25" if market == "ou25" else "p_btts")
    if value is None:
        return None, "missing_probability"
    if not _is_number(value) or not 0 <= value <= 1:
        return None, "invalid_probability"
    return [value, 1.0 - value], None


def evaluate_candidates(
    forecast: Mapping[str, Any],
    odds: Mapping[str, Any] | None,
    policy: Policy = DEFAULT_POLICY,
) -> dict[str, Any]:
    """Return eligible sides and quote/probability rejections, without outcomes.

    Quotes must supply complete market vectors: 1x2=[H,D,A],
    ou25=[over,under], btts=[yes,no]. A missing or invalid quote invalidates
    its entire market, without borrowing prices from another event or time.
    """
    odds = odds or {}
    candidates: list[dict[str, Any]] = []
    rejected: dict[str, str] = {}
    valid_markets: list[str] = []
    for market in MARKETS:
        probabilities, reason = _probabilities(forecast, market)
        if reason:
            rejected[market] = reason
            continue
        quotes = odds.get(market)
        if not isinstance(quotes, (list, tuple)) or len(quotes) != len(SIDES[market]):
            rejected[market] = "missing_or_incomplete_quote_vector"
            continue
        lower, upper = ODDS_BOUNDS[market]
        if any(not _is_number(o) or not lower <= o <= upper for o in quotes):
            rejected[market] = "invalid_or_out_of_range_quote"
            continue
        overround = math.fsum(1.0 / o for o in quotes)
        if not _inside(overround, policy.min_overround, policy.max_overround):
            rejected[market] = "overround_out_of_range"
            continue
        valid_markets.append(market)
        assert probabilities is not None
        for side_index, (probability, odd) in enumerate(zip(probabilities, quotes)):
            implied_probability = 1.0 / odd
            edge = probability - implied_probability
            # A 1e-12 margin treats numerical representations of the exact
            # minimum as the boundary, which the frozen policy excludes.
            if not policy.min_edge + 1e-12 < edge <= policy.max_edge + 1e-12:
                continue
            predicted_net_ev = probability * odd - 1.0 - policy.cost_per_unit
            if predicted_net_ev <= 0:
                continue
            candidates.append({
                "market": market,
                "side": SIDES[market][side_index],
                "side_index": side_index,
                "probability": probability,
                "odd": odd,
                "implied_probability": implied_probability,
                "edge": edge,
                "predicted_net_ev": predicted_net_ev,
                "overround": overround,
            })
    candidates.sort(key=lambda c: (-c["predicted_net_ev"], MARKETS.index(c["market"]), c["side_index"]))
    return {"candidates": candidates, "valid_markets": valid_markets, "rejected_markets": rejected}


def select_candidate(
    forecast: Mapping[str, Any],
    odds: Mapping[str, Any] | None,
    policy: Policy = DEFAULT_POLICY,
) -> dict[str, Any] | None:
    """Choose at most one side, maximizing net EV among eligible sides."""
    candidates = evaluate_candidates(forecast, odds, policy)["candidates"]
    return candidates[0] if candidates else None


def _score(value: Any, name: str) -> int:
    if not _is_number(value) or value < 0 or int(value) != value:
        raise ValueError(f"{name} must be a nonnegative integer")
    return int(value)


def settle_candidate(
    candidate: Mapping[str, Any],
    home_goals: int,
    away_goals: int,
    cost_per_unit: float = 0.02,
) -> dict[str, Any]:
    """Settle exactly 1 unit, including the extra cost on wins and losses."""
    home = _score(home_goals, "home_goals")
    away = _score(away_goals, "away_goals")
    market, side_index = candidate["market"], candidate["side_index"]
    if market not in MARKETS or not isinstance(side_index, int) or isinstance(side_index, bool):
        raise ValueError("Invalid market or side")
    if not 0 <= side_index < len(SIDES[market]):
        raise ValueError("Invalid side index")
    if candidate.get("side") != SIDES[market][side_index]:
        raise ValueError("Side name and index disagree")
    odd = candidate["odd"]
    if not _is_number(odd) or odd <= 1:
        raise ValueError("Invalid settlement odd")
    if not _is_number(cost_per_unit) or cost_per_unit < 0:
        raise ValueError("Invalid cost")
    if market == "1x2":
        winner = 0 if home > away else 1 if home == away else 2
    elif market == "ou25":
        winner = 0 if home + away >= 3 else 1
    else:
        winner = 0 if home > 0 and away > 0 else 1
    won = side_index == winner
    gross = odd - 1.0 if won else -1.0
    return {"won": won, "stake_units": 1.0, "gross_profit_units": gross,
            "cost_units": cost_per_unit, "net_profit_units": gross - cost_per_unit}


def summarize(decisions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Account only for settled stakes, with zero included in the equity curve."""
    settled = [row for row in decisions if row["status"] == "SETTLED"]
    curve = [{"event_id": None, "cumulative_net_units": 0.0, "drawdown_units": 0.0}]
    cumulative = high_water = max_drawdown = 0.0
    for row in settled:
        cumulative = math.fsum((cumulative, row["settlement"]["net_profit_units"]))
        high_water = max(high_water, cumulative)
        drawdown = high_water - cumulative
        max_drawdown = max(max_drawdown, drawdown)
        curve.append({"event_id": row["id"], "cumulative_net_units": cumulative,
                      "drawdown_units": drawdown})
    stake = float(len(settled))
    gross = math.fsum(row["settlement"]["gross_profit_units"] for row in settled)
    cost = math.fsum(row["settlement"]["cost_units"] for row in settled)
    net = gross - cost
    wins = sum(row["settlement"]["won"] for row in settled)
    return {
        "events": len(decisions),
        "events_with_valid_market": sum(bool(row["valid_markets"]) for row in decisions),
        "selected_bets": sum(row["candidate"] is not None for row in decisions),
        "settled_bets": len(settled),
        "unsettled_bets": sum(row["status"] == "UNSETTLED" for row in decisions),
        "no_eligible_bet": sum(row["status"] == "NO_ELIGIBLE_BET" for row in decisions),
        "wins": wins,
        "losses": len(settled) - wins,
        "stake_units": stake,
        "gross_profit_units": gross,
        "cost_units": cost,
        "net_profit_units": net,
        "net_roi": net / stake if stake else None,
        "win_rate": wins / len(settled) if settled else None,
        "max_drawdown_units": max_drawdown,
        "minimum_cumulative_net_units": min(row["cumulative_net_units"] for row in curve),
        "curve": curve,
    }


def _event_sort_key(event: Mapping[str, Any]) -> tuple[Any, ...]:
    value = event.get("kickoff_at")
    if value is None:
        # Suitable only if actual kickoff timestamps are not supplied at all.
        return (1, event["round"], str(event["id"]))
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("kickoff_at must have an explicit timezone")
    return (0, parsed.astimezone(timezone.utc), str(event["id"]))


def run_replay(events: Sequence[Mapping[str, Any]], policy: Policy = DEFAULT_POLICY) -> dict[str, Any]:
    """Evaluate a supplied frozen cohort without fitting, tuning or bankroll stops.

    Every input event remains represented, including missing quotes and pending
    results. This is flat-stake counterfactual accounting, not an executable
    order history or a bankroll strategy. No outcome is required for selection.
    """
    ids = [str(event["id"]) for event in events]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate event ids")
    if events and any(event.get("kickoff_at") is not None for event in events) and any(
        event.get("kickoff_at") is None for event in events
    ):
        raise ValueError("Mixed known and missing kickoff timestamps prevents chronological drawdown")
    decisions = []
    for event in sorted(events, key=_event_sort_key):
        round_number = event["round"]
        if not isinstance(round_number, int) or isinstance(round_number, bool) or not 1 <= round_number <= 38:
            raise ValueError("Round must be an integer in [1,38]")
        if not isinstance(event.get("role"), str) or not event["role"]:
            raise ValueError("Event role is required")
        # Explicit projection ensures that selection never receives outcomes.
        forecast = {key: event.get(key) for key in ("p_1x2", "p_over25", "p_btts")}
        evaluated = evaluate_candidates(forecast, event.get("odds"), policy)
        candidate = evaluated["candidates"][0] if evaluated["candidates"] else None
        home, away = event.get("home_goals"), event.get("away_goals")
        if (home is None) != (away is None):
            raise ValueError("Match outcome must contain both scores or neither")
        if home is not None:
            _score(home, "home_goals")
            _score(away, "away_goals")
        settlement = None
        status = "NO_ELIGIBLE_BET"
        if candidate is not None:
            status = "UNSETTLED" if home is None else "SETTLED"
            if home is not None:
                settlement = settle_candidate(candidate, home, away, policy.cost_per_unit)
        decisions.append({
            "id": event["id"], "round": round_number, "role": event["role"],
            "kickoff_at": event.get("kickoff_at"),
            "candidate_frozen2025_hash": event.get("candidate_frozen2025_hash"),
            "valid_markets": evaluated["valid_markets"],
            "rejected_markets": evaluated["rejected_markets"],
            "eligible_sides": len(evaluated["candidates"]),
            "candidate": candidate, "status": status, "settlement": settlement,
        })
    roles = sorted({row["role"] for row in decisions})
    rounds = sorted({row["round"] for row in decisions})
    return {
        "accounting": "fixed_1_unit_per_selected_event_no_bankroll_stopping",
        "order": "kickoff_at_utc_then_id" if events and events[0].get("kickoff_at") else "round_then_id_assumed",
        "policy": asdict(policy),
        "overall": summarize(decisions),
        "by_role": {role: summarize([row for row in decisions if row["role"] == role]) for role in roles},
        "by_round": {str(r): summarize([row for row in decisions if row["round"] == r]) for r in rounds},
        "decisions": decisions,
    }
