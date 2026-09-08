"""Independent arithmetic audit for the frozen 2026 split replay.

The auditor deliberately does not import the selection/accounting module.
It derives decisions from input probabilities and prices, then compares every
decision and aggregate. Settlement arithmetic uses Decimal(str(quote)).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

FROZEN_PLAN_SHA256 = "5561ed31a36945d40e5ffe258dea5f07d890a8f677f57e463ccdb875e3d45f20"
ARM_NAMES = {"primary_calibrated", "diagnostic_raw"}
MARKET_ORDER = ["1x2", "ou25", "btts"]
SIDE_NAMES = [["home", "draw", "away"], ["over", "under"], ["yes", "no"]]


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def chronology(event):
    if event.get("kickoff_at") is None:
        return (1, event["round"], str(event["id"]))
    when = datetime.fromisoformat(event["kickoff_at"].replace("Z", "+00:00"))
    if when.tzinfo is None:
        raise ValueError("Naive kickoff timestamp")
    return (0, when.astimezone(timezone.utc), str(event["id"]))


def independent_decision(event, plan):
    rules = plan["selection"]
    cost = plan["accounting"]["extra_cost_units_per_bet"]
    valid_markets, rejected, eligible = [], {}, []
    for market_index, market in enumerate(MARKET_ORDER):
        if market_index == 0:
            probabilities = event.get("p_1x2")
            if not isinstance(probabilities, (tuple, list)) or len(probabilities) != 3:
                rejected[market] = "missing_or_incomplete_probability_vector"
                continue
            if any(not number(p) or p < 0 or p > 1 for p in probabilities):
                rejected[market] = "invalid_probability"
                continue
            if abs(sum(probabilities) - 1) > 1e-6:
                rejected[market] = "probability_vector_does_not_sum_to_one"
                continue
        else:
            probability = event.get("p_over25" if market_index == 1 else "p_btts")
            if probability is None:
                rejected[market] = "missing_probability"
                continue
            if not number(probability) or probability < 0 or probability > 1:
                rejected[market] = "invalid_probability"
                continue
            probabilities = [probability, 1 - probability]
        quotes = (event.get("odds") or {}).get(market)
        if not isinstance(quotes, (tuple, list)) or len(quotes) != len(SIDE_NAMES[market_index]):
            rejected[market] = "missing_or_incomplete_quote_vector"
            continue
        lower, upper = rules["odds_bounds_inclusive"][market]
        if any(not number(o) or o < lower or o > upper for o in quotes):
            rejected[market] = "invalid_or_out_of_range_quote"
            continue
        booksum = sum(1 / odd for odd in quotes)
        lower_sum, upper_sum = rules["overround_inclusive"]
        if booksum < lower_sum - 1e-12 or booksum > upper_sum + 1e-12:
            rejected[market] = "overround_out_of_range"
            continue
        valid_markets.append(market)
        for side, (probability, odd) in enumerate(zip(probabilities, quotes)):
            edge = probability - 1 / odd
            net_ev = probability * odd - 1 - cost
            if edge <= rules["min_edge_exclusive"] + 1e-12:
                continue
            if edge > rules["max_edge_inclusive"] + 1e-12 or net_ev <= 0:
                continue
            eligible.append({
                "market": market, "side": SIDE_NAMES[market_index][side], "side_index": side,
                "probability": probability, "odd": odd, "implied_probability": 1 / odd,
                "edge": edge, "predicted_net_ev": net_ev, "overround": booksum,
            })
    chosen = min(eligible, key=lambda row: (-row["predicted_net_ev"], MARKET_ORDER.index(row["market"]), row["side_index"])) if eligible else None
    settlement, status = None, "NO_ELIGIBLE_BET"
    if chosen:
        if event.get("home_goals") is None and event.get("away_goals") is None:
            status = "UNSETTLED"
        else:
            home, away = event["home_goals"], event["away_goals"]
            if not all(number(score) and score >= 0 and int(score) == score for score in (home, away)):
                raise ValueError("Invalid score supplied to audit")
            outcomes = {
                "home": home > away, "draw": home == away, "away": home < away,
                "over": home + away > 2.5, "under": home + away < 2.5,
                "yes": home >= 1 and away >= 1, "no": home == 0 or away == 0,
            }
            won = outcomes[chosen["side"]]
            gross = Decimal(str(chosen["odd"])) - 1 if won else Decimal(-1)
            charge = Decimal(str(cost))
            settlement = {"won": won, "stake_units": 1.0, "gross_profit_units": float(gross),
                          "cost_units": cost, "net_profit_units": float(gross - charge)}
            status = "SETTLED"
    return {
        "id": event["id"], "round": event["round"], "role": event["role"],
        "kickoff_at": event.get("kickoff_at"),
        "candidate_frozen2025_hash": event.get("candidate_frozen2025_hash"),
        "valid_markets": valid_markets, "rejected_markets": rejected,
        "eligible_sides": len(eligible), "candidate": chosen, "status": status,
        "settlement": settlement,
    }


def independent_summary(decisions, plan):
    rows = [row for row in decisions if row["status"] == "SETTLED"]
    cumulative = peak = maximum_drawdown = Decimal(0)
    curve = [{"event_id": None, "cumulative_net_units": 0.0, "drawdown_units": 0.0}]
    gross = Decimal(0)
    for row in rows:
        payment = row["settlement"]
        gross += Decimal(str(payment["gross_profit_units"]))
        cumulative += Decimal(str(payment["net_profit_units"]))
        peak = max(peak, cumulative)
        drawdown = peak - cumulative
        maximum_drawdown = max(maximum_drawdown, drawdown)
        curve.append({"event_id": row["id"], "cumulative_net_units": float(cumulative), "drawdown_units": float(drawdown)})
    cost = Decimal(str(plan["accounting"]["extra_cost_units_per_bet"])) * len(rows)
    net = gross - cost
    wins = sum(row["settlement"]["won"] for row in rows)
    return {
        "events": len(decisions),
        "events_with_valid_market": sum(len(row["valid_markets"]) > 0 for row in decisions),
        "selected_bets": sum(row["candidate"] is not None for row in decisions),
        "settled_bets": len(rows),
        "unsettled_bets": sum(row["status"] == "UNSETTLED" for row in decisions),
        "no_eligible_bet": sum(row["status"] == "NO_ELIGIBLE_BET" for row in decisions),
        "wins": wins, "losses": len(rows) - wins, "stake_units": float(len(rows)),
        "gross_profit_units": float(gross), "cost_units": float(cost), "net_profit_units": float(net),
        "net_roi": float(net / len(rows)) if rows else None,
        "win_rate": wins / len(rows) if rows else None,
        "max_drawdown_units": float(maximum_drawdown),
        "minimum_cumulative_net_units": min(row["cumulative_net_units"] for row in curve),
        "curve": curve,
    }


def illustration(summary, plan):
    stake = Decimal(str(plan["accounting"]["illustration_stake_brl"]))
    initial = Decimal(str(plan["accounting"]["illustration_initial_bankroll_brl"]))
    # Arithmetic only; no retroactive bankroll stop or unobserved execution.
    net = Decimal(str(summary["net_profit_units"])) * stake
    minimum = Decimal(str(summary["minimum_cumulative_net_units"])) * stake
    total_debit = stake * (1 + Decimal(str(plan["accounting"]["extra_cost_units_per_bet"])))
    deficient = [point["event_id"] for point in summary["curve"][:-1]
                 if initial + Decimal(str(point["cumulative_net_units"])) * stake < total_debit]
    return {
        "fixed_stake_brl": float(stake), "initial_bankroll_brl": float(initial),
        "turnover_brl": float(Decimal(str(summary["stake_units"])) * stake),
        "gross_profit_brl": float(Decimal(str(summary["gross_profit_units"])) * stake),
        "cost_brl": float(Decimal(str(summary["cost_units"])) * stake),
        "net_profit_brl": float(net), "final_bankroll_brl": float(initial + net),
        "max_drawdown_brl": float(Decimal(str(summary["max_drawdown_units"])) * stake),
        "minimum_bankroll_brl": float(initial + minimum),
        "negative_balance_on_settled_curve": initial + minimum < 0,
        "insufficient_for_next_flat_stake_on_settled_curve": bool(deficient),
        "limitations": "Linear illustration; ignores simultaneous open exposure and actual settlement timing; no bankroll stopping.",
    }


def compare(expected: Any, actual: Any, path: str, errors: list[str]):
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            errors.append(f"{path}: expected object")
            return
        for key, value in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key}: missing")
            else:
                compare(value, actual[key], f"{path}.{key}", errors)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            errors.append(f"{path}: sequence length/type differs")
            return
        for index, (left, right) in enumerate(zip(expected, actual)):
            compare(left, right, f"{path}[{index}]", errors)
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if type(expected) is not type(actual) or expected != actual:
            errors.append(f"{path}: expected {expected!r}, got {actual!r}")
    elif number(expected):
        if not number(actual) or not math.isclose(expected, actual, rel_tol=1e-10, abs_tol=1e-9):
            errors.append(f"{path}: expected {expected!r}, got {actual!r}")
    elif expected != actual:
        errors.append(f"{path}: mismatch")


def audit_payloads(inputs, results, plan, *, enforce_full_cohort=True):
    errors, audited = [], {}
    arms = results.get("arms", {})
    if set(inputs) != ARM_NAMES or set(arms) != ARM_NAMES:
        errors.append("The two predefined arms must occur exactly once in both files")
    reference_inputs = None
    for arm in sorted(ARM_NAMES):
        events, actual = inputs.get(arm, []), arms.get(arm, {})
        if len({str(event["id"]) for event in events}) != len(events):
            errors.append(f"{arm}: duplicate event ids")
        round_counts = Counter(event["round"] for event in events)
        turn_counts = {"first_turn": sum(1 <= event["round"] <= 19 for event in events),
                       "second_turn": sum(20 <= event["round"] <= 38 for event in events)}
        if enforce_full_cohort:
            if len(events) != 380 or turn_counts != {"first_turn": 190, "second_turn": 190}:
                errors.append(f"{arm}: official denominator is not 380 total / 190 per turn")
            if round_counts != Counter({r: 10 for r in range(1, 39)}):
                errors.append(f"{arm}: each official round must contain exactly 10 fixtures")
        role_rounds = {}
        for event in events:
            role_rounds.setdefault(event["role"], set()).add(1 if event["round"] <= 19 else 2)
        if any(len(turns) != 1 for turns in role_rounds.values()):
            errors.append(f"{arm}: a role crosses the first/second turn boundary")
        if enforce_full_cohort and (
            len(role_rounds) != 2 or any(count != 190 for count in Counter(event["role"] for event in events).values())
        ):
            errors.append(f"{arm}: exactly two roles with 190 fixtures each are required")
        common = {str(event["id"]): {key: event.get(key) for key in (
            "id", "round", "role", "kickoff_at", "odds", "home_goals", "away_goals"
        )} for event in events}
        if reference_inputs is None:
            reference_inputs = common
        elif common != reference_inputs:
            errors.append("Arm input fixture metadata, quotes or outcomes differ")
        ordered = sorted(events, key=chronology)
        expected_decisions = [independent_decision(event, plan) for event in ordered]
        overall = independent_summary(expected_decisions, plan)
        role_summaries = {role: independent_summary([row for row in expected_decisions if row["role"] == role], plan)
                          for role in sorted(role_rounds)}
        round_summaries = {str(r): independent_summary([row for row in expected_decisions if row["round"] == r], plan)
                           for r in sorted(round_counts)}
        expected = {
            "accounting": "fixed_1_unit_per_selected_event_no_bankroll_stopping",
            "order": "kickoff_at_utc_then_id" if events and events[0].get("kickoff_at") else "round_then_id_assumed",
            "policy": {"min_edge": plan["selection"]["min_edge_exclusive"],
                       "max_edge": plan["selection"]["max_edge_inclusive"],
                       "cost_per_unit": plan["accounting"]["extra_cost_units_per_bet"],
                       "min_overround": plan["selection"]["overround_inclusive"][0],
                       "max_overround": plan["selection"]["overround_inclusive"][1]},
            "overall": overall, "by_role": role_summaries,
            "by_round": round_summaries, "decisions": expected_decisions,
        }
        compare(expected, actual, arm, errors)
        audited[arm] = {
            "event_count": len(events), "turn_counts": turn_counts,
            "overall": {key: value for key, value in overall.items() if key != "curve"},
            "by_role": {role: {key: value for key, value in summary.items() if key != "curve"}
                        for role, summary in role_summaries.items()},
            "illustration_brl": {"overall": illustration(overall, plan),
                                  "by_role": {role: illustration(summary, plan) for role, summary in role_summaries.items()}},
            "decisions_compared": len(expected_decisions),
        }
    return {"status": "PASS" if not errors else "FAIL", "error_count": len(errors), "errors": errors,
            "enforced_full_official_cohort": enforce_full_cohort, "audited": audited,
            "method": "Independent probability/quote selection and Decimal settlement; does not import economics.py"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--plan", type=Path, help="Frozen plan path when it is outside the result directory")
    args = parser.parse_args()
    paths = {name: args.directory / name for name in ("plan.json", "replay_inputs.json", "results.json")}
    if args.plan is not None:
        paths["plan.json"] = args.plan
    raw = {name: path.read_bytes() for name, path in paths.items()}
    if hashlib.sha256(raw["plan.json"]).hexdigest() != FROZEN_PLAN_SHA256:
        raise SystemExit("Frozen plan hash mismatch; refusing to audit a changed specification")
    payloads = {name: json.loads(content) for name, content in raw.items()}
    report = audit_payloads(payloads["replay_inputs.json"], payloads["results.json"], payloads["plan.json"])
    report["source_sha256"] = {name: hashlib.sha256(content).hexdigest() for name, content in raw.items()}
    report["auditor_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    output = args.directory / "audit_results.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "error_count": report["error_count"], "output": str(output)}, ensure_ascii=False))
    if report["errors"]:
        print("\n".join(report["errors"][:25]))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
