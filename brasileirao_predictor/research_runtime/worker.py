"""Closed worker for admitted Brasileirão research (handler walkforward_forecast_evaluation.v1).

The executor, never the request, chooses this module; predictor_ops runs it as a child
process. It reads only operator-materialized, hash-verified inputs (the dataset snapshot is
opened read-only and immutable; the live database is never touched) and writes one
immutable domain effect plus one Core trial row. No network, no SQL from the request, no
dynamic import, no arbitrary command, no capital path.

Temporal rule (contract): for every prediction t and every piece of information i used,
``available_at(i) < cutoff(t)`` with ``cutoff(t) = min(kickoff(t) - lead, data_cutoff)`` and
``available_at(result) = kickoff + 180 min`` (brasileirao_predictor.pit). The walk-forward is
driven by ``predictor_core.measurement.replay``: decisions and information are one ordered
stream; at a decision the handler receives only the PastView (information strictly before the
cutoff). Monthly refit: the goal model for cutoff t is fitted at the first instant of its UTC
month with results available before that instant. The database caches current_elo,
model_parameters and xg_model_parameters (state at capture time) are never read.

Core participation (predictor_core, frozen wheel): replay/LookaheadError (temporal validation),
metrics.rps/brier/log_loss, bootstrap.bootstrap_ci (cluster by kickoff), trial_v2
(dataset_fingerprint, TrialRegistryV2).

Exit codes: 0 effect written; 4 temporal integrity violation; 5 contract refusal;
6 reference integrity violation. The last three write worker-refusal.json and no effect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from predictor_core.contracts.trial_v2 import TRIAL_SCHEMA_VERSION, TrialRegistryV2, dataset_fingerprint
from predictor_core.measurement.bootstrap import bootstrap_ci
from predictor_core.measurement.metrics import brier, log_loss, rps
from predictor_core.measurement.replay import LookaheadError, PastView, replay

from brasileirao_predictor import model, ratings
from brasileirao_predictor.math_utils import shin_probabilities
from brasileirao_predictor.pit import result_available_at
from brasileirao_predictor.research_runtime.durable import atomic_write, read_json_object, sha256_file

HANDLER = "brasileirao.handlers.walkforward_forecast_evaluation.v1"
EFFECT_SCHEMA = "brasileirao-domain-effect/1"
EXIT_TEMPORAL = 4
EXIT_REFUSED = 5
EXIT_INTEGRITY = 6
SEALED_SEASONS = {2025}
DIGITS = 12
CI = {"scheme": "cluster", "n_boot": 1000, "seed": 13, "confidence": 0.95}
MIN_EVALUATED = 30
MIN_CALIBRATION = 100
DATA_QUALITY_MAX_EXCLUDED = 0.10
OUTCOMES_1X2 = ("home", "draw", "away")
REFERENCE_SCHEMAS = {
    "model": "brasileirao-model-config/1",
    "features": "brasileirao-features/1",
    "baseline": "brasileirao-baseline/1",
    "cost_model": "brasileirao-cost-model/1",
    "odds": "brasileirao-odds/1",
}


class TemporalViolation(ValueError):
    pass


class Refusal(ValueError):
    pass


class IntegrityViolation(ValueError):
    pass


def _round(value: float) -> float:
    return round(float(value), DIGITS)


def parse_instant(value: Any, field: str) -> datetime:
    """Stored instants must carry an explicit offset; a naive one is refused, never guessed."""
    if not isinstance(value, str) or not value:
        raise TemporalViolation(f"{field}: missing timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TemporalViolation(f"{field}: malformed timestamp {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TemporalViolation(f"{field}: timestamp without timezone {value!r} (never guessed)")
    return parsed.astimezone(UTC)


def _z(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- inputs


def _references(doc: dict) -> dict[str, dict]:
    refs = {}
    for kind, path in doc["references"].items():
        file = Path(path)
        if not file.is_file():
            raise IntegrityViolation(f"materialized reference missing: {kind}")
        if sha256_file(file) != doc["identities"][kind]:
            raise IntegrityViolation(f"materialized reference changed: {kind}")
        value = read_json_object(file)
        expected = REFERENCE_SCHEMAS.get(kind)
        if kind != "dataset" and value.get("schema") != expected:
            raise Refusal(f"reference {kind} has schema {value.get('schema')!r}, expected {expected!r}")
        refs[kind] = value
    return refs


def _open_dataset(doc: dict, manifest: dict) -> sqlite3.Connection:
    path = Path(doc["dataset"]["path"])
    if not path.is_file():
        raise IntegrityViolation("dataset snapshot missing")
    if sha256_file(path) != manifest["sqlite_sha256"]:
        raise IntegrityViolation("dataset snapshot hash differs from its manifest")
    # immutable=1: SQLite never writes, locks or creates -wal/-shm next to the snapshot.
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True)


INFO_SQL = """
SELECT m.event_id, m.date, m.home_team, m.away_team, m.home_score, m.away_score, m.tournament, m.neutral,
       COALESCE(
         (SELECT s.kickoff_at FROM sofascore_matches s WHERE m.event_id IS NOT NULL AND s.event_id = m.event_id),
         (SELECT s.kickoff_at FROM sofascore_matches s
           WHERE m.event_id IS NULL AND substr(s.date, 1, 10) = substr(m.date, 1, 10)
             AND s.home_team = m.home_team AND s.away_team = m.away_team
           ORDER BY s.kickoff_at DESC LIMIT 1)) AS kickoff_at
