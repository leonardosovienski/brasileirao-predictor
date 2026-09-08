"""Independent arithmetic audit of an already executed, frozen correction.

Standard library only. This module does not import model fitting, forecasting,
replay, application configuration, SQLite, or network modules. Its operations
verify published predictions and receipts; they do not train another candidate.
The artifact adapter is kept separate from the independent arithmetic below.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[2]
EXPECTED_PLAN_SHA256 = "2c9a6615f77c2568ecc70868ce8283f6bb6a5796c622df898bc3858927e11a92"
MARKETS = ("1x2", "ou25", "btts")
SIDES = {"1x2": ("home", "draw", "away"), "ou25": ("over", "under"), "btts": ("yes", "no")}
ODDS_LIMITS = {"1x2": (1.05, 20.0), "ou25": (1.2, 5.0), "btts": (1.2, 5.0)}
TRAIN_START = datetime(2024, 1, 1, tzinfo=UTC)
TRAIN_END = datetime(2025, 1, 1, tzinfo=UTC)
ASSUMED_LAG = timedelta(hours=48)


class AuditError(ValueError):
    """An artifact contradicts the frozen protocol or independent arithmetic."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def finite(value: Any, label: str = "number") -> float:
    require(type(value) in (int, float), f"{label}: numeric scalar required, excluding bool")
    result = float(value)
    require(math.isfinite(result), f"{label}: finite scalar required")
    return result


