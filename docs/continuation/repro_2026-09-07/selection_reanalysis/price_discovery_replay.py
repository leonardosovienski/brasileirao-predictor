"""Fixed exploratory 1X2 price replay; synthetic tests precede any raw-data read.

No football outcomes, settlement, ROI, CLV, or capital calculations. The CLI
loads only the thirty IDs named in a separately fixed selection manifest. A
quote is the last known state of every leg at one replay cutoff; it is not a
claim that all three provider updates occurred simultaneously or were executable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np


WORK = Path(__file__).resolve().parent
BOOKS = ("pinnacle", "bet365")
SIDES = ("home", "draw", "away")
OUTCOME_IDS = ("101", "102", "103")
WINDOWS = {"T6H": timedelta(hours=6), "T1H": timedelta(hours=1), "T10M": timedelta(minutes=10)}
ALPHA = 1e-4
MIN_TRAIN = 10
MIN_TEST = 5
TRAIN_SELECTED_N = 20
SELECTED_N = 30
MAX_AGE_SECONDS = 6 * 3600
MIN_ODDS = 1.01
MAX_ODDS = 20.0
MIN_BOOKSUM = 0.99
MAX_BOOKSUM = 1.30
FLOOR = 1e-6
MODELS = ("persistence", "momentum_unit", "ridge_momentum", "ridge_momentum_cross")
PLAN = {
    "selected_n": SELECTED_N,
    "split": "first_20_selected_train_last_10_selected_test_before_any_missingness",
    "training_boundary_purge": "train_T10M_target_at_or_after_first_selected_test_T1H_decision",
    "books": list(BOOKS),
    "market": "1x2",
    "side_order": list(SIDES),
    "odds_range_inclusive": [MIN_ODDS, MAX_ODDS],
    "booksum_range_inclusive": [MIN_BOOKSUM, MAX_BOOKSUM],
    "oldest_leg_max_age_seconds": MAX_AGE_SECONDS,
    "age_semantics": "age_of_last_recorded_selection_state_not_original_price_or_network_latency",
    "cutoff_last_state_inclusive": True,
    "missing_or_inactive_or_same_timestamp_conflict": "reject_no_old_quote_resurrection",
    "interpolation": False,
    "devig": "proportional",
    "primary_target": "pinnacle_q_T10M",
    "primary_origin": "pinnacle_q_T1H",
    "models": list(MODELS),
    "ridge_alpha": ALPHA,
    "ridge_intercept": False,
    "ridge_coefficients": "shared_across_stacked_home_draw_away_coordinates",
    "forecast_transform": "clamp_each_coordinate_at_1e-6_then_normalize",
    "primary_panel": "common_full_features_pin_T6H_T1H_T10M_bet365_T1H",
    "minimum_complete_train": MIN_TRAIN,
    "minimum_complete_test": MIN_TEST,
    "loss": "mean_squared_error_over_three_coordinates_then_mean_over_events",
    "secondary_C": "largest_frozen_pin_T1H_q_times_bet365_T1H_odds_minus_one_above_0.02",
    "C_followup": "same_selection_last_active_bet365_state_at_T1H_plus_5_minutes",
    "C_retention": "frozen_pin_T1H_q_times_followup_bet365_odds_minus_one_above_0.02",
    "C_tie_break": "home_then_draw_then_away",
    "economic_evidence": False,
    "football_outcomes_used": False,
}


def dt(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp must be an ISO string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must contain a UTC offset")
    return parsed.astimezone(UTC)


def stamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def latest_selection(book: dict[str, Any], outcome_id: str, cutoff: datetime) -> tuple[dict[str, Any] | None, str | None]:
    """Last state first, validity second. Never filter active rows before ranking."""
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("Cutoff must be timezone-aware")
    try:
        timeline = book["markets"]["101"]["outcomes"][outcome_id]["players"]["0"]
    except (KeyError, TypeError):
        return None, "MISSING_SELECTION_HISTORY"
    if not isinstance(timeline, list):
        return None, "MALFORMED_SELECTION_HISTORY"
    eligible = []
    for row in timeline:
        if not isinstance(row, dict):
            return None, "MALFORMED_STATE"
        try:
            created_at = dt(row["createdAt"])
        except (KeyError, TypeError, ValueError, OverflowError):
            # Without a valid timestamp we cannot establish whether a state is future.
            return None, "INVALID_STATE_TIMESTAMP"
        if created_at <= cutoff:
            eligible.append((created_at, row))
    if not eligible:
        return None, "NO_STATE_AT_CUTOFF"
    latest_at = max(at for at, _row in eligible)
    latest = [row for at, row in eligible if at == latest_at]
    active_codes = {"true" if row.get("active") is True else "false" if row.get("active") is False else "unknown" for row in latest}
    if len(active_codes) != 1:
        return None, "CONFLICTING_STATE_AT_SAME_TIMESTAMP"
    if active_codes != {"true"}:
        return None, "INACTIVE_STATE" if active_codes == {"false"} else "ACTIVE_STATE_UNVERIFIED"
    prices = []
    for row in latest:
        price = row.get("price")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price):
            return None, "INVALID_LATEST_PRICE"
        prices.append(float(price))
    if len(set(prices)) != 1:
        return None, "CONFLICTING_STATE_AT_SAME_TIMESTAMP"
    price = prices[0]
    if not MIN_ODDS <= price <= MAX_ODDS:
        return None, "LATEST_PRICE_OUTSIDE_DECLARED_RANGE"
    age = (cutoff - latest_at).total_seconds()
    if age > MAX_AGE_SECONDS:
        return None, "STALE_SELECTION_OVER_6H"
    return {"odds": price, "state_at": stamp(latest_at), "age_seconds": age, "active": True}, None


def market_snapshot(book: dict[str, Any] | None, cutoff: datetime, kickoff: datetime) -> dict[str, Any]:
    if cutoff >= kickoff:
        return {"eligible": False, "reasons": ["CUTOFF_NOT_PRE_KICKOFF"]}
    if not isinstance(book, dict):
        return {"eligible": False, "reasons": ["MISSING_BOOKMAKER"]}
    legs, reasons = [], []
    for side, outcome_id in zip(SIDES, OUTCOME_IDS, strict=True):
        leg, reason = latest_selection(book, outcome_id, cutoff)
        if leg is None:
            reasons.append(f"{side}:{reason}")
        else:
            legs.append(leg)
    if reasons:
        return {"eligible": False, "reasons": reasons}
    odds = [leg["odds"] for leg in legs]
    implied = [1 / price for price in odds]
    booksum = sum(implied)
    if not MIN_BOOKSUM <= booksum <= MAX_BOOKSUM:
        return {"eligible": False, "reasons": ["BOOKSUM_OUTSIDE_DECLARED_RANGE"], "booksum": booksum}
    return {
        "eligible": True, "cutoff_at": stamp(cutoff), "odds": odds,
        "q": [probability / booksum for probability in implied], "booksum": booksum,
        "leg_state_at": [leg["state_at"] for leg in legs],
        "leg_age_seconds": [leg["age_seconds"] for leg in legs],
        "oldest_leg_age_seconds": max(leg["age_seconds"] for leg in legs),
        "reasons": [],
    }


def normalized(values: Any) -> np.ndarray:
    probabilities = np.asarray(values, dtype=float)
    if probabilities.shape != (3,) or not np.isfinite(probabilities).all():
        raise ValueError("Forecast must have three finite coordinates")
    probabilities = np.maximum(probabilities, FLOOR)
    return probabilities / probabilities.sum()


def fit_ridge(training: list[dict[str, Any]], *, cross: bool) -> np.ndarray:
    if len(training) < MIN_TRAIN:
        raise ValueError("Insufficient complete training events")
    feature_rows, targets = [], []
    for event in training:
        p6 = np.asarray(event["snapshots"]["pinnacle"]["T6H"]["q"])
        p1 = np.asarray(event["snapshots"]["pinnacle"]["T1H"]["q"])
        target = np.asarray(event["snapshots"]["pinnacle"]["T10M"]["q"])
        features = [p1 - p6]
        if cross:
            b1 = np.asarray(event["snapshots"]["bet365"]["T1H"]["q"])
            features.append(b1 - p1)
        feature_rows.extend(np.column_stack(features).tolist())
        targets.extend((target - p1).tolist())
    matrix = np.asarray(feature_rows, dtype=float)
    target = np.asarray(targets, dtype=float)
    return np.linalg.solve(matrix.T @ matrix + ALPHA * np.eye(matrix.shape[1]), matrix.T @ target)


def forecasts(event: dict[str, Any], coefficients: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Feature-only path; it never accesses the target T10M state."""
    p6 = np.asarray(event["snapshots"]["pinnacle"]["T6H"]["q"])
    p1 = np.asarray(event["snapshots"]["pinnacle"]["T1H"]["q"])
    b1 = np.asarray(event["snapshots"]["bet365"]["T1H"]["q"])
    momentum, cross = p1 - p6, b1 - p1
    return {
        "persistence": normalized(p1),
        "momentum_unit": normalized(p1 + momentum),
        "ridge_momentum": normalized(p1 + coefficients["ridge_momentum"][0] * momentum),
        "ridge_momentum_cross": normalized(p1 + coefficients["ridge_momentum_cross"][0] * momentum + coefficients["ridge_momentum_cross"][1] * cross),
    }