FROM matches m
WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
ORDER BY m.date, m.home_team, m.away_team
"""

TARGET_SQL = """
SELECT s.event_id, s.competition, s.season, s.date, s.kickoff_at, s.home_team, s.away_team,
       s.superseded_by_event_id, s.odds_home, s.odds_draw, s.odds_away, l.odd_a, l.odd_b,
       m.home_score, m.away_score, m.neutral
FROM sofascore_matches s LEFT JOIN matches m ON m.event_id = s.event_id
LEFT JOIN odds_lines l ON l.event_id = s.event_id AND l.market = 'ou' AND l.line = 2.5
WHERE s.season = ?
ORDER BY s.event_id
"""


def _information(conn: sqlite3.Connection, as_of: datetime) -> list[dict]:
    rows = []
    for event_id, day, home, away, hs, as_, tournament, neutral, kickoff_text in conn.execute(INFO_SQL):
        kickoff = (
            parse_instant(kickoff_text, f"match {event_id or (day, home, away)}.kickoff_at") if kickoff_text else None
        )
        available = result_available_at(kickoff, day)
        if (kickoff or available) > as_of or available > as_of + timedelta(days=1, hours=3):
            raise TemporalViolation(
                f"match {event_id or (day, home, away)} has a final score but could not have ended before the "
                f"snapshot as_of {_z(as_of)} (kickoff {kickoff_text or day})"
            )
        if kickoff is not None and available > as_of:
            raise TemporalViolation(
                f"match {event_id} kicked off {_z(kickoff)}: final score impossible before as_of {_z(as_of)}"
            )
        rows.append(
            {
                "event_id": event_id,
                "date": str(day)[:10],
                "home": home,
                "away": away,
                "hs": int(hs),
                "as": int(as_),
                "tournament": tournament,
                "neutral": int(neutral or 0),
                "kickoff": kickoff,
                "available_at": available,
            }
        )
    # Canonical order fixed by content, never by the physical row order of the database.
    rows.sort(
        key=lambda r: (r["available_at"], r["kickoff"] or r["available_at"], r["event_id"] or 0, r["home"], r["away"])
    )
    seen: dict[tuple, int] = {}
    for row in rows:
        identity = (row["home"], row["away"], row["kickoff"] or row["date"])
        if identity in seen:
            raise Refusal(f"DUPLICATE_FIXTURE: {row['home']} x {row['away']} at {row['kickoff'] or row['date']}")
        seen[identity] = 1
    return rows


def _targets(
    conn: sqlite3.Connection, request: dict, data_cutoff: datetime, lead: timedelta
) -> tuple[list[dict], dict]:
    window_from = parse_instant(request["events"]["kickoff_from"], "events.kickoff_from")
    window_to = parse_instant(request["events"]["kickoff_to"], "events.kickoff_to")
    listed = {item["event_id"]: item["kickoff_at"] for item in request["events"].get("fixtures", [])}
    quality = {"window_events": 0, "excluded_superseded": 0, "excluded_without_kickoff": 0}
    targets, by_id = [], {}
    for row in conn.execute(TARGET_SQL, (str(request["season"]),)):
        (
            event_id,
            competition,
            _season,
            day,
            kickoff_text,
            home,
            away,
            superseded,
            oh,
            od,
            oa,
            oo,
            ou,
            hs,
            as_,
            neutral,
        ) = row
        if not str(competition or "").startswith(request["competition"]):
            continue
        if listed and event_id not in listed:
            continue
        if kickoff_text is None:
            if listed:
                raise Refusal(f"KICKOFF_UNKNOWN: listed event {event_id} has no kickoff in the dataset")
            day_start = datetime.fromisoformat(str(day)[:10]).replace(tzinfo=UTC)
            if window_from <= day_start < window_to:
                quality["window_events"] += 1
                quality["excluded_without_kickoff"] += 1
            continue
        kickoff = parse_instant(kickoff_text, f"event {event_id}.kickoff_at")
        if not window_from <= kickoff < window_to:
            if listed:
                raise Refusal(f"KICKOFF_MISMATCH: event {event_id} kicks off at {_z(kickoff)} outside the window")
            continue
        quality["window_events"] += 1
        if superseded is not None:
            if listed:
                raise Refusal(f"EVENT_SUPERSEDED: event {event_id} was replaced by {superseded}")
            quality["excluded_superseded"] += 1
            continue
        if listed and parse_instant(listed[event_id], "fixture.kickoff_at") != kickoff:
            raise Refusal(
                f"KICKOFF_MISMATCH: event {event_id} kicks off at {_z(kickoff)}, request says {listed[event_id]}"
            )
        if kickoff.year in SEALED_SEASONS:
            raise Refusal("HOLDOUT_SEALED: a target event falls in the sealed holdout season")
        cutoff = min(kickoff - lead, data_cutoff)
        item = {
            "event_id": int(event_id),
            "home": home,
            "away": away,
            "kickoff": kickoff,
            "cutoff": cutoff,
            "neutral": int(neutral or 0),
            "label": None if hs is None or as_ is None else (int(hs), int(as_)),
            "odds": {"home": oh, "draw": od, "away": oa, "over": oo, "under": ou},
        }
        by_id[int(event_id)] = item
        targets.append(item)
    if listed:
        missing = sorted(set(listed) - set(by_id))
        if missing:
            raise Refusal(f"EVENT_NOT_IN_DATASET: {missing[:10]}")
    identities: dict[tuple, int] = {}
    for item in targets:
        identity = (item["home"], item["away"], item["kickoff"])
        if identity in identities:
            raise Refusal(f"DUPLICATE_FIXTURE: target {item['home']} x {item['away']} at {_z(item['kickoff'])}")
        identities[identity] = item["event_id"]
    if not targets:
        raise Refusal("NO_TARGET_EVENTS: no event of the requested season/window with a kickoff")
    targets.sort(key=lambda t: (t["cutoff"], t["kickoff"], t["event_id"]))
    return targets, quality


# --------------------------------------------------------------------------- model


class GoalModelCache:
    """In-process memo of monthly refits keyed by the exact information used (no persistence)."""

    def __init__(self) -> None:
        self.entries: dict[str, tuple | None] = {}
        self.hits = 0
        self.misses = 0

    def params(self, key: str, compute: Callable[[], tuple | None]) -> tuple | None:
        if key in self.entries:
            self.hits += 1
            return self.entries[key]
        self.misses += 1
        value = compute()
        self.entries[key] = value
        return value


def _elo_rows(info: list[dict]) -> list[tuple]:
    return [
        (
            r["date"],
            r["home"],
            r["away"],
            r["hs"],
            r["as"],
            r["tournament"],
            r["neutral"],
            r["kickoff"].isoformat() if r["kickoff"] else None,
        )
        for r in info
    ]


def _windowed(info: list[dict], anchor: datetime, years: float | None) -> list[dict]:
    if not years:
        return info
    start = (anchor.date() - timedelta(days=int(float(years) * 365.25))).isoformat()
    return [r for r in info if r["date"] >= start]


def _fit_goal_model(info: list[dict], refit_at: datetime, cfg: dict) -> tuple | None:
    rows = _windowed(info, refit_at, cfg["elo"].get("window_years"))
    if not rows:
        return None
    _elo, history = ratings.compute_ratings(_elo_rows(rows), cfg["elo"], asof=refit_at.date())
    keys = ratings.temporal_keys(_elo_rows(rows))
    ordered = [row for _key, row in sorted(zip(keys, rows, strict=True), key=lambda item: item[0])]
    cal_start = (
        refit_at.date() - timedelta(days=int(float(cfg["model"]["calibration_window_years"]) * 365.25))
    ).isoformat()
    pairs = [(h, r) for h, r in zip(history, ordered, strict=True) if r["date"] >= cal_start]
    if len(pairs) < MIN_CALIBRATION:
        return None
    weights = model.exponential_recency_weights(
        [r["date"] for _h, r in pairs], refit_at.date().isoformat(), cfg["model"]["goal_half_life_days"]
    )
    return tuple(model.fit_goal_model([h for h, _r in pairs], sample_weights=weights))


def _info_fingerprint(info: list[dict]) -> str:
    return _canonical_hash(
        [[r["event_id"], r["date"], r["home"], r["away"], r["hs"], r["as"], _z(r["available_at"])] for r in info]
    )


def _climatology(info: list[dict], anchor: datetime, years: float) -> dict | None:
    rows = _windowed(info, anchor, years)
    if not rows:
        return None
    n = len(rows)
    home = sum(1 for r in rows if r["hs"] > r["as"]) / n
    draw = sum(1 for r in rows if r["hs"] == r["as"]) / n
    over = sum(1 for r in rows if r["hs"] + r["as"] > 2.5) / n
    return {"home": home, "draw": draw, "away": 1.0 - home - draw, "over": over, "n": n}


def walkforward(info: list[dict], targets: list[dict], cfg: dict, cache: GoalModelCache) -> tuple[list[dict], dict]:
    """Core replay over one ordered stream of information and decision events."""
    stream = [("I", r["available_at"], index) for index, r in enumerate(info)]
    stream += [("D", t["cutoff"], index) for index, t in enumerate(targets)]
    # At equal instants the decision comes first: information available exactly at the
    # cutoff is NOT visible (strict inequality available_at < cutoff).
    stream.sort(key=lambda e: (e[1], 0 if e[0] == "D" else 1, e[2]))
    base = float(cfg["elo"]["initial_rating"])
    home_adv = float(cfg["elo"]["home_advantage"])
    max_goals = int(cfg["model"]["max_goals"])
    audit = {"decisions": 0, "max_used_minus_cutoff_seconds": None}

    def handler(past: PastView) -> dict | None:
        kind, cutoff, index = past.latest
        if kind != "D":
            return None
        used = [info[i] for k, _t, i in past if k == "I"]
        if any(r["available_at"] >= cutoff for r in used):  # defensive: structure makes this impossible
            raise TemporalViolation("information at or after the cutoff reached a decision")
        target = targets[index]
        audit["decisions"] += 1
        if used:
            gap = (max(r["available_at"] for r in used) - cutoff).total_seconds()
            previous = audit["max_used_minus_cutoff_seconds"]
            audit["max_used_minus_cutoff_seconds"] = gap if previous is None else max(previous, gap)
        refit_at = datetime(cutoff.year, cutoff.month, 1, tzinfo=UTC)
        fit_info = [r for r in used if r["available_at"] < refit_at]
        key = _canonical_hash([_z(refit_at), _info_fingerprint(fit_info)])
        params = cache.params(key, lambda: _fit_goal_model(fit_info, refit_at, cfg))
        decision = {
            "event_id": target["event_id"],
            "home": target["home"],
            "away": target["away"],
            "kickoff": _z(target["kickoff"]),
            "cutoff": _z(cutoff),
            "refit_at": _z(refit_at),
            "n_information": len(used),
            "information_fingerprint": _info_fingerprint(used),
            "fit_information": len(fit_info),
        }
        if params is None:
            return decision | {"status": "INSUFFICIENT_HISTORY"}
        elo_rows = _elo_rows(_windowed(used, cutoff, cfg["elo"].get("window_years")))
        elo, _history = ratings.compute_ratings(elo_rows, cfg["elo"], asof=cutoff.date()) if elo_rows else ({}, [])
        elo_home, elo_away = elo.get(target["home"], base), elo.get(target["away"], base)
        adv = 0.0 if target["neutral"] else home_adv
        r = model.predict_match(elo_home, elo_away, params, adv, max_goals=max_goals)
        clim = _climatology(used, cutoff, float(cfg["model"]["calibration_window_years"]))
        return decision | {
            "status": "PREDICTED",
            "params": [_round(p) for p in params],
            "elo_home": _round(elo_home),
            "elo_away": _round(elo_away),
            "p_home": _round(r["p_win"]),
            "p_draw": _round(r["p_draw"]),
            "p_away": _round(r["p_loss"]),
            "p_over25": _round(r["over"][2.5]),
            "lambda_home": _round(r["lambda_a"]),
            "lambda_away": _round(r["lambda_b"]),
            "climatology": None if clim is None else {k: (_round(v) if k != "n" else v) for k, v in clim.items()},
        }

    try:
        decisions = replay(
            tuple(stream),
            handler,
            key=lambda e: (e[1], 0 if e[0] == "D" else 1, e[2]),
            available_at=lambda e: (e[1], 0 if e[0] == "D" else 1, e[2]),
        )
    except LookaheadError as exc:
        raise TemporalViolation(f"predictor_core replay: {exc}") from exc
    order = {t["event_id"]: i for i, t in enumerate(targets)}
    decisions.sort(key=lambda d: order[d["event_id"]])
    audit["engine"] = "predictor_core.measurement.replay"
    audit["cache"] = {"refits": cache.misses, "hits": cache.hits}
    return decisions, audit


# --------------------------------------------------------------------------- evaluation


def _outcome_1x2(label: tuple[int, int]) -> int:
    hs, as_ = label
    return 0 if hs > as_ else (1 if hs == as_ else 2)


def _odd_ok(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 1.0


def _market(target: dict, market: str) -> list[float] | None:
    odds = target["odds"]
    names = OUTCOMES_1X2 if market == "1X2" else ("over", "under")
    values = [odds[name] for name in names]
    if not all(_odd_ok(v) for v in values):
        return None
    probs, _z_value, _overround = shin_probabilities([float(v) for v in values])
    return [float(p) for p in probs]


def _ci(units: list[dict], field: str) -> tuple[float | None, float | None]:
    lo, hi, _boots = bootstrap_ci(
        units,
        lambda sample: sum(u[field] for u in sample) / len(sample),
        scheme=CI["scheme"],
        cluster_key=lambda u: u["kickoff"],
        n_boot=CI["n_boot"],
        seed=CI["seed"],
        confidence=CI["confidence"],
    )
    return (None if lo is None else _round(lo)), (None if hi is None else _round(hi))


def evaluate(request: dict, refs: dict, targets: list[dict], decisions: list[dict], quality: dict) -> dict:
    target_kind = request["target"]
    baseline_kind = refs["baseline"]["kind"]
    by_id = {t["event_id"]: t for t in targets}
    labelled = [d for d in decisions if d["status"] == "PREDICTED" and by_id[d["event_id"]]["label"] is not None]
    quality = dict(quality)
    quality["targets"] = len(targets)
    quality["insufficient_history"] = sum(1 for d in decisions if d["status"] == "INSUFFICIENT_HISTORY")
    quality["without_label"] = sum(
        1 for d in decisions if d["status"] == "PREDICTED" and by_id[d["event_id"]]["label"] is None
    )
    wants_market = baseline_kind == "MARKET_CLOSE_SHIN" or "odds" in refs
    units, missing_market = [], 0
    for d in labelled:
        t = by_id[d["event_id"]]
        if target_kind == "1X2":
            outcome = _outcome_1x2(t["label"])
            p_model = [d["p_home"], d["p_draw"], d["p_away"]]
        else:
            outcome = 0 if sum(t["label"]) > 2.5 else 1
            p_model = [d["p_over25"], 1.0 - d["p_over25"]]
        market = _market(t, target_kind)
        if wants_market and market is None:
            missing_market += 1
            if baseline_kind == "MARKET_CLOSE_SHIN":
                continue
        if baseline_kind == "MARKET_CLOSE_SHIN":
            p_base = market
        else:
            c = d["climatology"]
            p_base = [c["home"], c["draw"], c["away"]] if target_kind == "1X2" else [c["over"], 1.0 - c["over"]]
        score = (lambda p: rps([p], [outcome])) if target_kind == "1X2" else (lambda p: brier([p], [outcome]))
        s_model, s_base = score(p_model), score(p_base)
        units.append(
            {
                "event_id": d["event_id"],
                "kickoff": d["kickoff"],
                "outcome": outcome,
                "p_model": p_model,
                "p_base": p_base,
                "market": market,
                "raw_odds": None
                if market is None
                else [float(t["odds"][n]) for n in (OUTCOMES_1X2 if target_kind == "1X2" else ("over", "under"))],
                "score_model": s_model,
                "score_base": s_base,
                "delta": s_model - s_base,
            }
        )
    quality["missing_market"] = missing_market
    excluded = quality["excluded_without_kickoff"] + (missing_market if wants_market else 0)
    denominator = max(quality["window_events"], 1)
    quality["excluded_fraction"] = _round(excluded / denominator)
    metric = "rps" if target_kind == "1X2" else "brier"
    evaluation: dict[str, Any] = {"metric": metric, "baseline": baseline_kind, "n_evaluated": len(units)}
    if not labelled:
        return {
            "result_state": "FORECAST_ONLY",
            "scientific_state": "NOT_EVALUATED",
            "economic_state": "NOT_EVALUATED",
            "evaluation": evaluation | {"reason": "no labelled prediction (future events)"},
            "economics": None,
            "data_quality": quality,
        }
    if quality["excluded_fraction"] > DATA_QUALITY_MAX_EXCLUDED:
        return {
            "result_state": "INCONCLUSIVE_DATA_QUALITY",
            "scientific_state": "NOT_EVALUATED",
            "economic_state": "NOT_EVALUATED",
            "evaluation": evaluation,
            "economics": None,
            "data_quality": quality,
        }
    if len(units) < MIN_EVALUATED:
        return {
            "result_state": "CLOSED_INSUFFICIENT_SAMPLE",
            "scientific_state": "INSUFFICIENT_SAMPLE",
            "economic_state": "NOT_EVALUATED",
            "evaluation": evaluation,
            "economics": None,
            "data_quality": quality,
        }
    probs_model = [u["p_model"] for u in units]
    probs_base = [u["p_base"] for u in units]
    outcomes = [u["outcome"] for u in units]
    lo, hi = _ci(units, "delta")
    mean_delta = sum(u["delta"] for u in units) / len(units)
    if lo is None or hi is None:
        scientific = "INCONCLUSIVE"
    elif hi < 0:
        scientific = "SUPPORTED"
    elif lo > 0:
        scientific = "REFUTED"
    else:
        scientific = "INCONCLUSIVE"
    evaluation |= {
        "model": {
            metric: _round(sum(u["score_model"] for u in units) / len(units)),
            "brier": _round(brier(probs_model, outcomes)),
            "log_loss": _round(log_loss(probs_model, outcomes)),
        },
        "baseline_scores": {
            metric: _round(sum(u["score_base"] for u in units) / len(units)),
            "brier": _round(brier(probs_base, outcomes)),
            "log_loss": _round(log_loss(probs_base, outcomes)),
        },
        "mean_delta": _round(mean_delta),
        "ci_delta": [lo, hi],
        "ci": CI,
        "rule": "SUPPORTED if ci_hi < 0; REFUTED if ci_lo > 0; else INCONCLUSIVE (lower score is better)",
    }
    economics = _economics(refs, units, target_kind) if "odds" in refs else None
    if economics is None or economics["state"] == "NOT_EVALUATED":
        economic = "NOT_EVALUATED"
    elif scientific == "SUPPORTED" and economics["ci_net_mean"][0] is not None and economics["ci_net_mean"][0] > 0:
        economic = "WATCH"
    else:
        economic = "NO_EDGE"
    state = {
        "SUPPORTED": "WATCH_NO_CAPITAL" if economic == "WATCH" else "NO_EDGE",
        "REFUTED": "REFUTED",
        "INCONCLUSIVE": "INCONCLUSIVE",
    }[scientific]
    return {
        "result_state": state,
        "scientific_state": scientific,
        "economic_state": economic,
        "evaluation": evaluation,
        "economics": economics,
        "data_quality": quality,
    }


def _economics(refs: dict, units: list[dict], target_kind: str) -> dict:
    cost = refs["cost_model"]
    low, high = cost["edge_window"]
    slip = float(cost["slippage_on_winnings"])
    tax = float(cost["tax_on_annual_positive_net"])
    names = OUTCOMES_1X2 if target_kind == "1X2" else ("over", "under")
    bets = []
    for u in units:
        if u["market"] is None:
            continue
        raw = u["raw_odds"]
        for index, name in enumerate(names):
            odd = float(raw[index])
            edge = u["p_model"][index] * odd - 1.0
            if not low <= edge <= high:
                continue
            won = u["outcome"] == index
            gross = (odd - 1.0) if won else -1.0
            net = (odd - 1.0) * (1.0 - slip) if won else -1.0
            bets.append(
                {
                    "event_id": u["event_id"],
                    "kickoff": u["kickoff"],
                    "selection": name,
                    "odd": odd,
                    "edge": _round(edge),
                    "won": won,
                    "gross": gross,
                    "net": net,
                }
            )
    result: dict[str, Any] = {
        "execution_price": "closing odds (last pre-match price); opening price has no timestamp in history",
        "edge_window": [low, high],
        "slippage_on_winnings": slip,
        "n_bets": len(bets),
        "clv": {"status": "NOT_MEASURABLE", "reason": "no timestamped pre-kickoff price before the close"},
    }
    if len(bets) < int(cost["min_bets"]):
        return result | {
            "state": "NOT_EVALUATED",
            "reason": f"fewer than {cost['min_bets']} bets",
            "ci_net_mean": [None, None],
        }
    gross_total = sum(b["gross"] for b in bets)
    net_total = sum(b["net"] for b in bets)
    by_year: dict[str, float] = {}
    for b in bets:
        by_year[b["kickoff"][:4]] = by_year.get(b["kickoff"][:4], 0.0) + b["net"]
    tax_total = sum(tax * max(0.0, value) for value in by_year.values())
    return result | {
        "state": "EVALUATED",
        "roi_gross": _round(gross_total / len(bets)),
        "roi_net": _round(net_total / len(bets)),
        "ci_gross_mean": list(_ci(bets, "gross")),
        "ci_net_mean": list(_ci(bets, "net")),
        "net_after_tax_total": _round(net_total - tax_total),
        "tax_rule": f"{tax:.2f} x positive net per calendar year",
        "hit_rate": _round(sum(1 for b in bets if b["won"]) / len(bets)),
    }


# --------------------------------------------------------------------------- main


def _refuse(effect_path: Path, code: int, reason: str) -> int:
    atomic_write(
        effect_path.with_name("worker-refusal.json"),
        json.dumps({"exit_code": code, "reason": reason[:1000]}, sort_keys=True).encode("utf-8"),
    )
    print(json.dumps({"status": "REFUSED", "exit_code": code, "reason": reason[:300]}, sort_keys=True))
    return code


def run(doc: dict, trial_path: Path) -> dict:
    if doc.get("schema") != "brasileirao-admitted-research/1" or doc.get("handler") != HANDLER:
        raise Refusal("worker request schema/handler mismatch")
    request = doc["request"]
    refs = _references(doc)
    manifest = refs["dataset"]
    if manifest.get("schema") != "brasileirao-dataset/1":
        raise Refusal("dataset manifest schema")
    as_of = parse_instant(manifest["as_of"], "dataset.as_of")
    data_cutoff = parse_instant(request["data_cutoff"], "data_cutoff")
    if data_cutoff > as_of:
        raise Refusal(f"DATA_CUTOFF_AFTER_DATASET_AS_OF: {request['data_cutoff']} > {manifest['as_of']}")
    cfg = refs["model"]["config"]
    if refs["features"].get("xg") or refs["features"]["features"] != ["elo_diff_pre_match", "home_advantage"]:
        raise Refusal("features reference outside the compiled model")
    lead = timedelta(minutes=int(request["decision_lead_minutes"]))
    with _open_dataset(doc, manifest) as conn:
        info_all = _information(conn, as_of)
        targets, quality = _targets(conn, request, data_cutoff, lead)
    info = [r for r in info_all if r["available_at"] < data_cutoff]
    cache = GoalModelCache()
    decisions, audit = walkforward(info, targets, cfg, cache)
    for d, t in zip(
        sorted(decisions, key=lambda x: x["event_id"]), sorted(targets, key=lambda x: x["event_id"]), strict=True
    ):
        if d["event_id"] != t["event_id"]:
            raise IntegrityViolation("decision/target mismatch")
    outcome = evaluate_with_prices(request, refs, targets, decisions, quality)
    audit |= {
        "rule": (
            "available_at(i) < cutoff(t); cutoff(t) = min(kickoff(t) - lead, data_cutoff); "
            "available_at(result) = kickoff + 180 min"
        ),
        "n_information_events": len(info),
        "excluded_after_data_cutoff": len(info_all) - len(info),
        "n_decisions": len(decisions),
        "db_caches_read": [],
    }
    fingerprint = dataset_fingerprint(
        [
            {
                "event_id": r["event_id"] or 0,
                "date": r["date"],
                "home": r["home"],
                "away": r["away"],
                "hs": r["hs"],
                "as": r["as"],
                "available_at": _z(r["available_at"]),
            }
            for r in info
        ],
        fields=("event_id", "date", "home", "away", "hs", "as", "available_at"),
    )
    labelled = [t for t in targets if t["label"] is not None]
    trial = {
        "schema_version": TRIAL_SCHEMA_VERSION,
        "experiment_id": doc["experiment_id"],
        "hypothesis_id": request["hypothesis_id"],
        "hypothesis_family": "brasileirao:serving-baseline",
        "trial_id": doc["trial_id"],
        "registered_at": doc["registered_at"],
        "executed_at": doc["registered_at"],
        "seed": CI["seed"],
        "forecast_horizon": f"{request['decision_lead_minutes']}min-before-kickoff",
        "data_cutoff": request["data_cutoff"],
        "label_start": _z(min(t["kickoff"] for t in labelled)) if labelled else "NOT_APPLICABLE",
        "label_end": _z(max(t["kickoff"] for t in labelled)) if labelled else "NOT_APPLICABLE",
        "dataset_hash": fingerprint,
        "dataset_version": f"{doc['identities_named']['dataset']}",
        "feature_version": f"{doc['identities_named']['features']}",
        "model_version": f"{doc['identities_named']['model']}",
        "code_version": doc["code_version"],
        "params": {
            "target": request["target"],
            "baseline": refs["baseline"]["kind"],
            "decision_lead_minutes": request["decision_lead_minutes"],
            "refit": "monthly",
            "result_latency_minutes": 180,
            "model_config_hash": _canonical_hash(cfg),
        },
        "selection_path": {
            "family": "brasileirao:serving-baseline",
            "candidate_set": [cfg["algorithm"]],
            "selection_metric": "NOT_APPLICABLE",
            "selected_candidate": cfg["algorithm"],
        },
        "n_trials_family": "known_trials >= 1",
        "n_trials_domain": "known_trials >= 1",
        "n_trials_ecosystem": "known_trials >= 1",
        "metric": outcome["evaluation"]["metric"],
        "result": {
            k: v
            for k, v in outcome["evaluation"].items()
            if k in {"n_evaluated", "mean_delta", "ci_delta", "model", "baseline_scores"}
        }
        or {"n_evaluated": 0},
        "status": outcome["scientific_state"],
        "notes": f"{HANDLER}; result_state={outcome['result_state']}; capital_permission=false",
    }
    registry = TrialRegistryV2(trial_path)
    existing = [row for row in registry.load() if row["trial_id"] == trial["trial_id"]]
    if existing:
        if existing[0] != trial:
            raise IntegrityViolation("Core trial registry already holds a different row for this trial")
    else:
        registry.register(trial)
    return {
        "schema": EFFECT_SCHEMA,
        "handler": HANDLER,
        "experiment_id": doc["experiment_id"],
        "request_id": request["request_id"],
        "target": request["target"],
        "data_cutoff": request["data_cutoff"],
        "dataset_as_of": manifest["as_of"],
        "result_state": outcome["result_state"],
        "scientific_state": outcome["scientific_state"],
        "economic_state": outcome["economic_state"],
        "predictions": decisions,
        "evaluation": outcome["evaluation"],
        "economics": outcome["economics"],
        "data_quality": outcome["data_quality"],
        "temporal_validation": audit,
        "dataset_fingerprint": fingerprint,
        "trial": trial,
        "capital_permission": False,
    }


def evaluate_with_prices(request: dict, refs: dict, targets: list[dict], decisions: list[dict], quality: dict) -> dict:
    """Ex post evaluation: labels and closing prices join AFTER every prediction exists."""
    return evaluate(request, refs, targets, decisions, quality)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Brasileirão research worker (compiled handler)")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--effect", type=Path, required=True)
    parser.add_argument("--trial-registry", type=Path, required=True)
    parser.add_argument("--fault", choices=("crash", "hang", "slow"))
    args = parser.parse_args(argv)
    if args.fault == "crash":
        sys.stderr.write("INJECTED_WORKER_CRASH\n")
        sys.stderr.flush()
        os._exit(70)
    if args.fault == "hang":
        while True:
            time.sleep(1)
    if args.fault == "slow":
        time.sleep(2)
    if args.effect.exists():
        print(json.dumps({"status": "EFFECT_ALREADY_PRESENT"}))
        return 0
    try:
        doc = read_json_object(args.request)
        effect = run(doc, args.trial_registry)
    except TemporalViolation as exc:
        return _refuse(args.effect, EXIT_TEMPORAL, f"TEMPORAL: {exc}")
    except IntegrityViolation as exc:
        return _refuse(args.effect, EXIT_INTEGRITY, str(exc))
    except Refusal as exc:
        return _refuse(args.effect, EXIT_REFUSED, str(exc))
    raw = json.dumps(effect, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    atomic_write(args.effect, raw)
    print(
        json.dumps(
            {
                "status": "EFFECT_WRITTEN",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "result_state": effect["result_state"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