def clock(value: Any) -> datetime:
    require(isinstance(value, str), "timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None and result.utcoffset() is not None, "timestamp must include timezone")
    return result.astimezone(UTC)


def identifier(value: Any) -> str:
    require(type(value) in (str, int), "identifier must be string or integer")
    result = str(value)
    require(bool(result.strip()) and result == result.strip(), "invalid identifier")
    return result


def near(actual: Any, expected: Any, label: str, *, tolerance: float = 1e-10) -> None:
    if expected is None:
        require(actual is None, f"{label}: expected null, found {actual!r}")
        return
    a, e = finite(actual, label), finite(expected, label)
    require(math.isclose(a, e, rel_tol=tolerance, abs_tol=tolerance), f"{label}: {a!r} != {e!r}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise AuditError(f"nonstandard JSON constant: {value}")


def _scan_finite(value: Any) -> None:
    if isinstance(value, float):
        require(math.isfinite(value), "non-finite JSON numeric value")
    elif isinstance(value, list):
        for item in value:
            _scan_finite(item)
    elif isinstance(value, dict):
        for item in value.values():
            _scan_finite(item)


def read_json_receipt(path: Path, *, allowed: Sequence[Path]) -> tuple[Any, str]:
    """Parse and hash one read; permit only explicitly named audit inputs."""
    resolved = path.resolve(strict=True)
    permitted = {item.resolve(strict=True) for item in allowed}
    require(resolved in permitted, "path is not an explicitly declared audit input")
    require("data" not in resolved.relative_to(WORKSPACE.resolve()).parts, "data directories are outside audit scope")
    raw = resolved.read_bytes()
    parsed = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    _scan_finite(parsed)
    return parsed, hashlib.sha256(raw).hexdigest()


def probabilities(value: Any, market: str) -> tuple[float, ...]:
    require(market in SIDES, "unknown market")
    require(isinstance(value, (list, tuple)) and len(value) == len(SIDES[market]), f"{market}: complete vector required")
    vector = tuple(finite(item, "probability") for item in value)
    require(all(0 <= item <= 1 for item in vector), "probability outside [0,1]")
    require(math.isclose(math.fsum(vector), 1, abs_tol=1e-6, rel_tol=0), "probability vector does not sum to one")
    return vector


def flat_vectors(forecast: Mapping[str, Any]) -> dict[str, tuple[float, ...]]:
    result = {"1x2": probabilities(forecast["p_1x2"], "1x2")}
    for market, field in (("ou25", "p_over25"), ("btts", "p_btts")):
        positive = finite(forecast[field], field)
        result[market] = probabilities((positive, 1 - positive), market)
    return result


def devig(quotes: Any, market: str) -> tuple[float, ...] | None:
    if not isinstance(quotes, (list, tuple)) or len(quotes) != len(SIDES[market]):
        return None
    low, high = ODDS_LIMITS[market]
    if any(type(item) not in (float, int) or not math.isfinite(item) or not low <= item <= high for item in quotes):
        return None
    inverse = tuple(1 / item for item in quotes)
    total = math.fsum(inverse)
    if not 1 - 1e-12 <= total <= 1.3 + 1e-12:
        return None
    return tuple(item / total for item in inverse)


def winners(home_goals: Any, away_goals: Any) -> dict[str, int]:
    home, away = home_goals, away_goals
    require(type(home) is int and type(away) is int and min(home, away) >= 0, "goals must be nonnegative integers")
    return {
        "1x2": 0 if home > away else 2 if away > home else 1,
        "ou25": int(home + away < 3),
        "btts": int(not (home > 0 and away > 0)),
    }


def verify_weight(samples: Sequence[Mapping[str, Any]], market: str, reported_weight: float) -> dict[str, Any]:
    """Check the constrained quadratic optimum using 50-digit decimal sums.

    Each sample supplies model/market probability vectors and observed class.
    Recomputing this identity verifies a published coefficient, not a new fit.
    """
    require(len(samples) >= 20, f"{market}: fewer than frozen minimum20 samples")
    with localcontext() as context:
        context.prec = 50
        numerator, denominator = Decimal(0), Decimal(0)
        for sample in samples:
            p = probabilities(sample["model"], market)
            q = probabilities(sample["market"], market)
            outcome = sample["outcome"]
            require(type(outcome) is int and 0 <= outcome < len(p), "invalid outcome class")
            for index in range(len(p) if market == "1x2" else 1):
                d = Decimal(str(p[index])) - Decimal(str(q[index]))
                target = Decimal(int(index == outcome)) - Decimal(str(q[index]))
                numerator += d * target
                denominator += d * d
        expected = Decimal(0) if denominator == 0 else min(Decimal(1), max(Decimal(0), numerator / denominator))
    near(reported_weight, float(expected), f"{market}.weight")
    return {"n": len(samples), "weight": float(expected), "numerator": str(numerator), "denominator": str(denominator)}


def verify_training_times(samples: Sequence[Mapping[str, Any]], evaluation_ids: set[str], history: Mapping[str, Mapping[str, Any]]) -> None:
    seen = set()
    for sample in samples:
        event_id = identifier(sample["event_id"])
        require(event_id not in seen, "duplicate event within calibration market")
        seen.add(event_id)
        require(event_id not in evaluation_ids, "evaluation ID entered calibration")
        kickoff = clock(sample["kickoff"])
        require(TRAIN_START <= kickoff and kickoff + ASSUMED_LAG < TRAIN_END, "calibration label outside frozen time limits")
        decision = kickoff - timedelta(minutes=60)
        for used_id in sample["history_ids"]:
            used_id = identifier(used_id)
            require(used_id != event_id and used_id not in evaluation_ids, "self/future evaluation history entered calibration")
            require(clock(history[used_id]["kickoff"]) + ASSUMED_LAG < decision, "nonvisible calibration feature")


def verify_feature_history(forecast: Mapping[str, Any], history: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Check only rows claimed as used, without rebuilding any model forecast."""
    event_id = identifier(forecast["event_id"])
    decision = clock(forecast["decision_at"])
    used = [identifier(value) for value in forecast["history_ids"]]
    require(len(used) == len(set(used)), "duplicate history identifier")
    for used_id in used:
        require(used_id != event_id, "target entered its own features")
        row = history[used_id]
        require(clock(row["kickoff"]) + ASSUMED_LAG < decision, "future or embargoed feature history")
        result = row.get("result")
        require(isinstance(result, dict), "missing result entered features")
        hx, ax = result.get("home_xg"), result.get("away_xg")
        require(hx is not None and ax is not None, "missing/partial xG pair entered features")
        hx, ax = finite(hx, "home_xg"), finite(ax, "away_xg")
        require(hx >= 0 and ax >= 0 and (hx != 0 or ax != 0), "invalid/ambiguous-zero xG entered features")
    return {"event_id": event_id, "used_ids": len(used)}


def scores(vector: Sequence[float], outcome: int, market: str) -> tuple[float, float]:
    vector = probabilities(vector, market)
    require(type(outcome) is int and 0 <= outcome < len(vector), "invalid outcome")
    indices = range(len(vector)) if market == "1x2" else range(1)
    brier = math.fsum((vector[index] - int(outcome == index)) ** 2 for index in indices)
    # Frozen evaluators use clipping only to make a zero-probability loss finite.
    logloss = -math.log(max(1e-15, vector[outcome]))
    return brier, logloss


def select_from_published(forecast: Mapping[str, Any], odds: Mapping[str, Any]) -> dict[str, Any] | None:
    """Independent fixed-policy decision check using published predictions."""
    vectors = flat_vectors(forecast)
    candidates = []
    for market_rank, market in enumerate(MARKETS):
        if devig(odds.get(market), market) is None:
            continue
        for side_index, (p, odd) in enumerate(zip(vectors[market], odds[market])):
            edge = p - 1 / odd
            ev = p * odd - 1.02
            if edge > 0.02 + 1e-12 and edge <= 0.15 + 1e-12 and ev > 0:
                candidates.append(((-ev, market_rank, side_index), {
                    "market": market, "side": SIDES[market][side_index],
                    "side_index": side_index, "probability": p,
                    "odd": odd, "edge": edge, "predicted_net_ev": ev,
                }))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def payment(candidate: Mapping[str, Any] | None, home_goals: int, away_goals: int) -> dict[str, Any]:
    home, away = home_goals, away_goals
    if candidate is None:
        return {"won": None, "stake_units": 0.0, "gross_profit_units": 0.0, "cost_units": 0.0, "net_profit_units": 0.0}
    market = candidate["market"]
    require(market in SIDES, "invalid settled market")
    side = candidate["side_index"]
    require(type(side) is int and 0 <= side < len(SIDES[market]), "invalid settled side")
    require(candidate["side"] == SIDES[market][side], "settled side index/name mismatch")
    odd = finite(candidate["odd"], "settlement odd")
    require(odd > 1, "settlement odd must exceed1")
    won = side == winners(home, away)[market]
    gross = odd * int(won) - 1
    return {"won": won, "stake_units": 1.0, "gross_profit_units": gross, "cost_units": 0.02, "net_profit_units": gross - 0.02}


def transitions(baseline: Mapping[str, Mapping[str, Any]], primary: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Partition all events, distinguishing retained, removed and changed bets."""
    require(set(baseline) == set(primary), "transition panels differ")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event_id in sorted(baseline):
        old, new = baseline[event_id], primary[event_id]
        a, b = old["candidate"], new["candidate"]
        aw, bw = old["payment"]["won"], new["payment"]["won"]
        if a is None and b is None:
            category = "both_abstained"
        elif b is None:
            category = "removed_winner" if aw else "avoided_loser"
        elif a is None:
            category = "added_winner" if bw else "added_loser"
        elif (a["market"], a["side_index"]) == (b["market"], b["side_index"]):
            require(aw == bw, "identical selection settled inconsistently")
            category = "retained_winner" if aw else "retained_loser"
        else:
            category = f"changed_{'win' if aw else 'loss'}_to_{'win' if bw else 'loss'}"
        old_net, new_net = old["payment"]["net_profit_units"], new["payment"]["net_profit_units"]
        groups[category].append({"event_id": event_id, "baseline_net": old_net, "primary_net": new_net, "difference": new_net - old_net})
    return {name: {"n": len(rows), "baseline_net": math.fsum(row["baseline_net"] for row in rows),
                   "primary_net": math.fsum(row["primary_net"] for row in rows),
                   "difference": math.fsum(row["difference"] for row in rows), "events": rows}
            for name, rows in sorted(groups.items())}


def vectors_from_dict(value: Mapping[str, Any]) -> dict[str, tuple[float, ...]]:
    require(set(value) == set(MARKETS), "all three complete markets required")
    result = {}
    for market, sides in SIDES.items():
        require(set(value[market]) == set(sides), "unexpected or missing outcome side")
        result[market] = probabilities([value[market][side] for side in sides], market)
    return result


def flatten_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    vectors = vectors_from_dict(value)
    return {"p_1x2": vectors["1x2"], "p_over25": vectors["ou25"][0], "p_btts": vectors["btts"][0]}


def index_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result = {identifier(row["event_id"]): row for row in rows}
    require(len(result) == len(rows), "duplicate event IDs")
    return result


def quality_category(row: Mapping[str, Any]) -> str:
    values = row.get("result") or {}
    h, a = values.get("home_xg"), values.get("away_xg")
    if h is None and a is None:
        return "MISSING_PAIR"
    if h is None or a is None:
        return "PARTIAL_PAIR"
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in (h, a)):
        return "INVALID_PAIR"
    return "ZERO_PAIR_UNATTESTED" if h == 0 and a == 0 else "NUMERIC_PAIR"


def expected_history_ids(target: Mapping[str, Any], history: Mapping[str, Mapping[str, Any]]) -> tuple[list[str], int, int]:
    """Verify a claimed feature window; calculate no model probability."""
    decision = clock(target["kickoff"]) - timedelta(minutes=60)
    ordered = sorted(history.values(), key=lambda row: (clock(row["kickoff"]), identifier(row["event_id"])))
    visible = [row for row in ordered if identifier(row["event_id"]) != identifier(target["event_id"])
               and clock(row["kickoff"]) + ASSUMED_LAG < decision and quality_category(row) == "NUMERIC_PAIR"]
    home = [row for row in visible if row["home"] == target["home"]][-5:]
    away = [row for row in visible if row["away"] == target["away"]][-5:]
    return sorted({identifier(row["event_id"]) for row in (*home, *away)}), len(home), len(away)


def verify_candidate(actual: Any, expected: Any, label: str) -> None:
    if expected is None:
        require(actual is None, f"{label}: unexpected bet")
        return
    require(isinstance(actual, dict), f"{label}: missing bet")
    for field, value in expected.items():
        if field in ("market", "side", "side_index"):
            require(actual[field] == value, f"{label}.{field}: wrong selection")
        else:
            near(actual[field], value, f"{label}.{field}")


def summarize_checked(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    stakes = sum(row["candidate"] is not None for row in rows)
    wins_count = sum(row["payment"]["won"] is True for row in rows)
    net = math.fsum(row["payment"]["net_profit_units"] for row in rows)
    gross = math.fsum(row["payment"]["gross_profit_units"] for row in rows)
    balance = peak = drawdown = 0.0
    for row in rows:
        balance += row["payment"]["net_profit_units"]
        peak = max(peak, balance)
        drawdown = max(drawdown, peak - balance)
    return {"fixtures": len(rows), "bets": stakes, "wins": wins_count, "losses": stakes - wins_count,
            "stake_units": stakes, "gross_profit_units": gross, "cost_units": 0.02 * stakes,
            "net_profit_units": net, "net_roi": net / stakes if stakes else None,
            "net_profit_per_fixture": net / len(rows) if rows else None, "max_drawdown_units": drawdown}


def audit_artifacts(directory: Path) -> dict[str, Any]:
    directory = directory.resolve(strict=True)
    require(directory == (WORKSPACE / "outputs/DIAGNOSTICO_XG/CORRECAO").resolve(strict=True), "unexpected audit artifact directory")
    filenames = ("PLANO.json", "EXECUTION_LOCK.json", "quality.json", "calibration_rows.json", "FIT.json",
                 "FIT_LOCK.json", "forecasts.json", "panel.json", "FORECAST_LOCK.json", "event_results.json",
                 "original_panel_results.json", "results.json", "MANIFEST.json")
    allowed = [directory / name for name in filenames]
    artifacts, hashes = {}, {}
    for name in filenames:
        artifacts[name], hashes[name] = read_json_receipt(directory / name, allowed=allowed)
    plan = artifacts["PLANO.json"]
    require(hashes["PLANO.json"] == EXPECTED_PLAN_SHA256, "frozen plan digest mismatch")
    require(artifacts["MANIFEST.json"]["files"] == {name: digest for name, digest in hashes.items() if name != "MANIFEST.json"}, "manifest file digests differ")
    for name, expected in plan["inputs"].items():
        path = (WORKSPACE / name).resolve(strict=True)
        require(path.is_relative_to(WORKSPACE.resolve()), "frozen input escaped workspace")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "frozen input digest changed")
    source_hashes = artifacts["EXECUTION_LOCK.json"]["source_sha256"]
    for name, expected in source_hashes.items():
        path = Path(name).resolve(strict=True)
        require(path.is_relative_to(WORKSPACE.resolve()) and path.suffix == ".py", "unexpected executed source path")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "executed source changed after receipt")
    require(artifacts["EXECUTION_LOCK.json"]["plan_sha256"] == EXPECTED_PLAN_SHA256, "execution locked wrong plan")
    require(artifacts["FIT_LOCK.json"]["fit_sha256"] == hashes["FIT.json"], "fit lock digest mismatch")
    require(artifacts["FIT_LOCK.json"]["calibration_rows_sha256"] == hashes["calibration_rows.json"], "calibration rows lock mismatch")
    require(artifacts["FORECAST_LOCK.json"]["forecasts_sha256"] == hashes["forecasts.json"], "forecast lock mismatch")
    require(artifacts["FORECAST_LOCK.json"]["panel_sha256"] == hashes["panel.json"], "panel lock mismatch")

    old = WORKSPACE / "outputs/TESTE_XG_REAL"
    extras = [WORKSPACE / "work/price_strength_evaluation/inputs/history.json",
              old / "results.json", old / "forecasts.json", old / "panel.json", old / "event_results.json"]
    frozen_input_hashes = {(WORKSPACE / name).resolve(): digest for name, digest in plan["inputs"].items()}
    external = {}
    for path in extras:
        parsed, used_digest = read_json_receipt(path, allowed=extras)
        require(used_digest == frozen_input_hashes[path.resolve()], "parsed input bytes differ from frozen digest")
        external[path.name if path.parent == old else "history.json"] = parsed
    history = index_rows(external["history.json"])
    require(all(2021 <= clock(row["kickoff"]).year <= 2025 for row in history.values()), "history includes an inadmissible year")
    old_forecasts = index_rows(external["forecasts.json"])
    old_events = index_rows(external["event_results.json"])
    old_panel = {identifier(row["event_id"]) for row in external["panel.json"] if row["included"]}
    require(len(old_panel) == 368 and old_panel == set(old_events), "original population is not the frozen368")
    evaluation = index_rows(plan["evaluation_fixtures"])
    require(len(evaluation) == 380, "evaluation universe is not380")
    require(set(evaluation) == {key for key, row in history.items() if clock(row["kickoff"]).year == 2025}, "evaluation identities differ from history")
    for event_id, fixture in evaluation.items():
        require(all(fixture[key] == history[event_id][key] for key in ("home", "away", "kickoff")), "fixture identity changed")

    expected_quality: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    expected_excluded = []
    for event_id, row in history.items():
        category = quality_category(row)
        require(category != "INVALID_PAIR", "malformed historical xG")
        expected_quality[str(clock(row["kickoff"]).year)][category] += 1
        if category != "NUMERIC_PAIR":
            expected_excluded.append({"event_id": event_id, "category": category})
    require(artifacts["quality.json"]["by_year"] == expected_quality, "quality categories/counts differ")
    require(artifacts["quality.json"]["excluded_features"] == expected_excluded, "quality excluded identities differ")

    fit = artifacts["FIT.json"]
    require(fit["candidate_config"] == plan["candidate_config"], "candidate defaults changed")
    require(fit["rate_calibration_diagnostic"] == external["results.json"]["calibration"], "2024 rate calibration changed")
    calibration_rows = artifacts["calibration_rows.json"]
    calibration_ids = set(index_rows(calibration_rows))
    require(calibration_ids == set(fit["rate_calibration_diagnostic"]["target_match_ids"]), "rate and raw calibration targets differ")
    require(not calibration_ids & set(evaluation), "2025 target entered calibration")
    for row in calibration_rows:
        event_id = identifier(row["event_id"])
        target = history[event_id]
        require(row["kickoff"] == target["kickoff"], "calibration kickoff changed")
        require(clock(row["decision_at"]) == clock(row["kickoff"]) - timedelta(minutes=60), "wrong calibration decision time")
        expected_ids, _, _ = expected_history_ids(target, history)
        require(row["history_ids"] == expected_ids, "calibration feature window differs")
        verify_feature_history(row, history)
        require(row["odds"] == target["odds"], "calibration quotes changed")
        require(row["outcome"] == {key: target["result"][key] for key in ("home_goals", "away_goals")}, "calibration labels changed")
        require(row["outcome_indices"] == winners(**row["outcome"]), "calibration class labels wrong")
        for market in MARKETS:
            q = devig(row["odds"].get(market), market)
            require((market in row["market"]) == (q is not None), "calibration quote gate differs")
            if q is not None:
                for side, p in zip(SIDES[market], q):
                    near(row["market"][market][side], p, "calibration devig")
    weights_checked = {}
    for market, sides in SIDES.items():
        panel = [row for row in calibration_rows if market in row["market"]]
        verify_training_times(panel, set(evaluation), history)
        require(fit["weights"][market]["event_ids"] == [row["event_id"] for row in panel], "weight fit IDs mismatch")
        samples = [{"model": [row["probabilities"][market][side] for side in sides],
                    "market": [row["market"][market][side] for side in sides],
                    "outcome": row["outcome_indices"][market]} for row in panel]
        checked = verify_weight(samples, market, fit["weights"][market]["weight"])
        require(fit["weights"][market]["n"] == checked["n"], "weight sample size differs")
        weights_checked[market] = checked

    forecasts = index_rows(artifacts["forecasts.json"])
    panel = index_rows(artifacts["panel.json"])
    require(set(forecasts) == set(evaluation) == set(panel), "forecast/panel universe mismatch")
    changed_ids = []
    raw_change_magnitudes = []
    for event_id, forecast in forecasts.items():
        target = history[event_id]
        expected_ids, n_home, n_away = expected_history_ids(target, history)
        for kind in ("raw", "calibrated"):
            values = forecast[kind]
            verify_feature_history(values, history)
            require(clock(values["decision_at"]) == clock(target["kickoff"]) - timedelta(minutes=60), "wrong forecast decision time")
            require(values["history_ids"] == expected_ids, "forecast feature window differs")
            require((values["n_home"], values["n_away"]) == (n_home, n_away), "forecast history counts differ")
            require(values["eligible"] == (n_home >= 3 and n_away >= 3), "history eligibility differs")
            if not values["eligible"]:
                require(values["probabilities"] == {}, "ineligible forecast publishes probabilities")
        raw, old_raw = forecast["raw"], old_forecasts[event_id]["raw"]
        changed = raw["eligible"] != old_raw["eligible"] or raw["probabilities"] != old_raw["probabilities"]
        require(panel[event_id]["quarantine_changed_raw"] == changed, "change flag mismatch")
        if changed:
            changed_ids.append(event_id)
            if raw["eligible"] and old_raw["eligible"]:
                magnitude = max(abs(raw["probabilities"][market][side] - old_raw["probabilities"][market][side]) for market in MARKETS for side in SIDES[market])
                raw_change_magnitudes.append({"event_id": event_id, "max_probability_change": magnitude})
        require(not changed or event_id in plan["potentially_affected_2025_ids"], "quarantine changed an unrelated event")
        expected_markets = {market: q for market in MARKETS if raw["eligible"] and (q := devig(target["odds"].get(market), market)) is not None}
        require(set(forecast["market"]) == set(expected_markets), "forecast quote gate differs")
        for market, q in expected_markets.items():
            for side, value in zip(SIDES[market], q):
                near(forecast["market"][market][side], value, "forecast devig")
        primary_exists = len(expected_markets) == 3
        require(bool(forecast["primary_probabilities"]) == primary_exists, "primary eligibility differs")
        if primary_exists:
            for market, sides in SIDES.items():
                weight = fit["weights"][market]["weight"]
                for side, q in zip(sides, expected_markets[market]):
                    p = raw["probabilities"][market][side]
                    near(forecast["primary_probabilities"][market][side], q + weight * (p - q), "blended forecast")
        expected_common = event_id in old_panel and primary_exists and forecast["calibrated"]["eligible"]
        require(panel[event_id]["common"] == expected_common and panel[event_id]["original_common"] == (event_id in old_panel), "comparison panel membership differs")

    common_ids = {event_id for event_id, row in panel.items() if row["common"]}
    full_rows = artifacts["original_panel_results.json"]
    rows = artifacts["event_results.json"]
    full_index, common_index = index_rows(full_rows), index_rows(rows)
    require(set(full_index) == old_panel and set(common_index) == common_ids, "scored populations differ")
    require(all(common_index[key] == full_index[key] for key in common_ids), "common records differ from original-panel records")
    require([row["event_id"] for row in full_rows] == sorted(old_panel, key=lambda key: (clock(history[key]["kickoff"]), key)), "economic records are not chronological")
    new_arms = ("quality_raw_market_blend", "quality_raw", "quality_rate_calibrated")
    controls = tuple(plan["controls"])
    arms = (*new_arms, *controls)
    checked_by_arm = {arm: {} for arm in arms}
    for event_id, record in full_index.items():
        original, forecast = old_events[event_id], forecasts[event_id]
        require(all(record[key] == original[key] for key in ("home", "away", "kickoff", "outcome", "odds")), "original event fields changed")
        for arm in controls:
            require(all(record[field][arm] == original[field][arm] for field in ("probabilities", "scores", "bets")), "frozen control changed")
        for arm, published in zip(new_arms, (forecast["primary_probabilities"], forecast["raw"]["probabilities"], forecast["calibrated"]["probabilities"])):
            require(record["probabilities"][arm] == published, "scored forecast differs from locked forecast")
        outcome = winners(**record["outcome"])
        for arm in arms:
            p = record["probabilities"][arm]
            selected = select_from_published(flatten_dict(p), record["odds"]) if p else None
            reported = record["bets"][arm]
            verify_candidate(reported["candidate"] if reported else None, selected, f"{event_id}/{arm}")
            paid = payment(selected, **record["outcome"])
            if selected is not None:
                require(reported["settlement"]["won"] is paid["won"], "winning selection settled as loss or reverse")
                for metric in ("stake_units", "gross_profit_units", "cost_units", "net_profit_units"):
                    near(reported["settlement"][metric], paid[metric], "settlement")
            computed_scores = None
            if p:
                vectors = vectors_from_dict(p)
                computed_scores = {market: dict(zip(("brier", "log_loss"), scores(vectors[market], outcome[market], market))) for market in MARKETS}
                for market in MARKETS:
                    for metric, expected in computed_scores[market].items():
                        near(record["scores"][arm][market][metric], expected, f"{event_id}/{arm}/{market}/{metric}")
            else:
                require(record["scores"][arm] is None, "abstention without forecast received a score")
            checked_by_arm[arm][event_id] = {"event_id": event_id, "candidate": selected, "payment": paid, "scores": computed_scores}

    result = artifacts["results.json"]
    require(result["plan_sha256"] == EXPECTED_PLAN_SHA256, "result used another plan")
    require(result["coverage"]["new_common"] == len(common_ids) and result["coverage"]["original_common"] == len(old_panel), "coverage aggregate mismatch")
    require(result["coverage"]["additional_excluded_ids"] == sorted(old_panel - common_ids), "excluded IDs mismatch")
    require(result["coverage"]["changed_raw_ids"] == changed_ids, "changed raw IDs mismatch")
    economic_checks, probability_checks = {}, {}
    for arm in arms:
        common_checked = [checked_by_arm[arm][row["event_id"]] for row in rows]
        full_checked = [checked_by_arm[arm][row["event_id"]] for row in full_rows]
        economic_checks[arm] = summarize_checked(common_checked)
        for field, expected in economic_checks[arm].items():
            near(result["economics_common"][arm][field], expected, f"common economics {arm}.{field}")
        for field, expected in summarize_checked(full_checked).items():
            near(result["economics_original_panel_with_explicit_abstentions"][arm][field], expected, f"original economics {arm}.{field}")
        probability_checks[arm] = {}
        for market in MARKETS:
            probability_checks[arm][market] = {}
            for metric in ("brier", "log_loss"):
                expected = math.fsum(row["scores"][market][metric] for row in common_checked) / len(common_checked)
                near(result["probabilistic_common"][arm][market][metric], expected, "common score aggregate")
                probability_checks[arm][market][metric] = expected
    primary = new_arms[0]
    transition_checks = {}
    for control in controls:
        transition_checks[control] = {}
        for population, ids in (("common", common_ids), ("original", old_panel)):
            transition_checks[control][population] = transitions({key: checked_by_arm[control][key] for key in ids}, {key: checked_by_arm[primary][key] for key in ids})
            difference = math.fsum(group["difference"] for group in transition_checks[control][population].values())
            expected = math.fsum(checked_by_arm[primary][key]["payment"]["net_profit_units"] - checked_by_arm[control][key]["payment"]["net_profit_units"] for key in ids)
            near(difference, expected, "transition reconciliation")
    quarantine_changed_selection = [key for key in common_ids if
                                    checked_by_arm["quality_raw"][key]["candidate"] != checked_by_arm["xg_raw_diagnostic"][key]["candidate"]]
    # Probability metadata can change with an identical selection, price and payment.
    quarantine_changed_identity = [key for key in quarantine_changed_selection if
                                  (None if checked_by_arm["quality_raw"][key]["candidate"] is None else
                                   tuple(checked_by_arm["quality_raw"][key]["candidate"][field] for field in ("market", "side_index", "odd"))) !=
                                  (None if checked_by_arm["xg_raw_diagnostic"][key]["candidate"] is None else
                                   tuple(checked_by_arm["xg_raw_diagnostic"][key]["candidate"][field] for field in ("market", "side_index", "odd")))]
    return {"status": "PASS_INDEPENDENT_ARITHMETIC_AND_PROVENANCE_AUDIT", "plan_sha256": EXPECTED_PLAN_SHA256,
            "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "artifact_sha256": hashes,
            "checks": {"new_fit_or_backtest_executed": False, "model_fit_modules_imported": False,
                       "weights_decimal_precision": 50, "no_2025_ids_in_calibration": True,
                       "feature_windows_quarantined_and_strictly_prior": True, "rate_calibration_2024_equal": True,
                       "all_published_decisions_payments_and_scores_verified": True,
                       "bootstrap_interval_recalculated": False},
            "coverage": {"universe": len(evaluation), "original_common": len(old_panel), "new_common": len(common_ids), "additional_excluded_ids": sorted(old_panel-common_ids)},
            "weights": weights_checked, "economics_common": economic_checks, "probabilistic_common": probability_checks,
            "quarantine": {"changed_raw_ids": changed_ids, "probability_changes_where_both_eligible": raw_change_magnitudes,
                           "changed_selection_identity_on_common": sorted(quarantine_changed_identity)},
            "primary_vs_controls_transitions": transition_checks,
            "limits": ["2025 was already explored; this audit is not independent predictive validation.",
                       "The48-hour availability lag and retrospective prices remain unattested.",
                       "An audit pass verifies calculations and recorded provenance, not real-world profitability."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="explicit CORRECAO artifact directory")
    parser.add_argument("--output", type=Path, required=True, help="new audit JSON; refuses overwrite")
    args = parser.parse_args()
    result = audit_artifacts(args.directory)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
