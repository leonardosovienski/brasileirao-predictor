"""Independent arithmetic audit of the frozen 2025 diagnostic exports.

Only reads the explicitly frozen copies and this study's output files. Does
not import its evaluator, model, legacy selection or settlement functions.
NumPy supplies the declared bootstrap RNG only; losses, selection, settlement,
aggregation, resampling weights and quantiles are recomputed here.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parents[1] / "outputs" / "TESTE_XG_REAL"
PLAN_SHA = "507c69fc01aaabd9d78734b1153f740c3c347f601f5b1609cd54839a1698aaaa"
ARMS = ("xg_calibrated_primary", "xg_raw_diagnostic", "old_raw_frozen_2024", "market_proportional_devig")
SIDES = {"1x2": ("home", "draw", "away"), "ou25": ("over", "under"), "btts": ("yes", "no")}
BOUNDS = {"1x2": (1.05, 20.0), "ou25": (1.2, 5.0), "btts": (1.2, 5.0)}
COST = 0.02


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class Auditor:
    def __init__(self):
        self.checks = 0

    def require(self, condition, name):
        self.checks += 1
        if not condition:
            raise AssertionError(name)

    def equal(self, expected, actual, name):
        if isinstance(expected, dict):
            self.require(isinstance(actual, dict) and set(expected) == set(actual), name + ":keys")
            for key, value in expected.items():
                self.equal(value, actual[key], f"{name}.{key}")
        elif isinstance(expected, (list, tuple)):
            self.require(isinstance(actual, (list, tuple)) and len(expected) == len(actual), name + ":length")
            for index, (left, right) in enumerate(zip(expected, actual)):
                self.equal(left, right, f"{name}[{index}]")
        elif isinstance(expected, float):
            self.require(type(actual) in (int, float) and math.isfinite(actual), name + ":finite_number")
            self.require(math.isclose(expected, actual, rel_tol=1e-10, abs_tol=1e-10), name + ":value")
        else:
            self.require(type(actual) is type(expected) and expected == actual, name + ":exact")


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise AssertionError("Naive timestamp in exported source")
    return parsed.astimezone(UTC)


def old_distribution(source):
    three = source["p_1x2"]
    if isinstance(three, dict):
        three = [three[side] for side in SIDES["1x2"]]
    return {
        "1x2": dict(zip(SIDES["1x2"], three, strict=True)),
        "ou25": {"over": source["p_over25"], "under": 1 - source["p_over25"]},
        "btts": {"yes": source["p_btts"], "no": 1 - source["p_btts"]},
    }


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def valid_market(probabilities, prices, market):
    sides = SIDES[market]
    if set(probabilities.get(market, {})) != set(sides):
        return False
    values = [probabilities[market][side] for side in sides]
    if not all(finite(p) and 0 <= p <= 1 for p in values):
        return False
    if not math.isclose(sum(values), 1, abs_tol=1e-6, rel_tol=0):
        return False
    quotes = prices.get(market)
    if not isinstance(quotes, (list, tuple)) or len(quotes) != len(sides):
        return False
    low, high = BOUNDS[market]
    if not all(finite(odd) and low <= odd <= high for odd in quotes):
        return False
    margin = sum(1 / odd for odd in quotes)
    return 1 - 1e-12 <= margin <= 1.3 + 1e-12


def independent_choice(probabilities, prices):
    possible = []
    for market_position, (market, sides) in enumerate(SIDES.items()):
        if not valid_market(probabilities, prices, market):
            continue
        margin = sum(1 / odd for odd in prices[market])
        for side_position, side in enumerate(sides):
            p = probabilities[market][side]
            odd = prices[market][side_position]
            advantage = p - 1 / odd
            net_ev = p * odd - 1 - COST
            if advantage <= 0.02 + 1e-12 or advantage > 0.15 + 1e-12 or net_ev <= 0:
                continue
            possible.append(((-net_ev, market_position, side_position), {
                "market": market, "side": side, "side_index": side_position,
                "probability": p, "odd": odd, "implied_probability": 1 / odd,
                "edge": advantage, "predicted_net_ev": net_ev, "overround": margin,
            }))
    return min(possible, key=lambda entry: entry[0])[1] if possible else None


def winners(home, away):
    if type(home) is not int or type(away) is not int or min(home, away) < 0:
        raise AssertionError("Outcome is not a pair of nonnegative integer scores")
    return {
        "1x2": "draw" if home == away else "home" if home > away else "away",
        "ou25": "over" if home + away > 2.5 else "under",
        "btts": "yes" if min(home, away) > 0 else "no",
    }


def settle(choice, actual):
    if choice is None:
        return None
    win = actual[choice["market"]] == choice["side"]
    payout = choice["odd"] if win else 0.0
    return {"won": win, "stake_units": 1.0, "gross_profit_units": payout - 1,
            "cost_units": COST, "net_profit_units": payout - 1 - COST}


def score(probabilities, actual, auditor):
    answer = {}
    auditor.equal(set(SIDES), set(probabilities), "probability_markets")
    for market, sides in SIDES.items():
        vector = probabilities[market]
        auditor.require(set(vector) == set(sides), f"{market}:complete_sides")
        auditor.require(all(finite(value) and 0 <= value <= 1 for value in vector.values()), f"{market}:probability_range")
        auditor.require(math.isclose(sum(vector.values()), 1, abs_tol=1e-9), f"{market}:normalized")
        positive_sides = sides if market == "1x2" else sides[:1]
        brier = sum((vector[side] - (1 if actual[market] == side else 0)) ** 2 for side in positive_sides)
        answer[market] = {"brier": brier, "log_loss": -math.log(max(vector[actual[market]], 1e-15))}
    return answer


def economics(rows, arm):
    taken = [row["bets"][arm] for row in rows if row["bets"][arm] is not None]
    gross = sum(bet["settlement"]["gross_profit_units"] for bet in taken)
    net = gross - len(taken) * COST
    wins = sum(bet["settlement"]["won"] for bet in taken)
    cumulative, high, maximum_drawdown = 0.0, 0.0, 0.0
    for row in rows:
        bet = row["bets"][arm]
        cumulative += bet["settlement"]["net_profit_units"] if bet else 0
        high = max(high, cumulative)
        maximum_drawdown = max(maximum_drawdown, high - cumulative)
    return {"fixtures": len(rows), "bets": len(taken), "wins": wins, "losses": len(taken) - wins,
            "stake_units": len(taken), "gross_profit_units": float(gross), "cost_units": COST * len(taken),
            "net_profit_units": float(net), "net_roi": net / len(taken) if taken else None,
            "net_profit_per_fixture": net / len(rows) if rows else None, "max_drawdown_units": maximum_drawdown}


def quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    left = math.floor(position)
    right = math.ceil(position)
    return ordered[left] + (ordered[right] - ordered[left]) * (position - left)


def audit_bootstrap(rows, published, auditor):
    if not rows:
        auditor.equal({"week_count": 0, "probabilistic": {}, "economics": {}}, published, "bootstrap.empty")
        return
    import numpy as np

    keys = [tuple(timestamp(row["kickoff"]).isocalendar()[:2]) for row in rows]
    calendar = sorted(set(keys))
    groups = [[i for i, key in enumerate(keys) if key == week] for week in calendar]
    rng = np.random.default_rng(20260907)
    draws = rng.integers(0, len(groups), size=(2000, len(groups)))
    # Multiplicity weights are computed independently; no array indexing of totals.
    weights = [Counter(int(index) for index in draw) for draw in draws]

    def confidence(values):
        totals = [sum(values[index] for index in group) for group in groups]
        samples = [sum(totals[index] * count for index, count in weight.items())
                   / sum(len(groups[index]) * count for index, count in weight.items()) for weight in weights]
        return [quantile(samples, 0.025), quantile(samples, 0.975)]

    auditor.equal(len(groups), published["week_count"], "bootstrap.week_count")
    auditor.equal(2000, published["replicates"], "bootstrap.replicates")
    auditor.equal(20260907, published["seed"], "bootstrap.seed")
    for candidate in ARMS[:2]:
        for baseline in ARMS[2:]:
            for market in SIDES:
                for metric in ("brier", "log_loss"):
                    differences = [row["scores"][candidate][market][metric] - row["scores"][baseline][market][metric]
                                   for row in rows]
                    expected = {"mean_delta": sum(differences) / len(rows),
                                "ci95_weekly_descriptive": confidence(differences)}
                    auditor.equal(expected, published["probabilistic"][candidate][baseline][market][metric],
                                  f"bootstrap.{candidate}.{baseline}.{market}.{metric}")
            differences = []
            for row in rows:
                left, right = row["bets"][candidate], row["bets"][baseline]
                differences.append((left["settlement"]["net_profit_units"] if left else 0)
                                   - (right["settlement"]["net_profit_units"] if right else 0))
            auditor.equal({"delta_profit_per_fixture": sum(differences) / len(rows),
                           "ci95_weekly_descriptive": confidence(differences)},
                          published["economics"][candidate][baseline], f"bootstrap.economics.{candidate}.{baseline}")


def audit(auditor):
    for path in (HERE / "plan.json", OUTPUT / "PLANO.json"):
        auditor.equal(PLAN_SHA, digest(path), f"hash:{path.name}")
    plan = read(HERE / "plan.json")
    for name, metadata in plan["source_files"].items():
        auditor.require(Path(name).name == name, "source_must_be_local_basename")
        auditor.equal(metadata["sha256"], digest(HERE / "inputs" / name), f"input_hash:{name}")
    auditor.equal(plan["frozen_accounting_sha256"], digest(HERE / "frozen_economics.py"), "frozen_accounting_hash")
    manifest = read(OUTPUT / "MANIFEST.json")
    auditor.equal(PLAN_SHA, manifest["plan_sha256"], "manifest.plan")
    for name, expected in manifest["files"].items():
        auditor.require(Path(name).name == name, "manifest_must_be_local_basename")
        auditor.equal(expected, digest(OUTPUT / name), f"export_hash:{name}")
    execution = read(OUTPUT / "EXECUTION_LOCK.json")
    for name, expected in execution["sources"].items():
        auditor.require(Path(name).name == name, "locked_source_must_be_basename")
        auditor.equal(expected, digest(HERE / name), f"locked_code_hash:{name}")
    auditor.equal(False, execution["evaluation_scores_computed"], "execution_before_scores")
    lock = read(OUTPUT / "FORECAST_LOCK.json")
    auditor.equal(False, lock["evaluation_scores_computed"], "forecast_before_scores")
    for name in ("forecasts", "panel"):
        auditor.equal(lock[f"{name}_sha256"], digest(OUTPUT / f"{name}.json"), f"forecast_lock:{name}")
    results = read(OUTPUT / "results.json")
    rows = read(OUTPUT / "event_results.json")
    panel = read(OUTPUT / "panel.json")
    forecasts = read(OUTPUT / "forecasts.json")
    history = read(HERE / "inputs" / "history.json")
    baseline = read(HERE / "inputs" / "baseline_2025.json")
    auditor.equal(PLAN_SHA, results["plan_sha256"], "results.plan")
    auditor.equal(plan["candidate_config"], results["candidate_config"], "results.config")
    auditor.equal(execution["candidate_fingerprint"], results["config_fingerprint"], "config_fingerprint")
    auditor.equal(plan["availability_policy"], results["availability_policy"], "availability_label")
    for name in ("execution_proven", "profitability_established", "real_capital_enabled"):
        auditor.equal(False, results[name], f"research_gate:{name}")
    auditor.equal(plan["cross_book_comparison"], results["cross_book_comparison"], "no_cross_book_inference")
    targets = sorted((row for row in history if timestamp(row["kickoff"]).year == 2025),
                     key=lambda row: (timestamp(row["kickoff"]), str(row["event_id"])))
    ids = [str(row["event_id"]) for row in targets]
    auditor.equal(380, len(ids), "fixed_universe_count")
    auditor.equal(len(ids), len(set(ids)), "unique_target_ids")
    auditor.equal(ids, [row["event_id"] for row in plan["evaluation_fixtures"]], "fixed_fixture_order")
    auditor.equal(ids, [row["event_id"] for row in panel], "panel_covers_whole_universe")
    auditor.equal(ids, [row["event_id"] for row in forecasts], "forecasts_cover_whole_universe")
    baseline_by_id = {str(row["event_id"]): old_distribution(row) for row in baseline}
    auditor.equal(len(baseline), len(baseline_by_id), "unique_old_baseline_ids")
    included, all_reasons = [], Counter()
    expected_rows = []
    actual_rows = {row["event_id"]: row for row in rows}
    auditor.equal(len(rows), len(actual_rows), "unique_common_panel_ids")
    for target, prediction, panel_row, fixture in zip(targets, forecasts, panel, plan["evaluation_fixtures"], strict=True):
        identifier = str(target["event_id"])
        for name in ("home", "away", "kickoff"):
            auditor.equal(target[name], fixture[name], f"fixed_fixture:{identifier}:{name}")
        auditor.equal(target["kickoff"], prediction["kickoff"], f"forecast_kickoff:{identifier}")
        auditor.equal(plan["availability_policy"], prediction["availability_policy"], f"forecast_availability:{identifier}")
        old = baseline_by_id.get(identifier)
        auditor.equal(old, prediction["baseline"], f"old_probabilities_in_forecast:{identifier}")
        reasons = []
        for key in ("raw", "calibrated"):
            auditor.require(type(prediction[key]["eligible"]) is bool, f"eligibility_boolean:{identifier}:{key}")
            if not prediction[key]["eligible"]:
                reasons.append(key + ":" + prediction[key]["reason"])
        if old is None:
            reasons.append("missing_old_baseline")
        elif not all(valid_market(old, target["odds"], market) for market in SIDES):
            reasons.append("incomplete_or_invalid_prices")
        auditor.equal({"event_id": identifier, "included": not reasons, "reasons": reasons},
                      panel_row, f"panel_eligibility:{identifier}")
        all_reasons.update(reasons)
        if reasons:
            auditor.require(identifier not in actual_rows, f"excluded_fixture_not_scored:{identifier}")
            continue
        included.append(identifier)
        row = actual_rows[identifier]
        for name in ("home", "away", "kickoff", "odds"):
            auditor.equal(target[name], row[name], f"source_reconciliation:{identifier}:{name}")
        outcome = {name: target["result"][name] for name in ("home_goals", "away_goals")}
        auditor.equal(outcome, row["outcome"], f"source_outcome:{identifier}")
        true_sides = winners(**{"home": outcome["home_goals"], "away": outcome["away_goals"]})
        market = {}
        for name, sides in SIDES.items():
            total = sum(1 / odd for odd in row["odds"][name])
            market[name] = {side: 1 / odd / total for side, odd in zip(sides, row["odds"][name], strict=True)}
        probabilities = dict(zip(ARMS, [prediction["calibrated"]["probabilities"], prediction["raw"]["probabilities"],
                                       old, market], strict=True))
        auditor.equal(probabilities, row["probabilities"], f"frozen_forecast_reconciliation:{identifier}")
        computed_scores, computed_bets = {}, {}
        for arm in ARMS:
            computed_scores[arm] = score(probabilities[arm], true_sides, auditor)
            chosen = independent_choice(probabilities[arm], row["odds"])
            computed_bets[arm] = {"candidate": chosen, "settlement": settle(chosen, true_sides)} if chosen else None
        auditor.equal(computed_scores, row["scores"], f"independent_losses:{identifier}")
        auditor.equal(computed_bets, row["bets"], f"independent_selection_and_payout:{identifier}")
        expected_rows.append({"event_id": identifier, "kickoff": row["kickoff"],
                              "scores": computed_scores, "bets": computed_bets})
    auditor.equal(included, [row["event_id"] for row in rows], "common_panel_chronological_order")
    auditor.equal({"universe": len(ids), "common_panel": len(rows), "excluded": len(ids) - len(rows),
                   "exclusion_reason_counts_nonexclusive": dict(all_reasons)}, results["coverage"], "coverage")
    recomputed_probabilistic, recomputed_economics = {}, {}
    for arm in ARMS:
        recomputed_probabilistic[arm] = {market: {"n": len(expected_rows), **{
            metric: sum(row["scores"][arm][market][metric] for row in expected_rows) / len(expected_rows)
            for metric in ("brier", "log_loss")}} for market in SIDES} if expected_rows else {}
        recomputed_economics[arm] = economics(expected_rows, arm)
    auditor.equal(recomputed_probabilistic, results["probabilistic"], "aggregate_probabilistic")
    auditor.equal(recomputed_economics, results["economics"], "aggregate_economics")
    audit_bootstrap(expected_rows, results["bootstrap"], auditor)
    return {"coverage": results["coverage"], "recomputed_probabilistic": recomputed_probabilistic,
            "recomputed_economics": recomputed_economics,
            "paired_weekly_bootstrap_reconciled": True,
            "source_reconciliation": "outcomes, odds, identities and old raw probabilities match hash-fixed inputs",
            "selection_settlement_imports_used": False,
            "model_refit_or_forecast_reexecution": False,
            "limits": ["Forecast algorithm and assumed 48-hour availability are not independently validated by arithmetic.",
                       "Matching file hashes does not authenticate provider publication times or executable prices.",
                       "Explored 2025 and descriptive confidence intervals cannot establish a confirmatory economic edge."]}


def main():
    auditor = Auditor()
    report = {"schema_version": "rolling-xg-arithmetic-audit/1", "plan_sha256": PLAN_SHA,
              "status": "FAIL", "audit_source_sha256": digest(Path(__file__)),
              "performed_at_utc": datetime.now(UTC).isoformat()}
    try:
        report.update(audit(auditor))
        report["status"] = "PASS"
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
    report["checks_completed"] = auditor.checks
    with (OUTPUT / "audit.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({key: report[key] for key in ("status", "checks_completed")}, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