def _panel_reasons(event: dict[str, Any], requirements: tuple[tuple[str, str], ...]) -> list[str]:
    reasons = []
    for book, window in requirements:
        snapshot = event["snapshots"][book][window]
        if not snapshot["eligible"]:
            reasons.extend(f"{book}:{window}:{reason}" for reason in snapshot["reasons"])
    return reasons


def _secondary(event: dict[str, Any], books: dict[str, Any]) -> dict[str, Any]:
    reasons = _panel_reasons(event, (("pinnacle", "T1H"), ("bet365", "T1H")))
    base = {"fixture_id": event["fixture_id"], "split": event["split"], "decision_at": event["snapshots"]["pinnacle"]["T1H"].get("cutoff_at")}
    if reasons:
        return {**base, "status": "PAIR_INELIGIBLE", "reasons": reasons}
    p1 = event["snapshots"]["pinnacle"]["T1H"]["q"]
    b1 = event["snapshots"]["bet365"]["T1H"]["odds"]
    quoted_premiums = [probability * price - 1 for probability, price in zip(p1, b1, strict=True)]
    selected = max(range(3), key=lambda index: quoted_premiums[index])
    base.update({"selection": SIDES[selected], "reference_q_T1H": p1[selected], "quoted_odds_T1H": b1[selected], "quoted_proxy_premium_T1H": quoted_premiums[selected], "reference_oldest_leg_age_seconds": event["snapshots"]["pinnacle"]["T1H"]["oldest_leg_age_seconds"], "soft_oldest_leg_age_seconds": event["snapshots"]["bet365"]["T1H"]["oldest_leg_age_seconds"]})
    if quoted_premiums[selected] <= 0.02:
        return {**base, "status": "NO_QUOTED_PREMIUM_ABOVE_2PCT", "reasons": []}
    kickoff = dt(event["kickoff_at"])
    followup = kickoff - timedelta(minutes=55)
    if followup >= kickoff:
        return {**base, "status": "FOLLOWUP_INELIGIBLE", "reasons": ["FOLLOWUP_NOT_PRE_KICKOFF"]}
    leg, reason = latest_selection(books.get("bet365", {}), OUTCOME_IDS[selected], followup)
    if leg is None:
        return {**base, "status": "FOLLOWUP_UNAVAILABLE", "followup_at": stamp(followup), "reasons": [reason], "premium_retained_observed": False}
    followup_premium = p1[selected] * leg["odds"] - 1
    retained = followup_premium > 0.02
    return {**base, "status": "QUOTED_PREMIUM_RETAINED" if retained else "QUOTED_PREMIUM_NOT_RETAINED", "followup_at": stamp(followup), "followup_state_at": leg["state_at"], "followup_state_age_seconds": leg["age_seconds"], "followup_odds": leg["odds"], "quoted_proxy_premium_followup_frozen_reference": followup_premium, "premium_retained_observed": retained, "reasons": []}


