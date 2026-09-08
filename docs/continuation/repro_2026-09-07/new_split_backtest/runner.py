"""Single-fit replay under the frozen official-turn split. No operational writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import warnings
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from economics import MARKETS, Policy, evaluate_candidates, run_replay

WORK = Path(__file__).resolve().parent
REPO = Path("C:/Users/Superleo13/projetos/brasileirao-predictor")
PLAN_SHA = "5561ed31a36945d40e5ffe258dea5f07d890a8f677f57e463ccdb875e3d45f20"


def utc(value):
    if not isinstance(value, str) or not value:
        raise ValueError("A known timestamp is required for this frozen schedule")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Explicit timezone required")
    return dt.astimezone(UTC)


def serial(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(type(value).__name__)


def digest(obj):
    return hashlib.sha256(
        json.dumps(
            obj, sort_keys=True, separators=(",", ":"), allow_nan=False, default=serial
        ).encode()
    ).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite experiment artifact: {path}")
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False, default=serial)
        + "\n",
        encoding="utf-8",
    )


def features(row):
    """Explicit projection: never accesses result, xG or odds."""
    if not row["home"] or not row["away"] or row["home"] == row["away"]:
        raise ValueError("Invalid teams")
    if row.get("neutral", 0) not in (0, 1, False, True):
        raise ValueError("Invalid neutral flag")
    return {
        "home": row["home"],
        "away": row["away"],
        "kickoff": utc(row["kickoff"]),
        "date": row["date"],
        "tournament": row.get("tournament"),
        "city": row.get("city"),
        "neutral": int(bool(row.get("neutral", 0))),
    }


def model_state(ev):
    return {
        "elo": ev.elo,
        "params": ev.params,
        "xg_params": ev.xg_params,
        "trained_at": ev._trained_at,
        "dynamic_states": ev.dynamic_states,
        "pending_history": ev._pending_history,
        "blocked_observations": ev.blocked_observations,
        "deferred_refits": ev.deferred_refits,
        "xg_fit_failures": ev.xg_fit_failures,
    }


def probability_vectors(forecast):
    if not isinstance(forecast.get("p_1x2"), (list, tuple)):
        raise ValueError("Missing 1x2 forecast")
    scalars = [*forecast["p_1x2"], forecast.get("p_over25"), forecast.get("p_btts")]
    if any(
        type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
        for p in scalars
    ):
        raise ValueError("Invalid probability")
    values = {
        "1x2": list(forecast["p_1x2"]),
        "ou25": [forecast["p_over25"], 1 - forecast["p_over25"]],
        "btts": [forecast["p_btts"], 1 - forecast["p_btts"]],
    }
    for market, vector in values.items():
        if len(vector) != (3 if market == "1x2" else 2):
            raise ValueError("Probability vector length")
        if any(not math.isfinite(p) or not 0 <= p <= 1 for p in vector):
            raise ValueError("Invalid probability")
        if not math.isclose(math.fsum(vector), 1.0, abs_tol=1e-9):
            raise ValueError("Probability normalization")
    return values


def predict_frozen(ev, rows, expected_state_hash):
    forecasts = []
    for row in rows:
        if ev._pending_history is not None:
            raise AssertionError("Queued refit is prohibited")
        if ev._trained_at is None or ev._trained_at >= utc(row["kickoff"]):
            raise ValueError("Prediction requires strictly earlier training")
        predicted = ev.predict_step(features(row))
        forecast = {
            "event_id": row["event_id"],
            "p_1x2": [float(predicted.value[k]) for k in ("home", "draw", "away")],
            "p_over25": float(predicted.metadata["p_over"]),
            "p_btts": float(predicted.metadata["p_btts"]),
            "cold_start_teams": [
                row[k] for k in ("home", "away") if row[k] not in ev.elo
            ],
        }
        probability_vectors(forecast)
        forecasts.append(forecast)
    if digest(model_state(ev)) != expected_state_hash:
        raise AssertionError("Forecast generation changed trained model state")
    return forecasts


def outcome_indices(result):
    home, away = result["home_goals"], result["away_goals"]
    if any(type(v) is not int or v < 0 for v in (home, away)):
        raise ValueError("Invalid fulltime score")
    return {
        "1x2": 0 if home > away else 1 if home == away else 2,
        "ou25": 0 if home + away >= 3 else 1,
        "btts": 0 if home > 0 and away > 0 else 1,
    }


def market_q(quotes):
    inv = [1 / o for o in quotes]
    total = math.fsum(inv)
    return [p / total for p in inv]


def fit_calibrator(rows2025, forecasts2025, policy, minimum=200):
    if len(rows2025) != len(forecasts2025):
        raise ValueError("Calibration rows/forecast mismatch")
    samples = {m: [] for m in MARKETS}
    ids = set()
    for row, forecast in zip(rows2025, forecasts2025):
        if utc(row["kickoff"]).year != 2025 or str(row["date"])[:4] != "2025":
            raise ValueError("Calibration accepts only 2025")
        if row["event_id"] != forecast["event_id"] or row["event_id"] in ids:
            raise ValueError("Mismatched or duplicated calibration identity")
        ids.add(row["event_id"])
        probs = probability_vectors(forecast)
        winners = outcome_indices(row["result"])
        valid = evaluate_candidates(forecast, row["odds"], policy)["valid_markets"]
        for market in valid:
            p = probs[market]
            q = market_q(row["odds"][market])
            y = [int(k == winners[market]) for k in range(len(p))]
            samples[market].append((row["event_id"], row["kickoff"], p, q, y))
    result = {}
    for market, values in samples.items():
        numerator = math.fsum(
            (y[k] - q[k]) * (p[k] - q[k])
            for _, _, p, q, y in values
            for k in range(len(p))
        )
        denominator = math.fsum(
            (p[k] - q[k]) ** 2 for _, _, p, q, _ in values for k in range(len(p))
        )
        weight = (
            min(1.0, max(0.0, numerator / denominator)) if denominator > 1e-12 else 0.0
        )
        enabled = len(values) >= minimum
        result[market] = {
            "n": len(values),
            "enabled": enabled,
            "weight_model": weight if enabled else None,
            "numerator": numerator,
            "denominator": denominator,
            "last_kickoff": max((v[1] for v in values), default=None),
            "event_ids_sha256": digest([v[0] for v in values]),
            "brier_market_2025": math.fsum(
                (q[k] - y[k]) ** 2 for _, _, p, q, y in values for k in range(len(p))
            )
            / len(values)
            if values
            else None,
            "brier_raw_2025": math.fsum(
                (p[k] - y[k]) ** 2 for _, _, p, q, y in values for k in range(len(p))
            )
            / len(values)
            if values
            else None,
            "brier_calibrated_2025": math.fsum(
                (q[k] + weight * (p[k] - q[k]) - y[k]) ** 2
                for _, _, p, q, y in values
                for k in range(len(p))
            )
            / len(values)
            if enabled
            else None,
        }
    return result


def apply_calibrator(forecast, odds, calibration, policy):
    raw = probability_vectors(forecast)
    valid = evaluate_candidates(forecast, odds, policy)["valid_markets"]
    out = {"p_1x2": None, "p_over25": None, "p_btts": None}
    for market in valid:
        entry = calibration[market]
        if not entry["enabled"]:
            continue
        q, w = market_q(odds[market]), entry["weight_model"]
        p = [qi + w * (pi - qi) for qi, pi in zip(q, raw[market])]
        if market == "1x2":
            out["p_1x2"] = p
        else:
            out["p_over25" if market == "ou25" else "p_btts"] = p[0]
    return out


def execute(outdir):
    plan_path = WORK / "plan.json"
    if sha(plan_path) != PLAN_SHA:
        raise ValueError("Plan changed")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    history_path = (
        REPO / "data/research/season_2026_turn_split/historical_2021_2025.json"
    )
    if sha(history_path) != plan["data_sources"]["historical_sha256"]:
        raise ValueError("Historical source changed")
    if (
        sha(REPO / "config.yaml")
        != "a0ddbb4353839fc31231ac159fdc48a9e87378f43effb65b1f02dfb9642e6009"
    ):
        raise ValueError("Serving configuration changed")
    schedule_path = REPO / "data/research/season_2026_turn_split/schedule_manifest.json"
    if sha(schedule_path) != plan["data_sources"]["schedule_sha256"]:
        raise ValueError("Official schedule changed")
    schedule = json.loads(schedule_path.read_text(encoding="utf-8-sig"))
    if len(schedule) != 380 or any(not row.get("kickoff_at") for row in schedule):
        raise ValueError("This frozen replay requires the verified 380 known kickoffs")
    history = json.loads(history_path.read_text(encoding="utf-8-sig"))
    history.sort(key=lambda r: (utc(r["kickoff"]), str(r["event_id"])))
    counts = Counter(utc(r["kickoff"]).year for r in history)
    if (
        counts != {year: 380 for year in range(2021, 2026)}
        or len({r["event_id"] for r in history}) != 1900
    ):
        raise ValueError("Unexpected historical partition")
    train = [r for r in history if utc(r["kickoff"]).year in plan["training_years"]]
    calibrate = [r for r in history if utc(r["kickoff"]).year == 2025]
    sys.path.insert(0, str(REPO))
    import yaml
    from brasileirao_predictor import model
    from brasileirao_predictor.serving_evaluator import ServingStackEvaluator

    cfg = yaml.safe_load((REPO / "config.yaml").read_text(encoding="utf-8-sig"))
    if cfg["model"]["max_goals"] != 12 or cfg.get("ensemble_xg", {}).get("enabled"):
        raise ValueError("Unexpected serving config")
    source_paths = [
        "config.yaml",
        "brasileirao_predictor/serving_evaluator.py",
        "brasileirao_predictor/model.py",
        "brasileirao_predictor/ratings.py",
        "brasileirao_predictor/math_utils.py",
        "brasileirao_predictor/xg_model.py",
        "brasileirao_predictor/dynamic_strength.py",
    ]
    source_hashes = {p: sha(REPO / p) for p in source_paths}
    source_hashes.update(
        {p: sha(WORK / p) for p in ["runner.py", "economics.py", "extract_inputs.py"]}
    )
    outdir.mkdir(parents=True, exist_ok=True)
    if any(outdir.iterdir()):
        raise FileExistsError("Run output directory must be empty")
    ev = ServingStackEvaluator(cfg, max_goals=12)
    train_obs = [{**features(row), "result": row["result"]} for row in train]
    if any(row["kickoff"] >= utc(plan["training_horizon_utc"]) for row in train_obs):
        raise AssertionError("Future training row")
    optimizer_calls = []
    original_minimize = model.minimize

    def observed(*args, **kwargs):
        started = time.perf_counter()
        result = original_minimize(*args, **kwargs)
        optimizer_calls.append(
            {
                "method": kwargs.get("method"),
                "success": bool(result.success),
                "message": str(result.message),
                "seconds": time.perf_counter() - started,
            }
        )
        return result

    model.minimize = observed
    print("Training once on 1520 matches from 2021-2024", flush=True)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ev._fit(train_obs, utc(plan["training_horizon_utc"]))
    finally:
        model.minimize = original_minimize
    if optimizer_calls and not optimizer_calls[-1]["success"]:
        raise RuntimeError(
            "Final optimizer did not converge; no economic result permitted"
        )
    state = model_state(ev)
    state_hash = digest(state)
    forecasts25 = predict_frozen(ev, calibrate, state_hash)
    policy = Policy()
    calibration = fit_calibrator(
        calibrate,
        forecasts25,
        policy,
        plan["calibration"]["minimum_valid_events_per_market"],
    )
    candidate = {
        "plan_sha256": PLAN_SHA,
        "config": cfg,
        "model_state": state,
        "model_state_sha256": state_hash,
        "calibration_2025": calibration,
        "policy": asdict(policy),
        "source_sha256": source_hashes,
        "train_events": len(train),
        "calibration_events": len(calibrate),
        "train_event_ids_sha256": digest([r["event_id"] for r in train]),
        "train_first_kickoff": train[0]["kickoff"],
        "train_last_kickoff": train[-1]["kickoff"],
        "horizon_utc": plan["training_horizon_utc"],
        "fit_count": 1,
        "optimizer_calls": optimizer_calls,
        "fit_warnings": [
            {"category": w.category.__name__, "message": str(w.message)} for w in caught
        ],
    }
    candidate_hash = digest(candidate)
    save(outdir / "candidate.json", {"candidate_sha256": candidate_hash, **candidate})
    save(outdir / "forecasts_2025.json", forecasts25)
    print(
        json.dumps({"calibration": calibration, "candidate_sha256": candidate_hash}),
        flush=True,
    )
    # Candidate is persisted before 2026 outcomes or prices enter this runner.
    data_path = WORK / "data/canonical_input_2026.json"
    manifest = json.loads(
        (WORK / "data/extraction_manifest.json").read_text(encoding="utf-8")
    )
    if (
        sha(data_path) != manifest["canonical_input_sha256"]
        or manifest["plan_sha256"] != PLAN_SHA
    ):
        raise ValueError("Replay input/plan changed")
    events = json.loads(data_path.read_text(encoding="utf-8"))
    if len(events) != 380 or Counter(r["role"] for r in events) != {
        "test_exploratory": 190,
        "paper_betting": 190,
    }:
        raise ValueError("Official fixture denominator changed")
    forecasts26 = predict_frozen(ev, events, state_hash)
    replay_inputs = {arm: [] for arm in plan["arms"]}
    for row, raw in zip(events, forecasts26):
        result = row["result"] or {}
        for arm, arm_events in replay_inputs.items():
            forecast = (
                apply_calibrator(raw, row["odds"], calibration, policy)
                if arm == "primary_calibrated"
                else raw
            )
            arm_events.append(
                {
                    "id": row["event_id"],
                    "cbf_ref": row["cbf_ref"],
                    "round": row["round"],
                    "role": row["role"],
                    "home": row["home"],
                    "away": row["away"],
                    "kickoff_at": row["kickoff"],
                    "completion_state": row["completion_state"],
                    **{
                        key: forecast.get(key)
                        for key in ("p_1x2", "p_over25", "p_btts")
                    },
                    "odds": row["odds"],
                    "home_goals": result.get("home_goals"),
                    "away_goals": result.get("away_goals"),
                    "candidate_frozen2025_hash": candidate_hash,
                }
            )
    save(outdir / "forecasts_2026.json", forecasts26)
    save(outdir / "replay_inputs.json", replay_inputs)
    results = {
        "experiment": plan["experiment"],
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "plan_sha256": PLAN_SHA,
        "candidate_sha256": candidate_hash,
        "model_state_unchanged": digest(model_state(ev)) == state_hash,
        "extraction": manifest,
        "arms": {arm: run_replay(rows, policy) for arm, rows in replay_inputs.items()},
        "cold_start_teams_2026": sorted(
            {team for f in forecasts26 for team in f["cold_start_teams"]}
        ),
        "cold_start_forecasts_2026": sum(
            bool(f["cold_start_teams"]) for f in forecasts26
        ),
    }
    save(outdir / "results.json", results)
    print(
        json.dumps(
            {
                arm: {
                    role: {k: v for k, v in stats.items() if k != "curve"}
                    for role, stats in result["by_role"].items()
                }
                for arm, result in results["arms"].items()
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=WORK / "run")
    execute(parser.parse_args().outdir)
