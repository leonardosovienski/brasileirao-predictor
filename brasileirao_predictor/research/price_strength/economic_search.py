"""Frozen BE-20260910 retrospective scenarios; no operational or network access.

Maxima are anonymous price envelopes, never executable offers. The goal model
does not use odds. Public seasons after 2024 are discarded before interpreting
any other field. This module is independent of serving and protected studies.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import math
import random
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

SOURCE_SHA = "ba3e9ea79ab4091b117a901f3914940cea07f1fe06de0deb57af5076f664ccb6"
PROTOCOL_SHA = "8a6f89c216d5d29c2719f3144b3221e60eaf50ce27a794108ffb5e23b64d4d43"
SIDES = ("H", "D", "A")
COST = 0.02


@dataclass(frozen=True)
class Match:
    season: int
    day: date
    home: str
    away: str
    goals: tuple[int, int] | None
    result: str | None
    pinnacle: tuple[float, float, float] | None
    maximum: tuple[float, float, float] | None
    label_issue: str | None = None

    @property
    def key(self) -> str:
        return f"{self.season}|{self.home}|{self.away}"


def odds(raw: dict[str, str], prefix: str) -> tuple[float, float, float] | None:
    try:
        values = tuple(float(raw[prefix + side]) for side in SIDES)
    except (KeyError, ValueError, TypeError):
        return None
    if len(values) != 3 or not all(math.isfinite(x) and x > 1 for x in values):
        return None
    return values[0], values[1], values[2]


def read_matches(raw: bytes) -> tuple[list[Match], dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    expected = {"Season", "Date", "Home", "Away", "HG", "AG", "Res"}
    if not expected.issubset(reader.fieldnames or []):
        raise ValueError("missing source schema")
    if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
        raise ValueError("duplicate column")
    output = []
    keys: set[str] = set()
    skipped = 0
    for row in reader:
        # Do not interpret identities, dates, labels or prices outside scope.
        if row.get("Season") not in {str(year) for year in range(2012, 2025)}:
            skipped += 1
            continue
        season = int(row["Season"])
        day = datetime.strptime(row["Date"], "%d/%m/%Y").date()
        home, away = row["Home"].strip(), row["Away"].strip()
        if not home or not away or home == away:
            raise ValueError("invalid identity")
        goals, result, issue = None, None, None
        try:
            hg, ag = int(row["HG"]), int(row["AG"])
            derived = "H" if hg > ag else "A" if hg < ag else "D"
            if hg < 0 or ag < 0 or row["Res"] != derived:
                raise ValueError("inconsistent goals/result")
            goals, result = (hg, ag), derived
        except (ValueError, TypeError):
            issue = "missing_or_inconsistent_label"
        match = Match(season, day, home, away, goals, result, odds(row, "PSC"), odds(row, "MaxC"), issue)
        if match.key in keys:
            raise ValueError(f"duplicate event: {match.key}")
        keys.add(match.key)
        output.append(match)
    output.sort(key=lambda m: (m.day, m.home, m.away))
    per_year = {}
    for season in range(2012, 2025):
        group = [m for m in output if m.season == season]
        teams = Counter(t for m in group for t in (m.home, m.away))
        per_year[str(season)] = {
            "matches": len(group),
            "teams": len(teams),
            "team_matches_min": min(teams.values(), default=0),
            "team_matches_max": max(teams.values(), default=0),
            "missing_pinnacle": sum(m.pinnacle is None for m in group),
            "missing_maximum": sum(m.maximum is None for m in group),
            "label_issues": sum(m.label_issue is not None for m in group),
        }
    return output, {"rows": len(output), "excluded_before_field_interpretation": skipped, "by_season": per_year}


def arbitrage(prices: tuple[float, float, float], cost: float = COST, deterioration: float = 0.01) -> dict[str, Any]:
    if not all(math.isfinite(o) and o > 1 for o in prices):
        raise ValueError("invalid odds")
    if not 0 <= deterioration < 1 or not math.isfinite(cost) or cost < 0:
        raise ValueError("invalid friction")
    adjusted = tuple(1 + (o - 1) * (1 - deterioration) for o in prices)
    inverse_sum = sum(1 / o for o in adjusted)
    stakes = tuple((1 / o) / inverse_sum for o in adjusted)
    returns = [s * o for s, o in zip(stakes, adjusted, strict=True)]
    net = min(returns) - 1 - cost
    failures = []
    for count in (1, 2):
        for subset in itertools.combinations(range(3), count):
            exposure = sum(stakes[i] for i in subset)
            outcomes = [returns[i] if i in subset else 0 for i in range(3)]
            failures.append(
                {
                    "filled_sides": [SIDES[i] for i in subset],
                    "stake": exposure,
                    "worst_net": min(outcomes) - exposure * (1 + cost),
                }
            )
    low, high = 0.0, 1.0
    if 1 / sum(1 / o for o in prices) - 1 - cost <= 0:
        break_even = 0.0
    else:
        for _ in range(60):
            middle = (low + high) / 2
            s = sum(1 / (1 + (o - 1) * (1 - middle)) for o in prices)
            if 1 / s - 1 - cost >= 0:
                low = middle
            else:
                high = middle
        break_even = low
    return {
        "prices": prices,
        "adjusted_prices": adjusted,
        "inverse_sum": inverse_sum,
        "raw_inverse_sum": sum(1 / o for o in prices),
        "stakes": stakes,
        "returns_by_outcome": returns,
        "net": net,
        "candidate": net >= 0.005,
        "cost": cost,
        "partial_fill_cases": failures,
        "break_even_prize_deterioration": break_even,
    }


def probabilities(lh: float, la: float) -> tuple[float, float, float]:
    if not all(math.isfinite(x) and 0 < x <= 10 for x in (lh, la)):
        raise ValueError("invalid goal intensity")
    masses = []
    for rate in (lh, la):
        values = [math.exp(-rate)]
        for k in range(1, 41):
            values.append(values[-1] * rate / k)
        masses.append(values)
    mass = sum(masses[0]) * sum(masses[1])
    if 1 - mass >= 1e-8:
        raise ValueError("excess truncated probability")
    p = [0.0, 0.0, 0.0]
    for h, ph in enumerate(masses[0]):
        for a, pa in enumerate(masses[1]):
            p[0 if h > a else 2 if h < a else 1] += ph * pa / mass
    return p[0], p[1], p[2]


def predict(history: list[Match], target: Match) -> dict[str, Any] | None:
    available = [
        (m, (target.day - m.day).days) for m in history if m.goals is not None and 7 <= (target.day - m.day).days <= 730
    ]
    if len(available) < 300:
        return None
    weights = [(m, math.exp(-math.log(2) * age / 365)) for m, age in available]
    mass = sum(w for _, w in weights)
    mh = sum(m.goals[0] * w for m, w in weights if m.goals is not None) / mass
    ma = sum(m.goals[1] * w for m, w in weights if m.goals is not None) / mass
    if min(mh, ma) <= 0:
        return None
    prior = 10 * (mh + ma) / 2
    rates = {}
    for team in (target.home, target.away):
        scored = conceded = expected_scored = expected_conceded = prior
        for m, w in weights:
            assert m.goals is not None
            if m.home == team:
                scored += w * m.goals[0]
                conceded += w * m.goals[1]
                expected_scored += w * mh
                expected_conceded += w * ma
            elif m.away == team:
                scored += w * m.goals[1]
                conceded += w * m.goals[0]
                expected_scored += w * ma
                expected_conceded += w * mh
        rates[team] = (scored / expected_scored, conceded / expected_conceded)
    lh = mh * rates[target.home][0] * rates[target.away][1]
    la = ma * rates[target.away][0] * rates[target.home][1]
    try:
        return {
            "model": probabilities(lh, la),
            "league": probabilities(mh, ma),
            "lambda_home": lh,
            "lambda_away": la,
            "training_matches": len(available),
            "latest_training_day": max(m.day for m, _ in available).isoformat(),
            "earliest_training_day": min(m.day for m, _ in available).isoformat(),
        }
    except ValueError:
        return None


def select(p: tuple[float, float, float], prices: tuple[float, float, float]) -> int | None:
    if not all(math.isfinite(x) and 0 <= x <= 1 for x in p) or abs(sum(p) - 1) > 1e-8:
        raise ValueError("invalid probability")
    ev = [q * o - 1 - COST for q, o in zip(p, prices, strict=True)]
    choice = max(range(3), key=lambda i: ev[i])
    return choice if ev[choice] >= 0.03 else None


def ledger(rows: list[dict[str, Any]], strategy: str) -> list[dict[str, Any]]:
    """Reserve all same-day stakes/costs before hypothetical settlement."""
    cash = 100.0
    unsettled = 0.0
    output = []
    for day, batch in itertools.groupby(rows, key=lambda r: r["date"]):
        pending = []
        opening = cash
        for row in batch:
            item = {
                "key": row["key"],
                "date": day,
                "season": row["season"],
                "home": row["home"],
                "away": row["away"],
                "strategy": strategy,
                "stake": 0.0,
                "cost": 0.0,
                "return": 0.0,
                "net": 0.0,
                "choice": None,
                "probability": None,
                "price": None,
                "won": None,
                "status": "abstain",
                "reason": row.get("reason"),
            }
            if row.get("prediction") is not None and row.get("pinnacle") is not None:
                p = row["prediction"][strategy]
                choice = select(p, row["pinnacle"])
                if choice is None:
                    item["reason"] = "no_edge_after_cost"
                else:
                    item.update(choice=SIDES[choice], probability=p[choice], price=row["pinnacle"][choice])
                    if cash + 1e-10 < 1 + COST:
                        item["reason"] = "insufficient_unreserved_bankroll"
                    else:
                        cash -= 1 + COST
                        item.update(stake=1.0, cost=COST, status="hypothetical_fill", reason=None)
            pending.append((item, row["result"]))
        exposure = sum(item["stake"] for item, _ in pending) + unsettled
        for item, result in pending:
            if item["stake"]:
                if result is None:
                    unsettled += item["stake"]
                    item.update(status="unsettled", reason="label_unavailable", net=None, **{"return": None})
                else:
                    won = item["choice"] == result
                    returned = item["price"] if won else 0.0
                    cash += returned
                    item.update(won=won, net=returned - item["stake"] - item["cost"], **{"return": returned})
        for item, _ in pending:
            item.update(cash_before_day=opening, cash_after_day=cash, day_exposure=exposure, unsettled_stakes=unsettled)
            output.append(item)
    return output


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("empty distribution")
    ordered = sorted(values)
    at = (len(ordered) - 1) * q
    lo = int(at)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] * (hi - at) + ordered[hi] * (at - lo) if hi != lo else ordered[lo]


def blocks(rows: list[dict[str, Any]]) -> list[tuple[float, float]]:
    if not rows:
        return []
    start = date.fromisoformat(rows[0]["date"])
    count = (date.fromisoformat(rows[-1]["date"]) - start).days // 28 + 1
    bins = [[0.0, 0.0] for _ in range(count)]
    for r in rows:
        index = (date.fromisoformat(r["date"]) - start).days // 28
        bins[index][0] += r["net"] or 0.0
        bins[index][1] += r["stake"]
    return [(pnl, stake) for pnl, stake in bins]


def bootstrap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if any(r["status"] == "unsettled" for r in rows):
        return {"status": "unknown_unsettled_results"}
    bins = blocks(rows)
    rng = random.Random(20260910)
    ratios = []
    for _ in range(2000):
        sample = rng.choices(bins, k=len(bins))
        stake = sum(s for _, s in sample)
        if stake:
            ratios.append(sum(p for p, _ in sample) / stake)
    return {
        "block_days": 28,
        "blocks_including_empty": len(bins),
        "resamples": 2000,
        "seed": 20260910,
        "roi_ci95": [quantile(ratios, 0.025), quantile(ratios, 0.975)] if ratios else None,
        "roi_lower95_one_sided": quantile(ratios, 0.05) if ratios else None,
        "selection_history_adjusted": False,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fills = [r for r in rows if r["stake"]]
    unknown = any(r["net"] is None for r in rows)
    stake = sum(r["stake"] for r in rows)
    net = sum(r["net"] or 0.0 for r in rows)
    by_season = {}
    for year in sorted({r["season"] for r in rows}):
        subset = [r for r in rows if r["season"] == year]
        s = sum(r["stake"] for r in subset)
        n = sum(r["net"] or 0.0 for r in subset)
        by_season[str(year)] = {
            "events": len(subset),
            "fills": sum(bool(r["stake"]) for r in subset),
            "stake": s,
            "net": n if not any(r["net"] is None for r in subset) else None,
            "roi": n / s if s and not any(r["net"] is None for r in subset) else None,
        }
    peak = 100.0
    drawdown = 0.0
    for r in rows:
        peak = max(peak, r["cash_after_day"])
        drawdown = max(drawdown, peak - r["cash_after_day"])
    costs = {}
    for c in (0, 0.01, 0.02, 0.03, 0.05):
        costs[str(c)] = sum(r["return"] - r["stake"] * (1 + c) for r in fills) if not unknown else None
    degraded = (
        sum((1 + (r["price"] - 1) * 0.99 if r["won"] else 0) - r["stake"] - r["cost"] for r in fills)
        if not unknown
        else None
    )
    teams = Counter(t for r in fills for t in (r["home"], r["away"]))
    wins = sorted((r for r in fills if r["won"]), key=lambda r: r["net"], reverse=True)
    return {
        "events": len(rows),
        "opportunities": sum(r["choice"] is not None for r in rows),
        "hypothetical_fills": len(fills),
        "real_bets": 0,
        "abstentions": len(rows) - len(fills),
        "abstention_reasons": dict(Counter(r["reason"] for r in rows if r["reason"])),
        "initial_bankroll": 100,
        "final_cash": rows[-1]["cash_after_day"] if rows else 100,
        "unsettled_stakes": rows[-1]["unsettled_stakes"] if rows else 0,
        "stake": stake,
        "cost": sum(r["cost"] for r in rows),
        "return_including_principal": sum(r["return"] or 0 for r in rows),
        "net_scenario": None if unknown else net,
        "net_total_after_unknown_personal_costs": None,
        "roi_stakes": net / stake if stake and not unknown else None,
        "bankroll_return": net / 100 if not unknown else None,
        "max_daily_exposure": max((r["day_exposure"] for r in rows), default=0),
        "max_cash_drawdown_units": drawdown,
        "by_season": by_season,
        "fixed_fill_cost_sensitivity_net": costs,
        "fixed_fill_1pct_prize_deterioration_net": degraded,
        "selected_mean_probability": sum(r["probability"] for r in fills) / len(fills) if fills else None,
        "selected_win_fraction": sum(bool(r["won"]) for r in fills) / len(fills) if fills and not unknown else None,
        "top_five_win_net": sum(r["net"] for r in wins[:5]),
        "net_excluding_top_five_win_events": net - sum(r["net"] for r in wins[:5]) if not unknown else None,
        "largest_team_involvement": teams.most_common(5),
        "bootstrap": bootstrap(rows),
    }


def evaluate(matches: list[Match]) -> dict[str, Any]:
    envelopes = []
    predictions = []
    for m in matches:
        envelope = {
            "key": m.key,
            "date": m.day.isoformat(),
            "season": m.season,
            "reason": None if m.maximum else "missing_maximum",
            "execution_admitted": False,
        }
        if m.maximum:
            envelope.update(arbitrage(m.maximum))
        envelopes.append(envelope)
        if m.season >= 2015:
            pred = predict(matches, m)
            reason = (
                "missing_pinnacle"
                if m.pinnacle is None
                else "insufficient_training_or_invalid_model"
                if pred is None
                else None
            )
            predictions.append(
                {
                    "key": m.key,
                    "date": m.day.isoformat(),
                    "season": m.season,
                    "home": m.home,
                    "away": m.away,
                    "pinnacle": m.pinnacle,
                    "result": m.result,
                    "prediction": pred,
                    "reason": reason,
                }
            )
    ledgers = {name: ledger(predictions, name) for name in ("model", "league")}
    summaries = {name: summarize(rows) for name, rows in ledgers.items()}
    scoring: dict[str, Any] = {
        name: {"logloss": 0.0, "brier": 0.0} for name in ("model", "league", "pinnacle_normalized")
    }
    common = [r for r in predictions if r["prediction"] and r["pinnacle"] and r["result"]]
    for r in common:
        y = SIDES.index(r["result"])
        q = [1 / o for o in r["pinnacle"]]
        for name in scoring:
            p = [x / sum(q) for x in q] if name == "pinnacle_normalized" else r["prediction"][name]
            scoring[name]["logloss"] -= math.log(max(p[y], 1e-300)) / len(common)
            scoring[name]["brier"] += sum((x - int(i == y)) ** 2 for i, x in enumerate(p)) / len(common)
    candidates = [r for r in envelopes if r.get("candidate")]
    arb_years = {}
    for year in range(2012, 2025):
        all_year = [r for r in envelopes if r["season"] == year]
        chosen = [r for r in candidates if r["season"] == year]
        arb_years[str(year)] = {
            "events": len(all_year),
            "candidates": len(chosen),
            "net_envelope": sum(r["net"] for r in chosen),
        }
    model_summary = summaries["model"]
    lower = model_summary["bootstrap"].get("roi_lower95_one_sided")
    advance_model = (
        model_summary["hypothetical_fills"] >= 300
        and lower is not None
        and lower > 0
        and (model_summary["net_scenario"] or 0) > 0
        and sum((s["net"] or 0) > 0 for s in model_summary["by_season"].values()) >= 6
        and (model_summary["fixed_fill_1pct_prize_deterioration_net"] or 0) > 0
    )
    day_exposure = Counter(r["date"] for r in candidates)
    arb_net = sum(r["net"] for r in candidates)
    partial_worst = min((c["worst_net"] for r in candidates for c in r["partial_fill_cases"]), default=None)
    summary = {
        "status": "retrospective_conditional_scenarios_only",
        "execution_admitted": False,
        "arbitrage": {
            "events": len(envelopes),
            "missing_prices": sum(bool(r["reason"]) for r in envelopes),
            "candidates": len(candidates),
            "hypothetical_legs": 3 * len(candidates),
            "real_bets": 0,
            "stake_envelope": len(candidates),
            "net_envelope": arb_net,
            "cost_envelope": COST * len(candidates),
            "roi_envelope": arb_net / len(candidates) if candidates else None,
            "final_bankroll_envelope": 100 + arb_net,
            "max_same_date_stake": max(day_exposure.values(), default=0),
            "worst_partial_fill_net_per_event": partial_worst,
            "by_season": arb_years,
            "minimum_net": min((r["net"] for r in candidates), default=None),
            "maximum_net": max((r["net"] for r in candidates), default=None),
            "minimum_break_even_prize_deterioration": min(
                (r["break_even_prize_deterioration"] for r in candidates), default=None
            ),
            "fixed_candidate_cost_sensitivity": {
                str(c): sum(r["net"] + COST - c for r in candidates) for c in (0, 0.01, 0.02, 0.03, 0.05)
            },
            "advance_to_simultaneity_investigation": len(candidates) >= 30
            and sum(s["candidates"] > 0 for s in arb_years.values()) >= 3,
            "net_total_after_unknown_personal_costs": None,
        },
        "forecast": summaries,
        "advance_model_to_new_validation": advance_model,
        "common_panel": {"events": len(common), "scores": scoring},
        "start_date": matches[0].day.isoformat(),
        "end_date": matches[-1].day.isoformat(),
    }
    b1, b2 = blocks(ledgers["model"]), blocks(ledgers["league"])
    if len(b1) == len(b2) and not any(r["status"] == "unsettled" for rows in ledgers.values() for r in rows):
        rng = random.Random(20260910)
        diffs = []
        for _ in range(2000):
            indices = rng.choices(range(len(b1)), k=len(b1))
            diffs.append(sum(b1[i][0] - b2[i][0] for i in indices))
        summary["paired_model_minus_league_net_ci95"] = [quantile(diffs, 0.025), quantile(diffs, 0.975)]
    return {"summary": summary, "envelopes": envelopes, "predictions": predictions, "ledgers": ledgers}


def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError("not the preregistered public source")
    if hashlib.sha256(args.protocol.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError("not the frozen protocol")
    root = Path("C:/BRASILEIRAO/work/economic-search-2026-09-10").resolve()
    if not args.output_dir.resolve().is_relative_to(root) or args.output_dir.resolve() == root:
        raise ValueError("output must be a new child of isolated study directory")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    started = datetime.now(UTC).isoformat()
    matches, coverage = read_matches(raw)
    result = evaluate(matches)
    write_json(args.output_dir / "coverage.json", coverage)
    for name, value in result.items():
        write_json(args.output_dir / f"{name}.json", value)
    write_json(args.output_dir / "matches.json", [dict(asdict(m), day=m.day.isoformat()) for m in matches])
    manifest = {
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "source_sha256": SOURCE_SHA,
        "protocol_sha256": PROTOCOL_SHA,
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "outputs": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.output_dir.iterdir()) if p.is_file()
        },
    }
    write_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps(result["summary"], ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
