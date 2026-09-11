"""Pure binary-back accounting; full fills and flat costs are declared scenarios.

Amounts are symbolic units, not authenticated money or accepted executions.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from numbers import Real
from typing import Any


def finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    try:
        value = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


def utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an aware ISO string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def binary_outcome(value: Any) -> int | None:
    if value is None:
        return None
    number = finite(value, "outcome")
    if number not in (0, 1):
        raise ValueError("outcome must be binary or explicitly unsettled (None)")
    return int(number)


def replay_shadow_portfolio(
    orders: list[dict[str, Any]], *, reference_bankroll: float = 100.0, as_of: str | None = None
) -> dict[str, Any]:
    """Reserve stake plus fees; release proceeds only at their settlement clock.

    Stake fractions refer to initial bankroll. Same-time orders are prioritized
    by event id, never by outcome. No credit, partial fill or cash top-ups.
    """
    initial = finite(reference_bankroll, "reference_bankroll")
    if initial <= 0:
        raise ValueError("reference_bankroll must be positive")
    cutoff = utc(as_of) if as_of is not None else None
    prepared, identities = [], set()
    for row in orders:
        event = row["event_id"]
        if not isinstance(event, str) or not event.strip() or event in identities:
            raise ValueError("orders require unique nonblank event_id")
        identities.add(event)
        decision = utc(row["predicted_at"])
        settled = utc(row["settled_at"]) if row.get("settled_at") is not None else None
        outcome = binary_outcome(row.get("outcome"))
        if (settled is None) != (outcome is None) or (settled is not None and settled <= decision):
            raise ValueError("invalid order settlement chronology")
        fraction = finite(row["stake_fraction"], "stake_fraction")
        odds, fee = finite(row["odds"], "odds"), finite(row["friction_rate"], "friction_rate")
        if fraction < 0 or odds <= 1 or not 0 <= fee < 1 or row["selection"] not in {"over", "under"}:
            raise ValueError("invalid binary-back order")
        prepared.append((decision, event, settled, outcome, fraction, odds, fee, row["selection"]))

    with localcontext() as context:
        context.prec = 50
        bank = Decimal(str(initial))
        cash = bank
        stakes = costs = returns = locked = peak_locked = Decimal(0)
        pending, receipts = [], []

        def release(at):
            nonlocal cash, returns, locked
            for position in sorted(pending[:], key=lambda item: (item[0] or datetime.max.replace(tzinfo=UTC), item[1])):
                settled, event, stake, payout = position
                if settled is not None and (at is None or settled <= at):
                    cash += payout
                    returns += payout
                    locked -= stake
                    pending.remove(position)
                    receipts.append(
                        {"event_id": event, "action": "SETTLED", "at": settled.isoformat(), "return": float(payout)}
                    )

        for decision, event, settled, outcome, fraction, odds, fee, side in sorted(prepared):
            if cutoff is not None and decision > cutoff:
                receipts.append({"event_id": event, "action": "AFTER_CUTOFF"})
                continue
            release(decision)
            stake = bank * Decimal(str(fraction))
            charge = stake * Decimal(str(fee))
            if stake == 0 or cash < stake + charge:
                receipts.append({"event_id": event, "action": "NO_CAPITAL" if stake else "NO_STAKE"})
                continue
            cash -= stake + charge
            stakes += stake
            costs += charge
            locked += stake
            peak_locked = max(peak_locked, locked)
            won = outcome is not None and ((outcome == 1) if side == "over" else (outcome == 0))
            payout = stake * Decimal(str(odds)) if won else Decimal(0)
            pending.append((settled, event, stake, payout))
            receipts.append(
                {
                    "event_id": event,
                    "action": "SIMULATED_FILL",
                    "at": decision.isoformat(),
                    "stake": float(stake),
                    "cost": float(charge),
                }
            )
        release(cutoff)
        pnl = returns - (stakes - locked) - costs
        if cash + locked != bank + pnl:
            raise ArithmeticError("portfolio cash reconciliation failed")
        for amount in (cash, locked, stakes, costs, returns, pnl, peak_locked):
            if not math.isfinite(float(amount)):
                raise ValueError("portfolio amounts must remain finite at the output boundary")
        return {
            "schema_version": "shadow-portfolio/v1",
            "execution_assumption": "hypothetical_full_fill_if_cash_available",
            "cost_scope": "caller_declared_flat_cost_per_staked_unit_only",
            "unit": "symbolic_reference_units",
            "stake_basis": "fraction_of_initial_reference_bankroll",
            "initial_bankroll": float(bank),
            "final_cash": float(cash),
            "open_stakes": float(locked),
            "total_stakes": float(stakes),
            "total_costs": float(costs),
            "returns_including_principal": float(returns),
            "net_pnl": float(pnl),
            "roi": float(pnl / stakes) if stakes and not pending else None,
            "return_on_bankroll": float(pnl / bank) if not pending else None,
            "maximum_simultaneous_stakes": float(peak_locked),
            "open_positions": len(pending),
            "receipts": receipts,
            "capital_enabled": False,
            "economic_evidence": False,
        }
