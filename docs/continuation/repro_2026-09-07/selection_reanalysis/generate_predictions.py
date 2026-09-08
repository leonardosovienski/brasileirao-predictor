"""Isolated historical serving forecasts; no odds, selection, or economic analysis.

The declared decision is one hour before kickoff. Training labels are accessed
only for matches whose kickoff is at least 48 hours before that decision. This
buffer is an availability assumption, not evidence of publication timestamps.
The supplied input must contain only already explored 2021--2025 events.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import platform
import sys
import time
import warnings
from bisect import bisect_right
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable


WORK = Path(__file__).resolve().parent
DEFAULT_REPO = Path("C:/Users/Superleo13/projetos/brasileirao-predictor")
DECISION_LEAD_HOURS = 1
LABEL_BUFFER_HOURS = 48
MIN_HISTORY = 200
REFIT_EVERY = 100
MAX_GOALS = 12


def utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("kickoff must contain a UTC offset")
    return parsed.astimezone(UTC)


def stamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode())


def _event_shell(raw: dict[str, Any]) -> dict[str, Any]:
    """Project allowed features without accessing odds or outcome values."""
    kickoff = utc(raw["kickoff"])
    day = date.fromisoformat(raw["date"])
    if not 2021 <= kickoff.year <= 2025 or not 2021 <= day.year <= 2025:
        raise ValueError("Only explored 2021--2025 events are allowed")
    if not str(raw["home"]).strip() or not str(raw["away"]).strip():
        raise ValueError("Both team identities must be nonempty")
    if raw["home"] == raw["away"]:
        raise ValueError("An event must contain distinct teams")
    if raw.get("neutral", 0) not in (0, 1, False, True):
        raise ValueError("neutral must be boolean or 0/1")
    event_id = raw["event_id"]
    if not isinstance(event_id, (str, int)) or isinstance(event_id, bool) or not str(event_id):
        raise ValueError("event_id must be a nonempty string or integer")
    return {
        "event_id": event_id,
        "home": str(raw["home"]),
        "away": str(raw["away"]),
        "kickoff": kickoff,
        "date": day.isoformat(),
        "tournament": raw.get("tournament"),
        "city": raw.get("city"),
        "neutral": int(bool(raw.get("neutral", 0))),
    }


def _historical_observation(shell: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    """Called only after this game's kickoff satisfies the buffered cutoff."""
    outcome = raw["result"]
    safe = {}
    for key in ("home_goals", "away_goals"):
        value = outcome[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Invalid historical {key} for event {shell['event_id']}")
        safe[key] = value
    for key in ("home_xg", "away_xg"):
        value = outcome.get(key)
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise ValueError(f"Invalid historical {key} for event {shell['event_id']}")
        safe[key] = value
    return {**shell, "result": safe}


@contextlib.contextmanager
def optimizer_audit(model_module: Any | None, calls: list[dict[str, Any]]):
    """Observe existing solver calls, including Powell fallback, without changing them."""
    if model_module is None:
        yield
        return
    original = model_module.minimize

    def observed(*args: Any, **kwargs: Any):
        started = time.perf_counter()
        try:
            value = original(*args, **kwargs)
        except Exception as exc:
            calls.append({"method": kwargs.get("method"), "error_type": type(exc).__name__, "seconds": time.perf_counter() - started})
            raise
        calls.append({
            "method": kwargs.get("method"),
            "success": bool(value.success),
            "message": str(value.message),
            "iterations": int(value.nit) if hasattr(value, "nit") else None,
            "seconds": time.perf_counter() - started,
        })
        return value

    model_module.minimize = observed
    try:
        yield
    finally:
        model_module.minimize = original


def _probabilities(prediction: Any) -> tuple[dict[str, float], float, float]:
    p_1x2 = {side: float(prediction.value[side]) for side in ("home", "draw", "away")}
    p_over = float(prediction.metadata["p_over"])
    p_btts = float(prediction.metadata["p_btts"])
    probabilities = [*p_1x2.values(), p_over, p_btts]
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities):
        raise ValueError("Forecast probabilities must be finite and in [0,1]")
    if not math.isclose(sum(p_1x2.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("Forecast 1X2 probabilities are not normalized")
    return p_1x2, p_over, p_btts


def generate(
    raw_events: list[dict[str, Any]],
    cfg: dict[str, Any],
    evaluator_factory: Callable[..., Any],
    *,
    model_module: Any | None = None,
    min_history: int = MIN_HISTORY,
    refit_every: int = REFIT_EVERY,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if min_history < 2 or refit_every < 1:
        raise ValueError("min_history >=2 and refit_every >=1 are required")
    if cfg["model"]["max_goals"] != MAX_GOALS:
        raise ValueError("This declared replay requires current config max_goals=12")
    started = time.perf_counter()
    ordered = [(_event_shell(raw), raw) for raw in raw_events]
    ordered.sort(key=lambda pair: (pair[0]["kickoff"], str(pair[0]["event_id"])))
    identifiers = [str(shell["event_id"]) for shell, _raw in ordered]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate event_id")
    kicks = [shell["kickoff"] for shell, _raw in ordered]
    evaluator = evaluator_factory(cfg, max_goals=MAX_GOALS)
    config_hash = canonical_hash(cfg)
    forecasts: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    fits: list[dict[str, Any]] = []
    cached_history: list[dict[str, Any]] = []
    last_fit_n: int | None = None
    fit_info: dict[str, Any] | None = None
    cold_start_forecasts = 0

    for position, (shell, _raw) in enumerate(ordered):
        decision_at = shell["kickoff"] - timedelta(hours=DECISION_LEAD_HOURS)
        cutoff = decision_at - timedelta(hours=LABEL_BUFFER_HOURS)
        eligible_n = bisect_right(kicks, cutoff)
        if eligible_n > position:
            raise AssertionError("Target or future event entered training prefix")
        if eligible_n < min_history:
            skipped.append({"event_id": shell["event_id"], "kickoff": stamp(shell["kickoff"]), "reason": "INSUFFICIENT_BUFFERED_HISTORY", "eligible_n": eligible_n})
            continue

        due = last_fit_n is None or eligible_n - last_fit_n >= refit_every
        if due:
            # Results are first accessed here, from the strictly buffered prefix.
            for history_position in range(len(cached_history), eligible_n):
                old_shell, old_raw = ordered[history_position]
                if old_shell["kickoff"] > cutoff:
                    raise AssertionError("Noneligible label access")
                cached_history.append(_historical_observation(old_shell, old_raw))
            history = cached_history[:eligible_n]
            calls: list[dict[str, Any]] = []
            fit_start = time.perf_counter()
            if progress:
                progress({"status": "fit_started", "refit_number": len(fits) + 1, "eligible_n": eligible_n, "event_id": shell["event_id"]})
            caught = []
            try:
                with warnings.catch_warnings(record=True) as caught, optimizer_audit(model_module, calls):
                    warnings.simplefilter("always")
                    evaluator._fit(history, decision_at)
            except Exception as exc:
                if progress:
                    progress({"status": "fit_failed", "refit_number": len(fits) + 1, "eligible_n": eligible_n, "event_id": shell["event_id"], "error_type": type(exc).__name__, "message": str(exc), "optimizer_calls": calls, "warnings": [{"category": warning.category.__name__, "message": str(warning.message)} for warning in caught]})
                raise
            if getattr(evaluator, "params", None) is None:
                raise RuntimeError("Fit returned no parameters; no stale-state fallback allowed")
            last_fit_n = eligible_n
            fit_info = {
                "refit_number": len(fits) + 1,
                "decision_at": stamp(decision_at),
                "training_cutoff": stamp(cutoff),
                "training_n": eligible_n,
                "training_first_kickoff": stamp(history[0]["kickoff"]),
                "training_last_kickoff": stamp(history[-1]["kickoff"]),
                "training_event_ids_sha256": canonical_hash([str(row["event_id"]) for row in history]),
                "seconds": time.perf_counter() - fit_start,
                "optimizer_calls": calls,
                "optimizer_fallback_used": any(call.get("method") == "Powell" for call in calls),
                "warnings": [{"category": warning.category.__name__, "message": str(warning.message)} for warning in caught],
                "xg_fit_failures_cumulative": int(getattr(evaluator, "xg_fit_failures", 0)),
                "deferred_refits_cumulative": int(getattr(evaluator, "deferred_refits", 0)),
            }
            fits.append(fit_info)
            if progress:
                progress({"status": "fit_finished", "refit_number": len(fits), "seconds": fit_info["seconds"], "optimizer_fallback_used": fit_info["optimizer_fallback_used"], "warnings": fit_info["warnings"]})

        if fit_info is None:
            raise AssertionError("Prediction without fit metadata")
        # This dict has neither target result nor odds, and contains only known features.
        features = {key: shell[key] for key in ("home", "away", "kickoff", "date", "tournament", "city", "neutral")}
        cold_start = [shell[key] for key in ("home", "away") if shell[key] not in evaluator.elo]
        prediction = evaluator.predict_step(features)
        p_1x2, p_over, p_btts = _probabilities(prediction)
        cold_start_forecasts += bool(cold_start)
        forecasts.append({
            "event_id": shell["event_id"],
            "home": shell["home"],
            "away": shell["away"],
            "kickoff": stamp(shell["kickoff"]),
            "date": shell["date"],
            "p_1x2": [p_1x2[side] for side in ("home", "draw", "away")],
            "p_over25": p_over,
            "p_btts": p_btts,
            "decision_at": stamp(decision_at),
            "training_cutoff_at": stamp(cutoff),
            "metadata": {
                "decision_at": stamp(decision_at),
                "eligible_training_cutoff": stamp(cutoff),
                "eligible_training_n": eligible_n,
                "refit_number": fit_info["refit_number"],
                "fit_training_n": fit_info["training_n"],
                "fit_training_cutoff": fit_info["training_cutoff"],
                "fit_training_last_kickoff": fit_info["training_last_kickoff"],
                "config_sha256": config_hash,
                "cold_start_teams_using_initial_rating": cold_start,
                "ensemble_active": bool(prediction.metadata.get("ensemble", False)),
                "max_goals": MAX_GOALS,
            },
        })
    return {
        "schema_version": "historical-serving-forecasts/1",
        "status": "complete",
        "policy": {
            "model": "ServingStackEvaluator using current config",
            "allowed_years": [2021, 2022, 2023, 2024, 2025],
            "decision_lead_hours": DECISION_LEAD_HOURS,
            "label_buffer_hours": LABEL_BUFFER_HOURS,
            "training_cutoff_inclusive": True,
            "availability_evidence": "ASSUMED_48H_BUFFER_NOT_PUBLISHED_AT",
            "min_history": min_history,
            "refit_every_new_eligible_games": refit_every,
            "max_goals": MAX_GOALS,
            "odds_used": False,
            "selection_used": False,
            "input_outcomes_accessed_only_when_training_eligible": True,
            "future_confirmatory_evidence": False,
        },
        "config_sha256": config_hash,
        "counts": {"input_events": len(ordered), "forecasts": len(forecasts), "skipped_burn_in": len(skipped), "refits": len(fits), "cold_start_forecasts": cold_start_forecasts, "optimizer_fallback_refits": sum(fit["optimizer_fallback_used"] for fit in fits), "xg_fit_failures": int(getattr(evaluator, "xg_fit_failures", 0))},
        "elapsed_seconds": time.perf_counter() - started,
        "fits": fits,
        "skipped": skipped,
        "forecasts": forecasts,
    }


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=WORK / "historical_input.json")
    parser.add_argument("--output", type=Path, default=WORK / "forecasts.json")
    parser.add_argument("--config", type=Path, default=WORK / "config_frozen.yaml")
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    args = parser.parse_args()
    source = args.input.resolve()
    output = args.output.resolve()
    if not output.is_relative_to(WORK) or source == output:
        parser.error("Output must be a distinct file inside the isolated work namespace")
    if output.exists():
        parser.error("Output already exists; choose a new filename to preserve the prior run")
    sys.path.insert(0, str(args.repo.resolve()))
    import numpy
    import scipy
    import yaml
    from brasileirao_predictor import model
    from brasileirao_predictor.serving_evaluator import ServingStackEvaluator

    config_path = args.config.resolve()
    config_bytes = config_path.read_bytes()
    cfg = yaml.safe_load(config_bytes)
    source_files = [
        Path(__file__).resolve(),
        *(args.repo / "brasileirao_predictor" / name for name in ("serving_evaluator.py", "model.py", "ratings.py", "xg_model.py", "math_utils.py", "dynamic_strength.py")),
    ]
    code_hashes = {str(path.resolve()): sha256_bytes(path.read_bytes()) for path in source_files}
    code_sha256 = canonical_hash(code_hashes)
    input_bytes = source.read_bytes()
    events = json.loads(input_bytes)
    if not isinstance(events, list):
        raise ValueError("historical_input.json must contain an event list")
    last_progress: dict[str, Any] = {}

    def report(message: dict[str, Any]) -> None:
        last_progress.clear()
        last_progress.update(message)
        print(json.dumps(message, ensure_ascii=False), flush=True)

    try:
        payload = generate(events, cfg, ServingStackEvaluator, model_module=model, progress=report)
    except Exception as exc:
        _write(output.with_suffix(".failure.json"), {"status": "failed", "error_type": type(exc).__name__, "message": str(exc), "last_progress": last_progress, "input_sha256": sha256_bytes(input_bytes), "code_sha256": code_sha256})
        raise
    payload["provenance"] = {
        "input_path": str(source), "input_sha256": sha256_bytes(input_bytes),
        "config_path": str(config_path.resolve()), "config_file_sha256": sha256_bytes(config_bytes),
        "config": cfg, "code_files_sha256": code_hashes, "code_sha256": code_sha256,
        "python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__,
        "generated_at": stamp(datetime.now(UTC)),
    }
    for row in payload["forecasts"]:
        row["metadata"]["code_sha256"] = code_sha256
    _write(output.with_name(output.stem + "_manifest.json"), {key: value for key, value in payload.items() if key != "forecasts"})
    _write(output, payload["forecasts"])
    report({"status": "complete", "output": str(output), "counts": payload["counts"], "elapsed_seconds": payload["elapsed_seconds"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