def validate_selection(selection: list[dict[str, Any]]) -> tuple[list[str], list[datetime]]:
    if len(selection) != SELECTED_N:
        raise ValueError("The fixed selection must contain exactly thirty events")
    selected_ids = [str(fixture["fixture_id"]) for fixture in selection]
    if len(set(selected_ids)) != SELECTED_N:
        raise ValueError("Duplicate fixture ID in fixed selection")
    kickoffs = [dt(fixture["kickoff_at"]) for fixture in selection]
    if kickoffs != sorted(kickoffs):
        raise ValueError("Fixed selection order must be chronological")
    if any(not datetime(2026, 1, 1, tzinfo=UTC) <= kickoff < datetime(2026, 7, 1, tzinfo=UTC) for kickoff in kickoffs):
        raise ValueError("Only the approved January--June 2026 price population is allowed")
    return selected_ids, kickoffs


def evaluate(selection: list[dict[str, Any]], histories: dict[str, Any]) -> dict[str, Any]:
    selected_ids, kickoffs = validate_selection(selection)
    if set(histories) - set(selected_ids):
        raise ValueError("Histories contain an ID outside the fixed selection")
    first_test_decision = kickoffs[TRAIN_SELECTED_N] - WINDOWS["T1H"]
    purged_ids = {
        selected_ids[index] for index in range(TRAIN_SELECTED_N)
        if kickoffs[index] - WINDOWS["T10M"] >= first_test_decision
    }
    records, secondary = [], []
    for index, (fixture, kickoff) in enumerate(zip(selection, kickoffs, strict=True)):
        fixture_id = str(fixture["fixture_id"])
        raw = histories.get(fixture_id)
        if isinstance(raw, dict) and "historyraw" in raw:
            raw = raw["historyraw"]
        identity_error = isinstance(raw, dict) and str(raw.get("fixtureId", "")) != fixture_id
        if identity_error:
            books = {}
        elif isinstance(raw, dict) and isinstance(raw.get("bookmakers"), dict):
            books = raw["bookmakers"]
        else:
            books = {}
        snapshots = {book: {window: market_snapshot(books.get(book), kickoff - lead, kickoff) for window, lead in WINDOWS.items()} for book in BOOKS}
        if identity_error:
            for windows in snapshots.values():
                for snapshot in windows.values():
                    snapshot.update(eligible=False, reasons=["HISTORY_FIXTURE_ID_MISMATCH"])
        elif raw is None:
            for windows in snapshots.values():
                for snapshot in windows.values():
                    snapshot.update(eligible=False, reasons=["HISTORY_NOT_AVAILABLE"])
        record = {"fixture_id": fixture_id, "selection_position": index, "split": "train" if index < TRAIN_SELECTED_N else "test", "purged_training_boundary": fixture_id in purged_ids, "kickoff_at": stamp(kickoff), "snapshots": snapshots}
        records.append(record)
        secondary.append(_secondary(record, books))

    requirements = {
        "persistence": (("pinnacle", "T1H"), ("pinnacle", "T10M")),
        "momentum": (("pinnacle", "T6H"), ("pinnacle", "T1H"), ("pinnacle", "T10M")),
        "common_primary": (("pinnacle", "T6H"), ("pinnacle", "T1H"), ("pinnacle", "T10M"), ("bet365", "T1H")),
    }
    panels = {}
    for name, needed in requirements.items():
        included, excluded = [], []
        for record in records:
            reasons = _panel_reasons(record, needed)
            if reasons:
                excluded.append({"fixture_id": record["fixture_id"], "split": record["split"], "reasons": reasons})
            else:
                included.append(record["fixture_id"])
        panels[name] = {
            "selected_n": SELECTED_N, "eligible_n": len(included), "eligible_ids": included,
            "quote_complete_train_n": sum(record["split"] == "train" and record["fixture_id"] in included for record in records),
            "eligible_train_n": sum(record["split"] == "train" and record["fixture_id"] in included and record["fixture_id"] not in purged_ids for record in records),
            "eligible_test_n": sum(record["split"] == "test" and record["fixture_id"] in included for record in records),
            "excluded": excluded,
        }
    common = set(panels["common_primary"]["eligible_ids"])
    training = [record for record in records if record["split"] == "train" and record["fixture_id"] in common and record["fixture_id"] not in purged_ids]
    test = [record for record in records if record["split"] == "test" and record["fixture_id"] in common]
    complete = len(training) >= MIN_TRAIN and len(test) >= MIN_TEST
    primary: dict[str, Any] = {"status": "SUFFICIENT_FOR_DESCRIPTIVE_PILOT" if complete else "INSUFFICIENT_DATA", "train_n": len(training), "test_n": len(test), "purged_boundary_n": len(purged_ids), "purged_boundary_ids": [fixture_id for fixture_id in selected_ids[:TRAIN_SELECTED_N] if fixture_id in purged_ids], "first_selected_test_decision_at": stamp(first_test_decision), "minimum_train_n": MIN_TRAIN, "minimum_test_n": MIN_TEST, "coefficients": None, "model_metrics": None, "per_test_event": [], "interpretation": "exploratory_price_prediction_only_no_economic_or_confirmatory_claim"}
    if complete:
        coefficients = {"ridge_momentum": fit_ridge(training, cross=False), "ridge_momentum_cross": fit_ridge(training, cross=True)}
        primary["coefficients"] = {name: coefficient.tolist() for name, coefficient in coefficients.items()}
        losses: dict[str, list[float]] = {name: [] for name in MODELS}
        for record in test:
            predicted = forecasts(record, coefficients)
            target = np.asarray(record["snapshots"]["pinnacle"]["T10M"]["q"])
            per_model = {}
            for name in MODELS:
                mse = float(np.mean(np.square(predicted[name] - target)))
                losses[name].append(mse)
                per_model[name] = {"q_forecast": predicted[name].tolist(), "mse": mse}
            primary["per_test_event"].append({"fixture_id": record["fixture_id"], "target_q_pin_T10M": target.tolist(), "models": per_model})
        baseline = np.asarray(losses["persistence"])
        baseline_mean = float(np.mean(baseline))
        primary["model_metrics"] = {
            name: {"n": len(test), "mean_mse": float(np.mean(losses[name])), "paired_mean_mse_delta_vs_persistence": float(np.mean(np.asarray(losses[name]) - baseline)), "events_lower_mse_than_persistence": int(np.sum(np.asarray(losses[name]) < baseline)), "relative_mse_reduction_vs_persistence": (baseline_mean - float(np.mean(losses[name]))) / baseline_mean if baseline_mean > 0 else None}
            for name in MODELS
        }
    primary["target_movement_counts_on_common_panel"] = {}
    for split_name, subset in (("train_after_boundary_purge", training), ("test", test)):
        unchanged = sum(np.allclose(record["snapshots"]["pinnacle"]["T1H"]["q"], record["snapshots"]["pinnacle"]["T10M"]["q"], rtol=0, atol=1e-12) for record in subset)
        primary["target_movement_counts_on_common_panel"][split_name] = {"n": len(subset), "q_unchanged_n": int(unchanged), "q_changed_n": len(subset) - int(unchanged), "equality_absolute_tolerance": 1e-12}

    c_summary = {}
    for split in ("train", "test"):
        subset = [row for row in secondary if row["split"] == split]
        paired = [row for row in subset if row["status"] != "PAIR_INELIGIBLE"]
        candidates = [row for row in paired if row["quoted_proxy_premium_T1H"] > 0.02]
        known_followups = [row for row in candidates if row["status"] in ("QUOTED_PREMIUM_RETAINED", "QUOTED_PREMIUM_NOT_RETAINED")]
        c_summary[split] = {
            "selected_n": len(subset), "paired_quote_n": len(paired), "quoted_premium_candidates_n": len(candidates),
            "known_active_followup_n": len(known_followups),
            "observed_retained_n": sum(row["status"] == "QUOTED_PREMIUM_RETAINED" for row in candidates),
            "unavailable_followup_n": sum(row["status"] == "FOLLOWUP_UNAVAILABLE" for row in candidates),
        }
    c_enough = c_summary["train"]["paired_quote_n"] >= MIN_TRAIN and c_summary["test"]["paired_quote_n"] >= MIN_TEST
    return {
        "schema_version": "exploratory-price-replay/1", "plan": PLAN, "plan_sha256": canonical_hash(PLAN),
        "selection_ids_in_fixed_order": selected_ids, "coverage_panels": panels,
        "snapshot_coverage": {book: {window: {"valid_n": sum(record["snapshots"][book][window]["eligible"] for record in records), "selected_n": SELECTED_N} for window in WINDOWS} for book in BOOKS},
        "primary_B": primary,
        "secondary_C": {"status": "DESCRIPTIVE_QUOTES_ONLY" if c_enough else "INSUFFICIENT_DATA", "summary": c_summary, "observations": secondary, "not_measured": ["execution_acceptance", "true_expected_value", "football_results", "roi", "clv", "capital"], "reference_at_followup": "frozen_pinnacle_T1H_q", "full_three_leg_market_required_at_followup": False},
        "source_state_limitations": [
            "Activity is reconstructed from timestamped per-selection states only; historical global bookmaker or market suspension is not reconstructed.",
            "Current/global flags from a post-match payload are not allowed to invalidate or validate an earlier reconstructed state.",
            "createdAt identifies the last recorded state; it is not necessarily the original price age, publication latency, or executable-price timestamp.",
            "Three legs share the replay cutoff; their individual source update timestamps may differ.",
            "A quoted premium against an initial de-vigged reference is a proxy, not true expected value or evidence of accepted execution.",
        ],
        "snapshots": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--decision-record", required=True, type=Path)
    parser.add_argument("--plan", type=Path, default=WORK / "price_history" / "price_discovery_plan.json")
    parser.add_argument("--output", type=Path, default=WORK / "price_discovery_report.json")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(WORK) or output.exists():
        parser.error("Choose a new output path inside the isolated work namespace")
    # Decision record and ID manifest must exist before any raw price file is opened.
    decision_bytes = args.decision_record.read_bytes()
    selection_bytes = args.selection.read_bytes()
    plan_bytes = args.plan.read_bytes()
    frozen_plan = json.loads(plan_bytes)
    if frozen_plan.get("selection_file_sha256") != hashlib.sha256(selection_bytes).hexdigest():
        raise ValueError("Selection differs from the plan frozen before opening prices")
    expected = {
        "bookmakers": list(BOOKS), "decimal_odds_range": [MIN_ODDS, MAX_ODDS],
        "complete_vector_overround_range": [MIN_BOOKSUM, MAX_BOOKSUM],
        "oldest_leg_max_age_hours": MAX_AGE_SECONDS / 3600,
        "minimum_complete_training_events": MIN_TRAIN, "minimum_complete_test_events": MIN_TEST,
        "models": list(MODELS),
        "ridge": {"alpha": ALPHA, "intercept": False, "shared_coefficients_across_3_coordinates": True},
    }
    if any(frozen_plan.get(key) != value for key, value in expected.items()):
        raise ValueError("Frozen plan numeric settings differ from this implementation")
    selection = json.loads(selection_bytes)
    if not isinstance(selection, list) or len(selection) != SELECTED_N:
        raise ValueError("Selection must contain the thirty fixed fixture metadata records")
    validate_selection(selection)
    histories, hashes, missing = {}, {}, []
    raw_directory = args.raw_dir.resolve()
    for fixture in selection:
        fixture_id = str(fixture["fixture_id"])
        raw_path = (raw_directory / f"{fixture_id}.json").resolve()
        if raw_path.parent != raw_directory:
            raise ValueError("Fixture ID is not a safe filename")
        if not raw_path.is_file():
            missing.append(fixture_id)
            continue
        content = raw_path.read_bytes()
        hashes[fixture_id] = hashlib.sha256(content).hexdigest()
        histories[fixture_id] = json.loads(content)
    started = time.perf_counter()
    report = evaluate(selection, histories)
    report["provenance"] = {
        "decision_record_path": str(args.decision_record.resolve()), "decision_record_sha256": hashlib.sha256(decision_bytes).hexdigest(),
        "selection_path": str(args.selection.resolve()), "selection_sha256": hashlib.sha256(selection_bytes).hexdigest(),
        "frozen_plan_path": str(args.plan.resolve()), "frozen_plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "raw_file_sha256_by_fixture_id": hashes, "missing_raw_fixture_ids": missing,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": platform.python_version(), "numpy": np.__version__,
        "generated_at": stamp(datetime.now(UTC)), "evaluation_seconds": time.perf_counter() - started,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({"output": str(output), "primary_status": report["primary_B"]["status"], "train_n": report["primary_B"]["train_n"], "test_n": report["primary_B"]["test_n"], "secondary_status": report["secondary_C"]["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
