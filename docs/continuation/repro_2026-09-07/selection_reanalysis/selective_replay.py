"""Frozen exploratory selection replay. Never executes bets or touches runtime."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent
MARKETS = ("1x2", "ou25", "btts")


def dt(value):
    value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must include timezone")
    return value.astimezone(UTC)


def valid_odds(market, values, plan):
    size = 3 if market == "1x2" else 2
    if not isinstance(values, (list, tuple)) or len(values) != size:
        return False
    if any(v is None or isinstance(v, bool) for v in values):
        return False
    try:
        odds = np.asarray(values, dtype=float)
    except (TypeError, ValueError):
        return False
    lo, hi = plan["odds_gates"][market]
    if not np.all(np.isfinite(odds)) or np.any(odds < lo) or np.any(odds > hi):
        return False
    vlo, vhi = plan["odds_gates"]["complete_vector_overround"]
    return bool(vlo <= np.sum(1 / odds) <= vhi)


def validate_probabilities(values, size):
    p = np.asarray(values, dtype=float)
    if (
        p.shape != (size,)
        or not np.all(np.isfinite(p))
        or np.any(p < 0)
        or np.any(p > 1)
        or not np.isclose(np.sum(p), 1, atol=1e-8, rtol=0)
    ):
        raise ValueError("Invalid probability vector")
    return p


def label(result, market):
    home, away = result["home_goals"], result["away_goals"]
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in (home, away)):
        raise ValueError("Goals must be nonnegative integers")
    if market == "1x2":
        return 0 if home > away else 1 if home == away else 2
    if market == "ou25":
        return 0 if home + away >= 3 else 1
    return 0 if home > 0 and away > 0 else 1


def prepare_rows(events, forecasts, plan):
    if len({e["event_id"] for e in events}) != len(events):
        raise ValueError("Duplicate event id")
    for e in events:
        if not "2021-01-01" <= e["date"] <= "2025-12-31":
            raise ValueError("Forbidden input year")
        kickoff = dt(e["kickoff"])
        if not 2021 <= kickoff.year <= 2025:
            raise ValueError("Forbidden kickoff year")
        if abs((datetime.fromisoformat(e["date"]).date() - kickoff.date()).days) > 1:
            raise ValueError("Inconsistent event date and kickoff")
        label(e["result"], "1x2")  # Validate schema even when this event is not selected.
    predictions = {f["event_id"]: f for f in forecasts}
    if len(predictions) != len(forecasts):
        raise ValueError("Duplicate forecast id")
    rows = []
    coverage = Counter()
    for event in sorted(events, key=lambda e: (dt(e["kickoff"]), str(e["event_id"]))):
        f = predictions.get(event["event_id"])
        if f is None:
            coverage["no_forecast"] += 1
            continue
        decision = dt(event["kickoff"]) - timedelta(hours=plan["decision_before_kickoff_hours"])
        if dt(f["decision_at"]) != decision:
            raise ValueError("Forecast decision timestamp mismatch")
        cutoff = decision - timedelta(hours=plan["historical_result_buffer_hours"])
        if dt(f["training_cutoff_at"]) > cutoff:
            raise ValueError("Future model training")
        probs = {
            "1x2": validate_probabilities(f["p_1x2"], 3),
            "ou25": validate_probabilities([f["p_over25"], 1 - f["p_over25"]], 2),
            "btts": validate_probabilities([f["p_btts"], 1 - f["p_btts"]], 2),
        }
        markets = {}
        for market in MARKETS:
            if valid_odds(market, event["odds"].get(market), plan):
                odds = np.array(event["odds"][market], dtype=float)
                q = (1 / odds) / np.sum(1 / odds)
                markets[market] = {"p": probs[market], "q": q, "odds": odds}
                coverage[f"{event['date'][:4]}_{market}_valid"] += 1
            else:
                coverage[f"{event['date'][:4]}_{market}_invalid_or_missing"] += 1
        rows.append(
            {
                "event_id": event["event_id"],
                "date": event["date"],
                "kickoff": dt(event["kickoff"]),
                "decision": decision,
                "cutoff": cutoff,
                "markets": markets,
                "result": event["result"],
            }
        )
    return rows, dict(coverage)


def softmax(z):
    exp = np.exp(z - np.max(z, axis=-1, keepdims=True))
    return exp / np.sum(exp, axis=-1, keepdims=True)


def fit_calibration(history, cutoff, minimum=200):
    eligible = [r for r in history if r["kickoff"] < cutoff]
    fits = {}
    for market in MARKETS:
        sample = [r for r in eligible if market in r["markets"]]
        if len(sample) < minimum:
            fits[market] = {"n": len(sample), "status": "INSUFFICIENT_HISTORY"}
            continue
        p = np.array([r["markets"][market]["p"] for r in sample])
        q = np.array([r["markets"][market]["q"] for r in sample])
        target = np.array([label(r["result"], market) for r in sample])
        y = np.eye(p.shape[1])[target]
        diff = p - q
        denom = float(np.sum(diff**2))
        blend = float(np.clip(np.sum((y - q) * diff) / denom, 0, 1)) if denom > 1e-12 else 0.0
        logq = np.log(np.clip(q, 1e-8, 1))
        delta = np.log(np.clip(p, 1e-8, 1)) - logq
        classes = p.shape[1]

        def objective(theta):
            bias = np.r_[theta[1:], 0.0]
            pred = softmax(logq + theta[0] * delta + bias)
            loss = -np.mean(np.log(np.clip(pred[np.arange(len(target)), target], 1e-12, 1))) + 0.01 * np.sum(theta**2)
            residual = (pred - y) / len(target)
            grad = np.r_[np.sum(residual * delta), np.sum(residual, axis=0)[:-1]] + 0.02 * theta
            return float(loss), grad

        result = minimize(
            objective,
            np.zeros(classes),
            jac=True,
            method="L-BFGS-B",
            bounds=[(-1, 1)] + [(-0.35, 0.35)] * (classes - 1),
        )
        fits[market] = {
            "n": len(sample),
            "status": "OK" if result.success else "FIT_FAILED",
            "learned_blend": blend,
            "theta": result.x.tolist() if result.success else None,
            "loss": float(result.fun),
            "optimizer_message": str(result.message),
            "latest_training_kickoff": max(r["kickoff"] for r in sample).isoformat(),
            "cutoff": cutoff.isoformat(),
        }
    return fits


def corrected(p, q, fit):
    if fit.get("status") != "OK":
        return None
    theta = fit["theta"]
    logq = np.log(np.clip(q, 1e-8, 1))
    logits = logq + theta[0] * (np.log(np.clip(p, 1e-8, 1)) - logq) + np.r_[theta[1:], 0.0]
    return validate_probabilities(softmax(logits), len(p))


def choose(row, policy, fits, plan):
    if policy == "no_bet":
        return None
    candidates = []
    for market, data in sorted(row["markets"].items()):
        if policy.endswith("_only") and policy != f"residual_{market}_only":
            continue
        p, q, odds = data["p"], data["q"], data["odds"]
        if policy == "half_market_blend":
            prob = 0.5 * p + 0.5 * q
        elif policy == "learned_market_blend":
            fit = fits.get(market, {})
            if fit.get("status") != "OK":
                continue
            w = fit["learned_blend"]
            prob = w * p + (1 - w) * q
        elif policy in ("calibrated_residual", "conservative_residual") or policy.endswith("_only"):
            prob = corrected(p, q, fits.get(market, {}))
            if prob is None:
                continue
        else:
            prob = p
        for selection in range(len(prob)):
            probability = float(prob[selection])
            pessimistic = (
                max(0, probability - plan["conservative_probability_subtraction"])
                if policy == "conservative_residual"
                else probability
            )
            ev = pessimistic * float(odds[selection]) - 1 - plan["additional_cost_per_unit"]
            if policy.startswith("confidence_"):
                if probability < int(policy.split("_")[1]) / 100:
                    continue
                score = probability
            elif policy == "hash_placebo":
                digest = hashlib.sha256(
                    f"fixed-placebo-20260907:{row['event_id']}:{market}:{selection}".encode()
                ).digest()
                score = int.from_bytes(digest[:8], "big") / 2**64
            else:
                if ev < plan["net_ev_threshold"]:
                    continue
                score = ev
            candidates.append(
                {
                    "market": market,
                    "selection": selection,
                    "odds": float(odds[selection]),
                    "probability": probability,
                    "estimated_net_ev": ev,
                    "score": score,
                }
            )
    return min(candidates, key=lambda c: (-c["score"], c["market"], c["selection"])) if candidates else None


def run_decisions(rows, plan):
    decisions = []
    fits_log = []
    current_month = None
    fits = {}
    for row in rows:
        if row["decision"].year not in plan["decision_evaluation_years"]:
            continue
        month = row["decision"].strftime("%Y-%m")
        if month != current_month:
            fits = fit_calibration(rows, row["cutoff"], plan["calibration"]["min_games_per_market"])
            fits_log.append({"month": month, "decision": row["decision"].isoformat(), "fits": fits})
            current_month = month
        for policy in plan["policies"]:
            pick = choose(row, policy, fits, plan)
            result = {
                "event_id": row["event_id"],
                "date": row["date"],
                "decision_at": row["decision"].isoformat(),
                "policy": policy,
                "eligible_markets": sorted(row["markets"]),
                "pick": pick,
                "stake_units": 0,
                "pnl_units": 0.0,
            }
            if pick is not None:
                won = int(pick["selection"] == label(row["result"], pick["market"]))
                result.update(
                    {
                        "won": won,
                        "stake_units": 1,
                        "pnl_units": won * pick["odds"] - 1 - plan["additional_cost_per_unit"],
                    }
                )
            decisions.append(result)
    return decisions, fits_log


def stats(decisions):
    bets = [d for d in decisions if d["stake_units"]]
    profit = math.fsum(d["pnl_units"] for d in decisions)
    curve = np.r_[
        0, np.cumsum([d["pnl_units"] for d in sorted(decisions, key=lambda r: (r["decision_at"], str(r["event_id"])))])
    ]
    drawdown = float(np.max(np.maximum.accumulate(curve) - curve))
    return {
        "events": len(decisions),
        "bets": len(bets),
        "profit_units": profit,
        "roi": profit / len(bets) if bets else None,
        "hit_rate": sum(d["won"] for d in bets) / len(bets) if bets else None,
        "coverage": len(bets) / len(decisions) if decisions else None,
        "max_drawdown_units": drawdown,
        "by_market_bets": dict(Counter(d["pick"]["market"] for d in bets)),
    }


def bootstrap(decisions, plan):
    policies = plan["policies"]
    dates = [dt(d["decision_at"]) for d in decisions]
    start = min(dates).date()
    start -= timedelta(days=start.weekday())
    n_weeks = (max(dates).date() - start).days // 7 + 1
    profits = np.zeros((n_weeks, len(policies)))
    stakes = np.zeros_like(profits)
    for d in decisions:
        week = (dt(d["decision_at"]).date() - start).days // 7
        j = policies.index(d["policy"])
        profits[week, j] += d["pnl_units"]
        stakes[week, j] += d["stake_units"]
    rng = np.random.default_rng(plan["bootstrap"]["seed"])
    length = min(4, n_weeks)
    nblocks = math.ceil(n_weeks / length)
    starts = rng.integers(0, n_weeks - length + 1, size=(plan["bootstrap"]["replicates"], nblocks))
    indices = (starts[:, :, None] + np.arange(length)).reshape(len(starts), -1)[:, :n_weeks]
    p = profits[indices].sum(axis=1)
    n = stakes[indices].sum(axis=1)
    results = {}
    for j, policy in enumerate(policies):
        keep = n[:, j] > 0
        roi = p[keep, j] / n[keep, j]
        enough = stakes[:, j].sum() >= 30 and np.count_nonzero(stakes[:, j]) >= 8
        results[policy] = {
            "roi_ci95_descriptive": np.quantile(roi, [0.025, 0.975]).tolist() if len(roi) and enough else None,
            "ci_sample_guard": "at least 30 bets and 8 active calendar weeks",
            "resamples_with_bets": int(keep.sum()),
            "calendar_weeks": n_weeks,
            "active_weeks": int(np.count_nonzero(stakes[:, j])),
            "not_multiple_search_adjusted": True,
        }
    return results


def summarize(decisions, plan):
    boot = bootstrap(decisions, plan)
    outputs = {}
    common = {d["event_id"] for d in decisions if len(d["eligible_markets"]) == len(MARKETS)}
    for policy in plan["policies"]:
        subset = [d for d in decisions if d["policy"] == policy]
        all_stats = stats(subset) | boot[policy]
        years = {
            str(y): stats([d for d in subset if dt(d["decision_at"]).year == y])
            for y in plan["decision_evaluation_years"]
        }
        stress = []
        bets = [d for d in subset if d["stake_units"]]
        for cost in plan["stress"]["additional_cost_rates"]:
            for reduction in plan["stress"]["proportional_odds_reduction"]:
                profit = math.fsum(d["won"] * max(1, d["pick"]["odds"] * (1 - reduction)) - 1 - cost for d in bets)
                stress.append(
                    {
                        "additional_cost": cost,
                        "odds_reduction": reduction,
                        "profit_units": profit,
                        "roi": profit / len(bets) if bets else None,
                    }
                )
        largest = sorted([d["pnl_units"] for d in bets if d["pnl_units"] > 0], reverse=True)[:5]
        outputs[policy] = {
            "overall": all_stats,
            "by_year": years,
            "common_three_market_panel": stats([d for d in subset if d["event_id"] in common]),
            "stress_fixed_decisions_no_reselection": stress,
            "profit_after_removing_up_to_5_largest_wins": all_stats["profit_units"] - sum(largest),
        }
    return outputs


def main():
    plan_raw = (ROOT / "analysis_plan.json").read_bytes()
    plan = json.loads(plan_raw)
    input_raw = (ROOT / "historical_input.json").read_bytes()
    manifest = json.loads((ROOT / "input_manifest.json").read_text())
    assert hashlib.sha256(plan_raw).hexdigest() == manifest["plan_sha256"]
    assert hashlib.sha256(input_raw).hexdigest() == manifest["input_sha256"]
    forecast_path = ROOT / "forecasts.json"
    forecasts = json.loads(forecast_path.read_text(encoding="utf-8"))
    rows, coverage = prepare_rows(json.loads(input_raw), forecasts, plan)
    decisions, fits = run_decisions(rows, plan)
    summary = {
        "mode": plan["mode"],
        "analysis_id": plan["id"],
        "plan_sha256": manifest["plan_sha256"],
        "input_sha256": manifest["input_sha256"],
        "forecasts_sha256": hashlib.sha256(forecast_path.read_bytes()).hexdigest(),
        "selector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "coverage": coverage,
        "policies": summarize(decisions, plan),
        "limitations": plan["limitations"],
        "capital_enabled": False,
        "confirmation": False,
    }
    (ROOT / "selection_decisions.jsonl").write_text(
        "".join(json.dumps(d, ensure_ascii=False, allow_nan=False) + "\n" for d in decisions), encoding="utf-8"
    )
    (ROOT / "calibration_fits.json").write_text(
        json.dumps(fits, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (ROOT / "selection_results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({policy: value["overall"] for policy, value in summary["policies"].items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
