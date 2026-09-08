"""Explicit, reproducible research orchestration without operational data discovery."""

from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any

from .dynamic_xg import DynamicXGConfig, Fixture, XGObservation, fit_calibration, forecast
from .quotes import PricePolicy, scan_quotes

MARKETS = {"1x2": ("home", "draw", "away"), "ou25": ("over", "under"), "btts": ("yes", "no")}
PROTOCOL_KEYS = {
    "schema_version",
    "study_id",
    "data_kind",
    "hypothesis",
    "stopping_rule",
    "training_end",
    "calibration_end",
    "evaluation_start",
    "evaluation_end",
    "report_as_of",
    "xg_config",
    "price_policy",
}


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO string with timezone")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp requires timezone")
    return result.astimezone(UTC)


def jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return jsonable(asdict(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    return value


def price_policy(raw: dict) -> PricePolicy:
    if not isinstance(raw, dict) or not isinstance(raw.get("reference_books"), list):
        raise ValueError("price_policy requires explicit reference_books list")
    return PricePolicy(**{**raw, "reference_books": tuple(raw["reference_books"])})


def validate_probabilities(raw: Any) -> dict:
    if not isinstance(raw, dict) or set(raw) != set(MARKETS):
        raise ValueError("probabilities require exactly 1x2, ou25 and btts")
    for market, selections in MARKETS.items():
        vector = raw[market]
        if not isinstance(vector, dict) or set(vector) != set(selections):
            raise ValueError(f"incomplete probability vector: {market}")
        if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in vector.values()):
            raise ValueError("invalid probability")
        if not math.isclose(sum(vector.values()), 1.0, abs_tol=1e-9):
            raise ValueError("probabilities must sum to one")
    return raw


def _protocol(raw: dict) -> tuple[dict[str, datetime], DynamicXGConfig, PricePolicy]:
    if set(raw) != PROTOCOL_KEYS or raw.get("schema_version") != "price-strength-study/1":
        raise ValueError("invalid protocol schema or fields")
    if raw["data_kind"] not in {"SYNTHETIC_DEMONSTRATION", "EXPLORATORY_REPLAY"}:
        raise ValueError("only synthetic or explicitly exploratory studies are supported")
    for key in ("study_id", "hypothesis", "stopping_rule"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise ValueError(f"protocol requires {key}")
    clocks = {
        name: timestamp(raw[name])
        for name in ("training_end", "calibration_end", "evaluation_start", "evaluation_end", "report_as_of")
    }
    if not (
        clocks["training_end"]
        < clocks["calibration_end"]
        < clocks["evaluation_start"]
        <= clocks["evaluation_end"]
        <= clocks["report_as_of"]
    ):
        raise ValueError("training, calibration, evaluation and reporting windows must be ordered")
    if not isinstance(raw["xg_config"], dict):
        raise ValueError("xg_config must be explicit")
    return clocks, DynamicXGConfig(**raw["xg_config"]), price_policy(raw["price_policy"])


def _observations(rows: list[dict]) -> list[XGObservation]:
    observations = []
    for row in rows:
        values = dict(row)
        for key in ("kickoff", "completed_at", "available_at"):
            values[key] = timestamp(values[key])
        observations.append(XGObservation(**values))
    return observations


def _score(probabilities: dict, observation: XGObservation) -> dict:
    h, a = observation.home_goals, observation.away_goals
    if h is None or a is None:
        raise ValueError("scoring requires both goal counts")
    outcomes = {
        "1x2": "home" if h > a else "away" if a > h else "draw",
        "ou25": "over" if h + a > 2 else "under",
        "btts": "yes" if h > 0 and a > 0 else "no",
    }
    scores = {}
    for market, selections in MARKETS.items():
        vector = probabilities.get(market)
        if vector is None:
            continue
        actual = outcomes[market]
        # Multiclass Brier is the sum; binary Brier uses the positive class only.
        if market == "1x2":
            brier = sum((vector[s] - int(s == actual)) ** 2 for s in selections)
        else:
            brier = (vector[selections[0]] - int(actual == selections[0])) ** 2
        scores[market] = {"brier": brier, "log_loss": -math.log(max(vector[actual], 1e-15))}
    return scores


def _market_reference(scan: dict, policy: PricePolicy) -> tuple[dict, dict]:
    """Select lexically by offered book, independent of EV and eventual results."""
    probabilities, provenance = {}, {}
    for row in sorted(scan["evaluations"], key=lambda row: (row["market"], row["bookmaker"])):
        market = row["market"]
        if market in probabilities or row["bookmaker"] in policy.reference_books:
            continue
        vector = row.get("reference_probabilities")
        if vector:
            probabilities[market] = vector
            provenance[market] = {
                "comparison_book": row["bookmaker"],
                "reference_provenance": row["reference_provenance"],
            }
    return probabilities, provenance


def _paired_metrics(comparisons: list[dict]) -> dict:
    paired = {}
    for candidate in ("raw_xg", "calibrated_xg"):
        paired[candidate] = {}
        for comparator in ("market", "frozen_baseline"):
            paired[candidate][comparator] = {}
            for market in MARKETS:
                pairs = [
                    (row["scores"][candidate][market], row["scores"][comparator][market])
                    for row in comparisons
                    if market in row["scores"].get(candidate, {}) and market in row["scores"].get(comparator, {})
                ]
                paired[candidate][comparator][market] = {
                    "n": len(pairs),
                    "mean_delta_brier": math.fsum(a["brier"] - b["brier"] for a, b in pairs) / len(pairs)
                    if pairs
                    else None,
                    "mean_delta_log_loss": math.fsum(a["log_loss"] - b["log_loss"] for a, b in pairs) / len(pairs)
                    if pairs
                    else None,
                }
    return paired


def run_study(
    *, protocol: dict, history: list[dict], fixtures: list[dict], quotes: list[dict], baseline: list[dict] | None = None
) -> dict[str, Any]:
    """No refits chosen by evaluation scores; all inputs are supplied by the caller."""
    clocks, config, policy = _protocol(protocol)
    observations = _observations(history)
    if not fixtures:
        raise ValueError("at least one evaluation fixture is required")
    planned = []
    for raw in fixtures:
        if set(raw) != {"match_id", "home_team", "away_team", "kickoff", "decision_at"}:
            raise ValueError("invalid fixture fields")
        decision = timestamp(raw["decision_at"])
        if not clocks["evaluation_start"] <= decision <= clocks["evaluation_end"]:
            raise ValueError("fixture decision outside declared evaluation window")
        fixture = Fixture(raw["match_id"], raw["home_team"], raw["away_team"], timestamp(raw["kickoff"]))
        if decision >= fixture.kickoff:
            raise ValueError("decisions must precede kickoff")
        planned.append((decision, fixture))
    if len({f.match_id for _, f in planned}) != len(planned):
        raise ValueError("duplicate evaluation match_id")
    planned.sort(key=lambda pair: (pair[0], pair[1].match_id))
    fixture_ids = {fixture.match_id for _, fixture in planned}
    if any(row.get("event_id") not in fixture_ids for row in quotes):
        raise ValueError("all quote event IDs must belong to the explicit fixture universe")
    baseline_index = {}
    for row in baseline or []:
        if set(row) != {"match_id", "decision_at", "generated_at", "candidate_id", "probabilities"}:
            raise ValueError("invalid frozen baseline fields")
        if row["match_id"] in baseline_index:
            raise ValueError("duplicate baseline match_id")
        if not isinstance(row["candidate_id"], str) or not row["candidate_id"].strip():
            raise ValueError("baseline requires candidate_id")
        validate_probabilities(row["probabilities"])
        if timestamp(row["generated_at"]) > timestamp(row["decision_at"]):
            raise ValueError("baseline was generated after its decision")
        baseline_index[row["match_id"]] = row
    if set(baseline_index) - fixture_ids:
        raise ValueError("baseline contains a match outside the fixture universe")
    calibration = fit_calibration(
        observations, training_end=clocks["training_end"], calibration_end=clocks["calibration_end"], config=config
    )
    forecasts, scans, comparisons, rejected = [], [], [], []
    for decision, fixture in planned:
        raw_prediction = forecast(observations, fixture, decision_at=decision, config=config)
        calibrated = forecast(observations, fixture, decision_at=decision, config=config, calibration=calibration)
        forecast_row = {
            "match_id": fixture.match_id,
            "decision_at": decision,
            "raw": raw_prediction,
            "calibrated": calibrated,
        }
        forecasts.append(jsonable(forecast_row))
        event_quotes = [row for row in quotes if row.get("event_id") == fixture.match_id]
        for quote in event_quotes:
            if timestamp(quote.get("kickoff_at")) != fixture.kickoff:
                raise ValueError("quote kickoff does not match fixture identity")
        scan = scan_quotes(event_quotes, as_of=decision, policy=policy)
        scan["match_id"] = fixture.match_id
        for evaluation in scan["evaluations"]:
            if evaluation.get("reference_probability") is None:
                continue
            model_diagnostics = {}
            for name, prediction in (("raw_xg", raw_prediction), ("calibrated_xg", calibrated)):
                if prediction.eligible:
                    p = prediction.probabilities[evaluation["market"]][evaluation["selection"]]
                    odd = evaluation["decimal_odds"]
                    model_diagnostics[name] = {
                        "probability": p,
                        "difference_from_reference": p - evaluation["reference_probability"],
                        "net_ev": p * (1 + (odd - 1) * (1 - policy.commission_on_profit)) - 1 - policy.cost_per_unit,
                    }
            evaluation["xg_diagnostics"] = model_diagnostics
        market_probabilities, market_provenance = _market_reference(scan, policy)
        scans.append(scan)
        for error in scan["validation_errors"]:
            rejected.append({"match_id": fixture.match_id, "kind": "quote_validation", "detail": error})
        for name, prediction in (("raw_xg", raw_prediction), ("calibrated_xg", calibrated)):
            if not prediction.eligible:
                rejected.append({"match_id": fixture.match_id, "kind": name, "reason": prediction.reason})
        labels = [
            obs
            for obs in observations
            if obs.match_id == fixture.match_id
            and obs.available_at <= clocks["report_as_of"]
            and obs.home_goals is not None
        ]
        if len(labels) > 1:
            # The model may handle revisions; metrics must never silently choose a conflicting result.
            distinct = {(o.home_goals, o.away_goals) for o in labels}
            if len(distinct) != 1:
                raise ValueError("conflicting evaluation labels")
        if any(
            (obs.home_team, obs.away_team, obs.kickoff) != (fixture.home_team, fixture.away_team, fixture.kickoff)
            for obs in labels
        ):
            raise ValueError("evaluation label identity does not match fixture")
        label = labels[0] if labels else None
        comparison = {"match_id": fixture.match_id, "label_available": label is not None, "scores": {}}
        comparison["market_reference"] = market_provenance
        if label is not None:
            for name, prediction in (("raw_xg", raw_prediction), ("calibrated_xg", calibrated)):
                if prediction.eligible:
                    comparison["scores"][name] = _score(prediction.probabilities, label)
            comparison["scores"]["market"] = _score(market_probabilities, label)
        supplied = baseline_index.get(fixture.match_id)
        if supplied is not None:
            if timestamp(supplied["decision_at"]) != decision:
                raise ValueError("baseline decision does not match fixture")
            comparison["baseline_candidate_id"] = supplied["candidate_id"]
            if label is not None:
                comparison["scores"]["frozen_baseline"] = _score(supplied["probabilities"], label)
        comparisons.append(comparison)
    summary = {
        "status": "RESEARCH_ONLY",
        "data_kind": protocol["data_kind"],
        "study_id": protocol["study_id"],
        "lineage": "INDEPENDENT_ROLLING_XG_PRICE_STRENGTH_V1",
        "execution_proven": False,
        "real_capital_enabled": False,
        "profitability_established": False,
        "fixtures": len(planned),
        "calibrated_forecasts": sum(row["calibrated"]["eligible"] for row in forecasts),
        "quote_candidates": sum(len(scan["selected_candidates"]) for scan in scans),
        "labelled_fixtures": sum(row["label_available"] for row in comparisons),
        "calibration": jsonable(calibration),
        "paired_metrics": _paired_metrics(comparisons),
        "metric_policy": (
            "Same fixtures per candidate/comparator/market; negative loss deltas favor candidate; descriptive only."
        ),
        "market_benchmark_policy": (
            "First eligible non-reference offer book in lexical order per market; no EV/result selection."
        ),
        "limitations": [
            "Explicit input clocks are declarations, not independent source verification.",
            "Observed quotes do not establish execution or available stake.",
            "Exploratory history cannot establish a new untouched holdout.",
            "No legacy model, protected cohort or training gate is changed.",
        ],
    }
    return {
        "protocol.json": protocol,
        "forecasts.jsonl": forecasts,
        "price_scans.jsonl": scans,
        "comparisons.jsonl": comparisons,
        "rejections.jsonl": rejected,
        "summary.json": summary,
    }
