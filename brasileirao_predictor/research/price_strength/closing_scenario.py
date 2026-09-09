"""Two-stage hypothetical closing-price replay; never an executable backtest.

Choice construction accepts prices only. Settlement accepts a separately frozen
choice set and reconciles principal, returned prizes, costs and locked capital.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

SIDES = ("away", "draw", "home")
COST = Decimal("0.02")
ONE = Decimal(1)


def odd(value: Any) -> Decimal | None:
    if not isinstance(value, str | int | float | Decimal) or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        return None
    return result if result.is_finite() and result > 1 else None


def freeze_choices(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """No labels accepted. Missing matches remain in the returned universe."""
    ids: set[str] = set()
    frozen = []
    for row in rows:
        if set(row) != {"event_id", "date", "offer", "reference"}:
            raise ValueError("price_stage_must_not_receive_labels_or_extra_fields")
        if row["event_id"] in ids:
            raise ValueError("duplicate_event_identity")
        ids.add(row["event_id"])
        if date.fromisoformat(row["date"]).year != 2025:
            raise ValueError("outside_frozen_2025_universe")
        item = {
            "event_id": row["event_id"],
            "date": row["date"],
            "selection": None,
            "status": "ABSTAIN",
            "execution_admitted": False,
        }
        vectors = {}
        for name in ("offer", "reference"):
            vector = row[name]
            vectors[name] = {side: odd(vector.get(side)) for side in SIDES} if isinstance(vector, dict) else {}
        if any(set(v) != set(SIDES) or any(p is None for p in v.values()) for v in vectors.values()):
            item["reason"] = "missing_or_invalid_individual_closing_prices"
            frozen.append(item)
            continue
        offer, reference = vectors["offer"], vectors["reference"]
        total = sum((ONE / reference[s] for s in SIDES), Decimal(0))
        if total <= 1:
            item["reason"] = "reference_sum_not_above_one"
            frozen.append(item)
            continue
        q = {s: ONE / reference[s] / total for s in SIDES}
        net = {s: q[s] * offer[s] - ONE - COST for s in SIDES}
        candidates = sorted((-ev, s) for s, ev in net.items() if 0 < ev <= Decimal("0.15"))
        item.update(
            reference_probabilities={s: str(q[s]) for s in SIDES},
            reference_sum=str(total),
            net_ev_by_side={s: str(net[s]) for s in SIDES},
        )
        if not candidates:
            item["reason"] = "no_price_difference_inside_frozen_threshold"
        else:
            neg_ev, side = candidates[0]
            item.update(
                status="CONDITIONAL_PICK",
                selection=side,
                decimal_odds=str(offer[side]),
                probability=str(q[side]),
                net_ev=str(-neg_ev),
                reason="conditional_close_price_difference",
            )
        frozen.append(item)
    return sorted(frozen, key=lambda r: (r["date"], r["event_id"]))


def label_winner(label: Any) -> str | None:
    if not isinstance(label, dict) or set(label) != {"home_goals", "away_goals", "result"}:
        return None
    goals = []
    for field in ("home_goals", "away_goals"):
        value = label[field]
        if not isinstance(value, str) or not value.isdecimal():
            return None
        goals.append(int(value))
    winner = "home" if goals[0] > goals[1] else "away" if goals[0] < goals[1] else "draw"
    return winner if label["result"] == {"home": "H", "away": "A", "draw": "D"}[winner] else None


def settle_frozen(frozen: list[dict[str, Any]], labels: dict[str, Any], bankroll: str = "100") -> dict[str, Any]:
    """Costs debited at commitment; unresolved results retain principal as locked."""
    initial = Decimal(bankroll)
    if not initial.is_finite() or initial <= 0:
        raise ValueError("invalid_initial_bankroll")
    ids = [r["event_id"] for r in frozen]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate_frozen_identity")
    cash, locked, stakes, prizes, costs = initial, Decimal(0), Decimal(0), Decimal(0), Decimal(0)
    maximum_exposure = Decimal(0)
    days: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen:
        days[row["date"]].append(row)
    events = []
    for day in sorted(days):
        accepted = []
        for row in sorted(days[day], key=lambda r: r["event_id"]):
            base = {"event_id": row["event_id"], "date": day, "conditional": True, "stake": "0"}
            if row["status"] != "CONDITIONAL_PICK":
                events.append({**base, "status": "ABSTAIN", "reason": row["reason"]})
                continue
            if row["selection"] not in SIDES or odd(row["decimal_odds"]) is None:
                raise ValueError("invalid_frozen_pick")
            if cash < ONE + COST:
                events.append({**base, "status": "ABSTAIN", "reason": "insufficient_scenario_bankroll"})
                continue
            cash -= ONE + COST
            locked += ONE
            stakes += ONE
            costs += COST
            accepted.append(row)
        maximum_exposure = max(maximum_exposure, locked)
        # Only after committing every stake of the day are its labels accessed.
        for row in accepted:
            winner = label_winner(labels.get(row["event_id"]))
            base = {
                "event_id": row["event_id"],
                "date": day,
                "conditional": True,
                "selection": row["selection"],
                "probability": row["probability"],
                "decimal_odds": row["decimal_odds"],
                "stake": "1",
                "cost": str(COST),
            }
            if winner is None:
                events.append(
                    {**base, "status": "UNSETTLED", "reason": "missing_or_conflicting_result", "net_pnl": None}
                )
                continue
            won = winner == row["selection"]
            returned = Decimal(row["decimal_odds"]) if won else Decimal(0)
            cash += returned
            locked -= ONE
            prizes += returned
            events.append(
                {
                    **base,
                    "status": "SETTLED",
                    "won": won,
                    "prize_including_principal": str(returned),
                    "net_pnl": str(returned - ONE - COST),
                }
            )
    settled = [r for r in events if r["status"] == "SETTLED"]
    pending = [r for r in events if r["status"] == "UNSETTLED"]
    net_realized = sum((Decimal(r["net_pnl"]) for r in settled), Decimal(0)) - COST * len(pending)
    equity = cash + locked
    if cash != initial - stakes - costs + prizes or equity != initial + net_realized:
        raise AssertionError("financial_reconciliation_failed")
    return {
        "status": "CONDITIONAL_NON_EXECUTABLE",
        "universe_n": len(frozen),
        "conditional_price_candidates": sum(r["status"] == "CONDITIONAL_PICK" for r in frozen),
        "conditional_bets": len(settled) + len(pending),
        "settled": len(settled),
        "unsettled": len(pending),
        "abstentions": sum(r["status"] == "ABSTAIN" for r in events),
        "initial_bankroll": str(initial),
        "contributions": "0",
        "total_stakes": str(stakes),
        "prizes_including_principal": str(prizes),
        "scenario_costs": str(costs),
        "final_cash": str(cash),
        "locked_principal": str(locked),
        "final_equity_at_cost": str(equity),
        "net_realized_pnl": str(net_realized),
        "roi_on_stakes": str(net_realized / stakes) if stakes and not pending else None,
        "return_on_bankroll": str(net_realized / initial) if not pending else None,
        "maximum_simultaneous_exposure_daily_scenario": str(maximum_exposure),
        "execution_proven": False,
        "actual_costs_known": False,
        "events": events,
    }
