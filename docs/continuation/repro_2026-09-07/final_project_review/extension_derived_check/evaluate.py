"""Frozen historical price extension, with no fitting or football outcomes.

The secondary diagnostic is a price-reference proxy only: it does not estimate
true expected value, accepted execution, settlement, ROI, P&L, or CLV.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

WORK = Path(__file__).resolve().parent
PREVIOUS = WORK.parent / "selection_reanalysis"
SOURCE_REPLAY = PREVIOUS / "price_discovery_replay.py"
SPEC = importlib.util.spec_from_file_location("frozen_price_reconstruction", SOURCE_REPLAY)
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)

BETA = -0.31988646513691255
SELECTED_N = 51
MINIMUM_COMPLETE = 30
PROXY_THRESHOLD = 0.02
PROXY_COST_SCENARIO = 0.02
MODELS = ("persistence", "frozen_ridge_momentum")
EXPECTED = {
    "selected_n": SELECTED_N,
    "beta": BETA,
    "bookmaker": "pinnacle",
    "new_fits": 0,
    "models": list(MODELS),
    "market": "1X2",
    "side_order": ["home", "draw", "away"],
    "feature_cutoffs": ["T6H", "T1H"],
    "target_cutoff": "T10M",
    "decimal_odds_range": [1.01, 20.0],
    "complete_vector_overround_range": [0.99, 1.30],
    "oldest_leg_max_age_hours": 6,
    "minimum_complete_test_events": MINIMUM_COMPLETE,
}


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_plan(plan: dict[str, Any]) -> None:
    for key, value in EXPECTED.items():
        if plan.get(key) != value:
            raise ValueError(f"Frozen plan differs from implementation: {key}")
    if plan.get("secondary_price_proxy", {}).get("threshold") != PROXY_THRESHOLD:
        raise ValueError("Frozen price proxy threshold differs from implementation")
    if plan.get("secondary_price_proxy", {}).get("cost_scenario") != PROXY_COST_SCENARIO:
        raise ValueError("Frozen price proxy cost scenario differs from implementation")
    # These are imported from the hash-verified original reconstruction module.
    if (replay.MIN_ODDS, replay.MAX_ODDS, replay.MIN_BOOKSUM, replay.MAX_BOOKSUM,
            replay.MAX_AGE_SECONDS, replay.FLOOR) != (1.01, 20.0, 0.99, 1.30, 21600, 1e-6):
        raise ValueError("Original reconstruction constants have changed")


def validate_selection(selection: list[dict[str, Any]], previous_ids: set[str],
                       training_latest_target_at: str, *, expected_n: int = SELECTED_N) -> list[datetime]:
    if not isinstance(selection, list) or len(selection) != expected_n:
        raise ValueError("Selection must contain the complete frozen number of events")
    ids = [str(row["fixture_id"]) for row in selection]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate selected fixture ID")
    if set(ids) & previous_ids:
        raise ValueError("Previously selected fixture cannot enter the extension")
    if any(not fixture_id or Path(fixture_id).name != fixture_id or "/" in fixture_id or "\\" in fixture_id
           for fixture_id in ids):
        raise ValueError("Unsafe fixture ID")
    kickoffs = [replay.dt(row["kickoff_at"]) for row in selection]
    if kickoffs != sorted(kickoffs):
        raise ValueError("Selection order must be chronological")
    latest_target = replay.dt(training_latest_target_at)
    for kickoff in kickoffs:
        if not datetime(2026, 1, 1, tzinfo=UTC) <= kickoff < datetime(2026, 7, 1, tzinfo=UTC):
            raise ValueError("Only January through June 2026 is allowed")
        if kickoff - timedelta(hours=1) <= latest_target:
            raise ValueError("Every decision must be strictly after the last training target")
    return kickoffs


def predict(features: dict[str, Any]) -> dict[str, np.ndarray]:
    """Only T6H and T1H are accessed; target cannot influence a forecast."""
    q6 = np.asarray(features["T6H"]["q"], dtype=float)
    q1 = np.asarray(features["T1H"]["q"], dtype=float)
    return {"persistence": replay.normalized(q1),
            "frozen_ridge_momentum": replay.normalized(q1 + BETA * (q1 - q6))}


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "persistence_mean_mse": None, "frozen_ridge_momentum_mean_mse": None,
                "paired_mean_mse_delta": None, "relative_mse_reduction": None,
                "events_lower_mse": 0, "events_equal_mse": 0, "events_higher_mse": 0}
    baseline = np.asarray([row["losses"]["persistence"] for row in rows])
    candidate = np.asarray([row["losses"]["frozen_ridge_momentum"] for row in rows])
    delta = candidate - baseline
    base_mean = float(np.mean(baseline))
    candidate_mean = float(np.mean(candidate))
    return {"n": len(rows), "persistence_mean_mse": base_mean,
            "frozen_ridge_momentum_mean_mse": candidate_mean,
            "paired_mean_mse_delta": float(np.mean(delta)),
            "relative_mse_reduction": 1 - candidate_mean / base_mean if base_mean > 0 else None,
            "events_lower_mse": int(np.sum(delta < 0)),
            "events_equal_mse": int(np.sum(delta == 0)),
            "events_higher_mse": int(np.sum(delta > 0))}


def secondary_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    signals = [row for row in records if row["secondary_price_proxy"]["status"].startswith("SIGNAL_")]
    observed = [row["secondary_price_proxy"] for row in signals
                if row["secondary_price_proxy"]["status"] == "SIGNAL_TARGET_AVAILABLE"]
    return {
        "selected_n": len(records),
        "feature_eligible_n": sum(row["features_eligible"] for row in records),
        "no_signal_n": sum(row["secondary_price_proxy"]["status"] == "NO_SIGNAL" for row in records),
        "signal_n": len(signals),
        "signal_target_available_n": len(observed),
        "signal_target_missing_n": len(signals) - len(observed),
        "observed_reference_proxy_mean": float(np.mean([r["observed_reference_proxy"] for r in observed])) if observed else None,
        "after_cost_scenario_proxy_mean": float(np.mean([r["after_cost_scenario_proxy"] for r in observed])) if observed else None,
        "observed_reference_proxy_positive_n": sum(r["observed_reference_proxy"] > 0 for r in observed),
        "after_cost_scenario_proxy_positive_n": sum(r["after_cost_scenario_proxy"] > 0 for r in observed),
        "economic_evidence": False,
    }


def evaluate(selection: list[dict[str, Any]], histories: dict[str, Any], *,
             previous_ids: set[str], training_latest_target_at: str,
             expected_n: int = SELECTED_N) -> dict[str, Any]:
    kickoffs = validate_selection(selection, previous_ids, training_latest_target_at, expected_n=expected_n)
    ids = [str(row["fixture_id"]) for row in selection]
    if set(histories) - set(ids):
        raise ValueError("A history outside the fixed selection was supplied")
    records, complete = [], []
    for fixture, kickoff in zip(selection, kickoffs, strict=True):
        fixture_id = str(fixture["fixture_id"])
        raw = histories.get(fixture_id)
        if isinstance(raw, dict) and "historyraw" in raw:
            raw = raw["historyraw"]
        if raw is None:
            identity_reason = "HISTORY_NOT_AVAILABLE"
        elif not isinstance(raw, dict) or str(raw.get("fixtureId", "")) != fixture_id:
            identity_reason = "HISTORY_FIXTURE_ID_MISMATCH"
        else:
            identity_reason = None
        books = raw.get("bookmakers", {}) if isinstance(raw, dict) and identity_reason is None else {}
        if not isinstance(books, dict):
            books = {}
        snapshots = {window: replay.market_snapshot(books.get("pinnacle"), kickoff - lead, kickoff)
                     for window, lead in replay.WINDOWS.items()}
        if identity_reason:
            snapshots = {window: {"eligible": False, "reasons": [identity_reason]} for window in replay.WINDOWS}
        feature_reasons = [f"{window}:{reason}" for window in ("T6H", "T1H")
                           for reason in snapshots[window]["reasons"]]
        target_reasons = snapshots["T10M"]["reasons"]
        feature_ok = all(snapshots[window]["eligible"] for window in ("T6H", "T1H"))
        target_ok = snapshots["T10M"]["eligible"]
        record = {"fixture_id": fixture_id, "kickoff_at": replay.stamp(kickoff),
                  "decision_at": replay.stamp(kickoff - timedelta(hours=1)),
                  "target_at": replay.stamp(kickoff - timedelta(minutes=10)),
                  "features_eligible": feature_ok, "target_eligible": target_ok,
                  "paired_mse_eligible": feature_ok and target_ok,
                  "feature_exclusion_reasons": feature_reasons,
                  "target_exclusion_reasons": target_reasons,
                  "snapshots": snapshots, "forecasts": None, "losses": None,
                  "secondary_price_proxy": {"status": "FEATURES_UNAVAILABLE"}}
        if feature_ok:
            forecasts = predict(snapshots)
            record["forecasts"] = {name: value.tolist() for name, value in forecasts.items()}
            # Choose once from features, before checking target availability.
            prices = snapshots["T1H"]["odds"]
            predicted_proxy = forecasts["frozen_ridge_momentum"] * np.asarray(prices) - 1
            selected = int(np.argmax(predicted_proxy))  # Fixed home, draw, away order.
            proxy = {"status": "NO_SIGNAL", "best_predicted_reference_proxy": float(predicted_proxy[selected])}
            if predicted_proxy[selected] > PROXY_THRESHOLD:
                proxy.update(status="SIGNAL_TARGET_MISSING", side=replay.SIDES[selected],
                             quoted_odds_T1H=prices[selected], predicted_reference_q=float(forecasts["frozen_ridge_momentum"][selected]))
                if target_ok:
                    observed_proxy = snapshots["T10M"]["q"][selected] * prices[selected] - 1
                    proxy.update(status="SIGNAL_TARGET_AVAILABLE", observed_reference_proxy=observed_proxy,
                                 after_cost_scenario_proxy=observed_proxy - PROXY_COST_SCENARIO)
            record["secondary_price_proxy"] = proxy
            if target_ok:
                target = np.asarray(snapshots["T10M"]["q"])
                record["losses"] = {name: float(np.mean((value - target) ** 2)) for name, value in forecasts.items()}
                complete.append(record)
        records.append(record)

    metrics = aggregate(complete)
    if metrics["n"] < MINIMUM_COMPLETE:
        status = "INSUFFICIENT_DATA"
    elif metrics["paired_mean_mse_delta"] < 0:
        status = "OBSERVED_LOWER_PRICE_PREDICTION_ERROR"
    else:
        status = "OBSERVED_NOT_LOWER_PRICE_PREDICTION_ERROR"
    months = sorted({row["kickoff_at"][:7] for row in records})
    monthly = {month: {"metrics": aggregate([row for row in complete if row["kickoff_at"].startswith(month)]),
                       "secondary_price_proxy": secondary_summary([row for row in records if row["kickoff_at"].startswith(month)])}
               for month in months}
    loo = []
    if len(complete) >= 2:
        for excluded in complete:
            remainder = aggregate([row for row in complete if row["fixture_id"] != excluded["fixture_id"]])
            loo.append({"removed_fixture_id": excluded["fixture_id"],
                        "paired_mean_mse_delta": remainder["paired_mean_mse_delta"],
                        "relative_mse_reduction": remainder["relative_mse_reduction"]})
    reason_counts = Counter(reason for row in records for reason in row["feature_exclusion_reasons"])
    return {
        "schema_version": "frozen-price-extension/1",
        "status": status, "selected_n": len(records), "fixed_beta": BETA,
        "new_training_events": 0, "minimum_complete_test_events": MINIMUM_COMPLETE,
        "primary_metrics": metrics,
        "coverage": {"feature_eligible_n": sum(row["features_eligible"] for row in records),
                     "target_eligible_n": sum(row["target_eligible"] for row in records),
                     "paired_mse_eligible_n": len(complete),
                     "feature_exclusion_reason_counts": dict(reason_counts)},
        "secondary_price_proxy": secondary_summary(records),
        "monthly": monthly,
        "leave_one_event_out": {"refitting": False, "observations": loo,
            "paired_delta_min": min(row["paired_mean_mse_delta"] for row in loo) if loo else None,
            "paired_delta_max": max(row["paired_mean_mse_delta"] for row in loo) if loo else None},
        "records": records,
        "confirmation": False, "economic_evidence": False,
        "limitations": [
            "This extension was chosen after the earlier exploratory result; it is not a blind confirmation.",
            "No model fitting, coefficient updates, football outcomes, settlement, ROI, P&L, or CLV are used.",
            "The target is a normalized bookmaker price reference, not the true probability of the football outcome.",
            "The secondary diagnostic uses one feature-selected side and accounts separately for unavailable targets.",
            "The 2% deduction is a fixed proxy scenario, not measured costs or proof of execution.",
            "Per-selection states do not reconstruct global historical suspensions or establish executable quotes.",
            "Last recorded state age is not original quote age, network latency, or proof of availability.",
            "Monthly and leave-one-event results are descriptive; no formal confidence interval or multiple-search correction is claimed.",
        ],
    }


def validate_sources(plan: dict[str, Any], selection_bytes: bytes,
                     previous_bytes: bytes, universe_bytes: bytes,
                     pinnacle_results_bytes: bytes) -> tuple[set[str], str]:
    validate_plan(plan)
    materials = {
        "selection_file_sha256": selection_bytes,
        "source_replay_sha256": SOURCE_REPLAY.read_bytes(),
        "source_pinnacle_results_sha256": pinnacle_results_bytes,
        "source_universe_sha256": universe_bytes,
        "excluded_previous_selection_file_sha256": previous_bytes,
    }
    for key, content in materials.items():
        if plan.get(key) != sha(content):
            raise ValueError(f"Source does not match frozen plan: {key}")
    previous = json.loads(previous_bytes)
    universe = json.loads(universe_bytes)
    pinnacle_results = json.loads(pinnacle_results_bytes)
    if pinnacle_results["ridge_beta"] != BETA:
        raise ValueError("Frozen coefficient does not match original result")
    previous_ids = {str(row["fixture_id"]) for row in previous}
    if len(previous) != 30 or len(previous_ids) != 30:
        raise ValueError("Exactly all thirty previous selected fixtures must be excluded")
    train_ids = pinnacle_results["training_ids"]
    if len(train_ids) != 13 or len(set(train_ids)) != 13:
        raise ValueError("Original frozen candidate must have thirteen training events")
    if not set(train_ids).issubset(previous_ids):
        raise ValueError("Training event is missing from previous selection")
    rows = {str(row["fixture_id"]): row for row in universe}
    if len(rows) != len(universe):
        raise ValueError("Source universe contains duplicate fixtures")
    training = [rows[fixture_id] for fixture_id in train_ids]
    times = [replay.dt(row["kickoff_at"]) - timedelta(minutes=10) for row in training]
    latest = max(times)
    if replay.dt(plan["training_latest_target_at"]) != latest:
        raise ValueError("Plan training boundary does not match the source training targets")
    eligible = {fixture_id for fixture_id, row in rows.items()
                if fixture_id not in previous_ids and replay.dt(row["kickoff_at"]) - timedelta(hours=1) > latest}
    selected = json.loads(selection_bytes)
    if {str(row["fixture_id"]) for row in selected} != eligible:
        raise ValueError("Selection is not all unused temporally eligible universe fixtures")
    if any(row != rows[str(row["fixture_id"])] for row in selected):
        raise ValueError("Selected metadata differs from the frozen source universe")
    return previous_ids, replay.stamp(latest)


def compact_history(raw: Any) -> Any:
    """Retain identity and the declared market only, preserving malformed states."""
    if isinstance(raw, dict) and "historyraw" in raw:
        raw = raw["historyraw"]
    if not isinstance(raw, dict):
        return raw
    books = raw.get("bookmakers")
    if not isinstance(books, dict):
        return {"fixtureId": raw.get("fixtureId"), "bookmakers": books}
    pinnacle = books.get("pinnacle")
    if isinstance(pinnacle, dict):
        markets = pinnacle.get("markets")
        if isinstance(markets, dict):
            markets = {"101": markets["101"]} if "101" in markets else {}
        pinnacle = {"markets": markets}
    return {"fixtureId": raw.get("fixtureId"), "bookmakers": {"pinnacle": pinnacle}}


def load_histories(selection: list[dict[str, Any]], raw_directory: Path,
                   manifest: dict[str, Any], plan_bytes: bytes) -> tuple[dict[str, Any], dict[str, str]]:
    if manifest.get("plan_file_sha256_before_first_request") != sha(plan_bytes):
        raise ValueError("Acquisition did not freeze this plan before the first request")
    if not manifest.get("finished_at"):
        raise ValueError("Acquisition must be complete before evaluation")
    selected_ids = [str(row["fixture_id"]) for row in selection]
    attempts = manifest["records"]
    attempt_ids = [str(row["fixture_id"]) for row in attempts]
    if attempt_ids != selected_ids[:len(attempt_ids)] or len(set(attempt_ids)) != len(attempt_ids):
        raise ValueError("Acquisition must follow the fixed selection once, in order")
    status = manifest.get("status")
    if status == "COMPLETE_NO_RETRIES":
        if attempt_ids != selected_ids:
            raise ValueError("Completed acquisition has unaccounted fixtures")
    elif status == "STOP_PROVIDER_ERROR_NO_RETRY":
        codes = [record.get("http_status") for record in attempts]
        if not codes or not (codes[-1] in (401, 402, 403) or codes[-3:] == [429, 429, 429]):
            raise ValueError("Acquisition stopping reason does not follow the frozen provider rule")
    else:
        raise ValueError("Acquisition is incomplete, running, or failed its integrity checks")
    if manifest.get("attempted_count") != len(attempts) or manifest.get("unattempted_count") != len(selected_ids) - len(attempts):
        raise ValueError("Acquisition denominator counts are inconsistent")
    raw_directory = raw_directory.resolve()
    expected_files = {f"{fixture_id}.json" for fixture_id in selected_ids}
    if {path.name for path in raw_directory.glob("*.json")} - expected_files:
        raise ValueError("Unexpected raw file outside the fixed selection")
    if any((raw_directory / f"{fixture_id}.json").exists() for fixture_id in selected_ids[len(attempt_ids):]):
        raise ValueError("Raw file exists for a fixture that was never attempted")
    histories, hashes = {}, {}
    for record in attempts:
        fixture_id = str(record["fixture_id"])
        raw_path = (raw_directory / f"{fixture_id}.json").resolve()
        if raw_path.parent != raw_directory:
            raise ValueError("Unsafe raw fixture path")
        success = record.get("http_status") == 200 and bool(record.get("sha256"))
        if not success:
            if raw_path.exists():
                raise ValueError("Raw file exists despite unsuccessful acquisition record")
            continue
        content = raw_path.read_bytes()
        if sha(content) != record["sha256"]:
            raise ValueError("Raw content hash does not match acquisition record")
        histories[fixture_id] = compact_history(json.loads(content))
        hashes[fixture_id] = sha(content)
    return histories, hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=WORK / "plan.json")
    parser.add_argument("--selection", type=Path, default=WORK / "selection.json")
    parser.add_argument("--raw-dir", type=Path, default=WORK / "raw")
    parser.add_argument("--acquisition-manifest", type=Path, default=WORK / "acquisition_manifest.json")
    parser.add_argument("--source-universe", type=Path, default=PREVIOUS / "price_history" / "fixture_universe_jan_jun_2026.json")
    parser.add_argument("--source-pinnacle-results", type=Path, default=PREVIOUS / "pinnacle_only_results.json")
    parser.add_argument("--previous-selection", type=Path, default=PREVIOUS / "price_history" / "fixture_selection_30.json")
    parser.add_argument("--output", type=Path, default=WORK / "result.json")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(WORK) or output.exists():
        parser.error("Use a new output path within the extension work directory")
    # Validate frozen sources and metadata before loading any new price history.
    plan_bytes, selection_bytes = args.plan.read_bytes(), args.selection.read_bytes()
    plan, selection = json.loads(plan_bytes), json.loads(selection_bytes)
    previous_ids, latest_target = validate_sources(plan, selection_bytes, args.previous_selection.read_bytes(),
        args.source_universe.read_bytes(), args.source_pinnacle_results.read_bytes())
    validate_selection(selection, previous_ids, latest_target)
    manifest_bytes = args.acquisition_manifest.read_bytes()
    histories, hashes = load_histories(selection, args.raw_dir, json.loads(manifest_bytes), plan_bytes)
    report = evaluate(selection, histories, previous_ids=previous_ids, training_latest_target_at=latest_target)
    report["provenance"] = {
        "plan_sha256": sha(plan_bytes), "selection_sha256": sha(selection_bytes),
        "acquisition_manifest_sha256": sha(manifest_bytes), "raw_sha256_by_fixture_id": hashes,
        "script_sha256": sha(Path(__file__).read_bytes()), "source_replay_sha256": sha(SOURCE_REPLAY.read_bytes()),
        "training_latest_target_at": latest_target, "python": platform.python_version(), "numpy": np.__version__,
        "generated_at": replay.stamp(datetime.now(UTC)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "status": report["status"], "primary_metrics": report["primary_metrics"],
                      "secondary_price_proxy": report["secondary_price_proxy"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
