"""One preplanned conditional 2025 comparison; never writes observed clocks or live data."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import numpy as np
from brasileirao_predictor.research.price_strength.dynamic_xg import DynamicXGConfig
from conditional_model import calibrate_conditional, forecast_conditional
from frozen_economics import evaluate_candidates, select_candidate, settle_candidate

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parents[1] / "outputs/TESTE_XG_REAL"
MARKETS = {
    "1x2": ("home", "draw", "away"),
    "ou25": ("over", "under"),
    "btts": ("yes", "no"),
}
ARMS = (
    "xg_calibrated_primary",
    "xg_raw_diagnostic",
    "old_raw_frozen_2024",
    "market_proportional_devig",
)
PLAN_SHA = "507c69fc01aaabd9d78734b1153f740c3c347f601f5b1609cd54839a1698aaaa"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    with (OUTPUT / name).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def flatten(probabilities):
    return {
        "p_1x2": [probabilities["1x2"][side] for side in MARKETS["1x2"]],
        "p_over25": probabilities["ou25"]["over"],
        "p_btts": probabilities["btts"]["yes"],
    }


def expand(raw):
    vector = raw["p_1x2"]
    if isinstance(vector, dict):
        vector = [vector[side] for side in MARKETS["1x2"]]
    if len(vector) != 3:
        raise ValueError("baseline 1x2 vector must have three classes")
    return {
        "1x2": dict(zip(MARKETS["1x2"], vector)),
        "ou25": {"over": raw["p_over25"], "under": 1 - raw["p_over25"]},
        "btts": {"yes": raw["p_btts"], "no": 1 - raw["p_btts"]},
    }


def losses(probabilities, outcome):
    h, a = outcome["home_goals"], outcome["away_goals"]
    if type(h) is not int or type(a) is not int or min(h, a) < 0:
        raise ValueError("invalid final scores")
    winners = {
        "1x2": "home" if h > a else "away" if a > h else "draw",
        "ou25": "over" if h + a >= 3 else "under",
        "btts": "yes" if h and a else "no",
    }
    result = {}
    for market, sides in MARKETS.items():
        vector = probabilities[market]
        if set(vector) != set(sides) or not math.isclose(
            math.fsum(vector.values()), 1, abs_tol=1e-9
        ):
            raise ValueError("incomplete or unnormalized probabilities")
        if any(
            type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
            for p in vector.values()
        ):
            raise ValueError("invalid probability")
        actual = winners[market]
        brier = (
            math.fsum((vector[side] - int(side == actual)) ** 2 for side in sides)
            if market == "1x2"
            else (vector[sides[0]] - int(sides[0] == actual)) ** 2
        )
        result[market] = {
            "brier": brier,
            "log_loss": -math.log(max(vector[actual], 1e-15)),
        }
    return result


def accounting(rows, arm):
    bets = [row["bets"][arm] for row in rows if row["bets"][arm] is not None]
    gross = math.fsum(bet["settlement"]["gross_profit_units"] for bet in bets)
    net = math.fsum(bet["settlement"]["net_profit_units"] for bet in bets)
    balance = peak = drawdown = 0.0
    for row in rows:
        bet = row["bets"][arm]
        balance += bet["settlement"]["net_profit_units"] if bet else 0.0
        peak = max(peak, balance)
        drawdown = max(drawdown, peak - balance)
    wins = sum(bet["settlement"]["won"] for bet in bets)
    return {
        "fixtures": len(rows),
        "bets": len(bets),
        "wins": wins,
        "losses": len(bets) - wins,
        "stake_units": len(bets),
        "gross_profit_units": gross,
        "cost_units": 0.02 * len(bets),
        "net_profit_units": net,
        "net_roi": net / len(bets) if bets else None,
        "net_profit_per_fixture": net / len(rows) if rows else None,
        "max_drawdown_units": drawdown,
    }


def aggregate(rows):
    summary = {}
    for arm in ARMS:
        summary[arm] = (
            {
                market: {
                    "n": len(rows),
                    **{
                        loss: math.fsum(
                            row["scores"][arm][market][loss] for row in rows
                        )
                        / len(rows)
                        for loss in ("brier", "log_loss")
                    },
                }
                for market in MARKETS
            }
            if rows
            else {}
        )
    return summary


def paired_bootstrap(rows, *, replicates=2000, seed=20260907):
    if not rows:
        return {"week_count": 0, "probabilistic": {}, "economics": {}}
    weeks = [
        tuple(datetime.fromisoformat(row["kickoff"]).isocalendar()[:2]) for row in rows
    ]
    unique = sorted(set(weeks))
    groups = [
        np.array([i for i, week in enumerate(weeks) if week == key]) for key in unique
    ]
    draws = np.random.default_rng(seed).integers(
        0, len(groups), size=(replicates, len(groups))
    )
    counts = np.array([len(group) for group in groups])
    denominators = counts[draws].sum(axis=1)

    def interval(values):
        totals = np.array([math.fsum(values[i] for i in group) for group in groups])
        samples = totals[draws].sum(axis=1) / denominators
        return [float(value) for value in np.quantile(samples, [0.025, 0.975])]

    probabilistic, economics = {}, {}
    for candidate in ARMS[:2]:
        probabilistic[candidate], economics[candidate] = {}, {}
        for baseline in ARMS[2:]:
            probabilistic[candidate][baseline] = {}
            for market in MARKETS:
                probabilistic[candidate][baseline][market] = {}
                for loss in ("brier", "log_loss"):
                    values = [
                        row["scores"][candidate][market][loss]
                        - row["scores"][baseline][market][loss]
                        for row in rows
                    ]
                    probabilistic[candidate][baseline][market][loss] = {
                        "mean_delta": math.fsum(values) / len(values),
                        "ci95_weekly_descriptive": interval(values),
                    }
            values = [
                (
                    (
                        row["bets"][candidate]["settlement"]["net_profit_units"]
                        if row["bets"][candidate]
                        else 0
                    )
                    - (
                        row["bets"][baseline]["settlement"]["net_profit_units"]
                        if row["bets"][baseline]
                        else 0
                    )
                )
                for row in rows
            ]
            economics[candidate][baseline] = {
                "delta_profit_per_fixture": math.fsum(values) / len(values),
                "ci95_weekly_descriptive": interval(values),
            }
    return {
        "week_count": len(groups),
        "replicates": replicates,
        "seed": seed,
        "probabilistic": probabilistic,
        "economics": economics,
    }


def main():
    if sha(HERE / "plan.json") != PLAN_SHA or sha(OUTPUT / "PLANO.json") != PLAN_SHA:
        raise ValueError("frozen plan changed")
    plan = json.loads((HERE / "plan.json").read_text())
    for name, item in plan["source_files"].items():
        if sha(HERE / "inputs" / name) != item["sha256"]:
            raise ValueError("input hash mismatch")
    if sha(HERE / "frozen_economics.py") != plan["frozen_accounting_sha256"]:
        raise ValueError("accounting source changed")
    import brasileirao_predictor.research.price_strength.dynamic_xg as candidate_module

    if sha(Path(candidate_module.__file__)) != plan["candidate_module_sha256"]:
        raise ValueError("candidate source changed")
    config = DynamicXGConfig(**plan["candidate_config"])
    assert asdict(config) == plan["candidate_config"]
    history = json.loads((HERE / "inputs/history.json").read_text())
    old_rows = json.loads((HERE / "inputs/baseline_2025.json").read_text())
    old = {str(row["event_id"]): expand(row) for row in old_rows}
    if len(old) != len(old_rows):
        raise ValueError("duplicate baseline IDs")
    targets = sorted(
        [row for row in history if datetime.fromisoformat(row["kickoff"]).year == 2025],
        key=lambda row: (row["kickoff"], str(row["event_id"])),
    )
    if [str(row["event_id"]) for row in targets] != [
        row["event_id"] for row in plan["evaluation_fixtures"]
    ]:
        raise ValueError("fixture universe changed")
    write(
        "EXECUTION_LOCK.json",
        {
            "plan_sha256": PLAN_SHA,
            "candidate_fingerprint": config.fingerprint,
            "sources": {path.name: sha(path) for path in sorted(HERE.glob("*.py"))},
            "evaluation_scores_computed": False,
        },
    )
    calibration = calibrate_conditional(history, config)
    predictions, panel = [], []
    for target in targets:
        event_id = str(target["event_id"])
        raw = forecast_conditional(history, target, config)
        calibrated = forecast_conditional(
            history, target, config, calibration=calibration
        )
        record = {
            "event_id": event_id,
            "kickoff": target["kickoff"],
            "raw": raw,
            "calibrated": calibrated,
            "baseline": old.get(event_id),
            "availability_policy": "ASSUMED_48H_NOT_OBSERVED",
        }
        reasons = []
        if not raw["eligible"]:
            reasons.append("raw:" + raw["reason"])
        if not calibrated["eligible"]:
            reasons.append("calibrated:" + calibrated["reason"])
        if event_id not in old:
            reasons.append("missing_old_baseline")
        else:
            evaluated = evaluate_candidates(flatten(old[event_id]), target["odds"])
            if len(evaluated["valid_markets"]) != 3:
                reasons.append("incomplete_or_invalid_prices")
        panel.append(
            {"event_id": event_id, "included": not reasons, "reasons": reasons}
        )
        predictions.append(record)
    write("forecasts.json", predictions)
    write("panel.json", panel)
    write(
        "FORECAST_LOCK.json",
        {
            "forecasts_sha256": sha(OUTPUT / "forecasts.json"),
            "panel_sha256": sha(OUTPUT / "panel.json"),
            "evaluation_scores_computed": False,
        },
    )
    included = {row["event_id"] for row in panel if row["included"]}
    rows = []
    for target, prediction in zip(targets, predictions):
        event_id = str(target["event_id"])
        if event_id not in included:
            continue
        market = {}
        for name, sides in MARKETS.items():
            inverse = [1 / value for value in target["odds"][name]]
            market[name] = dict(
                zip(sides, [value / math.fsum(inverse) for value in inverse])
            )
        probabilities = dict(
            zip(
                ARMS,
                [
                    prediction["calibrated"]["probabilities"],
                    prediction["raw"]["probabilities"],
                    prediction["baseline"],
                    market,
                ],
            )
        )
        # Choose all bets before passing the target outcome into settlement.
        choices = {
            arm: select_candidate(flatten(probabilities[arm]), target["odds"])
            for arm in ARMS
        }
        outcome = {
            name: target["result"][name] for name in ("home_goals", "away_goals")
        }
        bets = {
            arm: {
                "candidate": chosen,
                "settlement": settle_candidate(chosen, **outcome),
            }
            if chosen
            else None
            for arm, chosen in choices.items()
        }
        rows.append(
            {
                "event_id": event_id,
                "home": target["home"],
                "away": target["away"],
                "kickoff": target["kickoff"],
                "outcome": outcome,
                "odds": target["odds"],
                "probabilities": probabilities,
                "scores": {arm: losses(probabilities[arm], outcome) for arm in ARMS},
                "bets": bets,
            }
        )
    reason_counts = {}
    for row in panel:
        for reason in row["reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    result = {
        "study_id": plan["study_id"],
        "status": plan["status"],
        "plan_sha256": PLAN_SHA,
        "config_fingerprint": config.fingerprint,
        "candidate_config": asdict(config),
        "calibration": calibration,
        "coverage": {
            "universe": len(targets),
            "common_panel": len(rows),
            "excluded": len(targets) - len(rows),
            "exclusion_reason_counts_nonexclusive": reason_counts,
        },
        "probabilistic": aggregate(rows),
        "economics": {arm: accounting(rows, arm) for arm in ARMS},
        "bootstrap": paired_bootstrap(rows),
        "availability_policy": plan["availability_policy"],
        "cross_book_comparison": plan["cross_book_comparison"],
        "execution_proven": False,
        "profitability_established": False,
        "real_capital_enabled": False,
        "limitations": [
            "Previously explored 2025; no confirmatory holdout.",
            "Final xG versions assumed usable after 48h, without publication or revision proof.",
            "Historical aggregate quotes lack bookmaker, observed time and execution evidence.",
            "Comparison changes full candidate, including dynamics/calibration, not only xG.",
            "Weekly bootstrap is descriptive and does not correct prior searches or fit uncertainty.",
        ],
    }
    write("event_results.json", rows)
    write("results.json", result)
    write(
        "MANIFEST.json",
        {
            "plan_sha256": PLAN_SHA,
            "files": {
                path.name: sha(path)
                for path in sorted(OUTPUT.glob("*.json"))
                if path.name != "MANIFEST.json"
            },
        },
    )
    print(
        json.dumps(
            {
                "coverage": result["coverage"],
                "calibration": {
                    key: calibration[key]
                    for key in ("n_matches", "eligible", "home_scale", "away_scale")
                },
                "probabilistic": result["probabilistic"],
                "economics": result["economics"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
