"""Conditional replay of frozen xG formulas, without attested availability.

The fixed 48-hour lag is an assumption for this diagnostic, not an observed
publication, completion, ingestion or receipt timestamp. This adapter creates
no XGObservation and does not call the strict research CLI. It reads only match
identity, kickoff, xG and (during calibration) goal labels from supplied rows;
it never accesses odds, files, databases or networks.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from brasileirao_predictor.research.price_strength.dynamic_xg import (
    DynamicXGConfig,
    _probabilities,
)

AVAILABILITY_POLICY = "ASSUMED_48H_NOT_OBSERVED"
STATUS = "CONDITIONAL_DIAGNOSTIC_NOT_PIT_ATTESTED"
ASSUMED_LAG = timedelta(hours=48)
CALIBRATION_START = datetime(2024, 1, 1, tzinfo=UTC)
CALIBRATION_END = datetime(2025, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class _Match:
    match_id: str
    event_id: int | str
    home: str
    away: str
    kickoff: datetime
    source: Mapping[str, Any]


def _clock(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("kickoff must include a timezone")
    return value.astimezone(UTC)


def _match(row: Mapping[str, Any]) -> _Match:
    if not isinstance(row, Mapping):
        raise TypeError("historical rows must be mappings")
    event_id = row.get("event_id")
    if type(event_id) is int:
        if event_id <= 0:
            raise ValueError("event_id must be positive")
    elif (
        not isinstance(event_id, str)
        or not event_id.strip()
        or event_id != event_id.strip()
    ):
        raise ValueError("event_id must be a positive integer or nonempty string")
    home, away = row.get("home"), row.get("away")
    if (
        any(not isinstance(team, str) or not team.strip() for team in (home, away))
        or home == away
    ):
        raise ValueError("home and away must be distinct nonempty team names")
    assert isinstance(home, str) and isinstance(away, str)
    return _Match(str(event_id), event_id, home, away, _clock(row.get("kickoff")), row)


def _prepare(rows: Iterable[Mapping[str, Any]]) -> tuple[_Match, ...]:
    prepared = tuple(_match(row) for row in rows)
    if len({row.match_id for row in prepared}) != len(prepared):
        # No revision timestamps exist here, so duplicates cannot be ordered.
        raise ValueError("duplicate event_id in conditional history")
    return tuple(sorted(prepared, key=lambda row: (row.kickoff, row.match_id)))


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError(
            f"{name} must be finite and {'positive' if positive else 'nonnegative'}"
        )
    return result


def _result(row: _Match) -> Mapping[str, Any] | None:
    result = row.source.get("result")
    if result is None:
        return None
    if not isinstance(result, Mapping):
        raise TypeError("result must be a mapping or null")
    return result


def _xg(row: _Match) -> tuple[float, float] | None:
    result = _result(row)
    if result is None or result.get("home_xg") is None or result.get("away_xg") is None:
        return None
    return _number(result["home_xg"], "home_xg"), _number(result["away_xg"], "away_xg")


def _goals(row: _Match) -> tuple[int, int] | None:
    result = _result(row)
    if result is None or (
        result.get("home_goals") is None and result.get("away_goals") is None
    ):
        return None
    home, away = result.get("home_goals"), result.get("away_goals")
    if type(home) is not int or type(away) is not int or home < 0 or away < 0:
        raise ValueError("both calibration goal labels must be nonnegative integers")
    return home, away


def _mean(
    history: list[tuple[_Match, tuple[float, float]]],
    side: int,
    prior: float,
    decision: datetime,
    config: DynamicXGConfig,
) -> float:
    # Operation order matches the frozen candidate's _mean exactly.
    weights = [
        0.5
        ** ((decision - row.kickoff).total_seconds() / 86400 / config.half_life_days)
        for row, _ in history
    ]
    numerator = math.fsum(
        [
            config.prior_weight * prior,
            *(weight * xg[side] for (_, xg), weight in zip(history, weights)),
        ]
    )
    return numerator / (config.prior_weight + math.fsum(weights))


def _forecast(
    rows: tuple[_Match, ...],
    target: _Match,
    config: DynamicXGConfig,
    calibration: Mapping[str, Any] | None,
) -> dict[str, Any]:
    decision = target.kickoff - timedelta(minutes=config.calibration_lead_minutes)
    if calibration is not None:
        if calibration.get("availability_policy") != AVAILABILITY_POLICY:
            raise ValueError("calibration must belong to the conditional diagnostic")
        if calibration.get("config_fingerprint") != config.fingerprint:
            raise ValueError("calibration belongs to another candidate configuration")
        if _clock(calibration.get("calibration_end")) >= decision:
            raise ValueError("calibration must end strictly before the decision")
        if target.match_id in calibration["used_match_ids"]:
            raise ValueError("target cannot contribute to its own calibration")
    visible = []
    excluded_missing_xg = []
    for row in rows:
        # Apply identity/time boundaries before reading xG or any label.
        if row.match_id == target.match_id or row.kickoff + ASSUMED_LAG >= decision:
            continue
        xg = _xg(row)
        if xg is None:
            excluded_missing_xg.append(row.match_id)
        else:
            visible.append((row, xg))
    home = [(row, xg) for row, xg in visible if row.home == target.home][
        -config.window_matches :
    ]
    away = [(row, xg) for row, xg in visible if row.away == target.away][
        -config.window_matches :
    ]
    metadata: dict[str, Any] = {
        "event_id": target.event_id,
        "decision_at": decision.isoformat(),
        "eligible": False,
        "reason": "INSUFFICIENT_HISTORY",
        "lambda_home": None,
        "lambda_away": None,
        "probabilities": {},
        "n_home": len(home),
        "n_away": len(away),
        "history_ids": sorted({row.match_id for row, _ in (*home, *away)}),
        "excluded_missing_xg_ids": sorted(excluded_missing_xg),
        "availability_policy": AVAILABILITY_POLICY,
        "assumed_lag_hours": 48,
        "config_fingerprint": config.fingerprint,
        "calibration_applied": False,
        "calibration_n": calibration["n_matches"] if calibration is not None else 0,
        "calibration_match_ids": list(calibration["used_match_ids"])
        if calibration is not None
        else [],
        "status": STATUS,
    }
    if len(home) < config.min_team_matches or len(away) < config.min_team_matches:
        return metadata
    if calibration is not None:
        n_matches = calibration["n_matches"]
        if (
            type(n_matches) is not int
            or n_matches < 0
            or type(calibration["eligible"]) is not bool
        ):
            raise ValueError("invalid calibration eligibility metadata")
        if not calibration["eligible"] or n_matches < config.min_calibration_matches:
            return {**metadata, "reason": "INSUFFICIENT_CALIBRATION"}
    home_lambda = (
        _mean(home, 0, config.prior_home_xg, decision, config)
        + _mean(away, 0, config.prior_home_xg, decision, config)
    ) / 2
    away_lambda = (
        _mean(away, 1, config.prior_away_xg, decision, config)
        + _mean(home, 1, config.prior_away_xg, decision, config)
    ) / 2
    if calibration is not None:
        home_lambda *= _number(calibration["home_scale"], "home_scale", positive=True)
        away_lambda *= _number(calibration["away_scale"], "away_scale", positive=True)
    return {
        **metadata,
        "eligible": True,
        "reason": "ELIGIBLE",
        "lambda_home": home_lambda,
        "lambda_away": away_lambda,
        "probabilities": _probabilities(home_lambda, away_lambda),
        "calibration_applied": calibration is not None,
    }


def forecast_conditional(
    rows: Iterable[Mapping[str, Any]],
    target: Mapping[str, Any],
    config: DynamicXGConfig,
    calibration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Forecast under an assumed 48-hour lag; no observed availability claim.

    Target xG and goals are never required or read. Missing historical xG pairs
    are excluded from strengths, while malformed visible numeric values fail.
    IDs in provenance are strings, matching the frozen candidate's IDs.
    """
    if not isinstance(config, DynamicXGConfig):
        raise TypeError("config must be the frozen DynamicXGConfig")
    return _forecast(_prepare(rows), _match(target), config, calibration)


def calibrate_conditional(
    rows: Iterable[Mapping[str, Any]], config: DynamicXGConfig
) -> dict[str, Any]:
    """Fit the same two rate scales using only 2024 calibration targets.

    A target must satisfy kickoff + 48h < 2025-01-01. Each raw forecast uses
    earlier history under that same assumed lag. Target xG is not needed for
    its label; missing xG excludes only that row's contribution to strengths.
    """
    if not isinstance(config, DynamicXGConfig):
        raise TypeError("config must be the frozen DynamicXGConfig")
    prepared = _prepare(rows)
    predicted_home: list[float] = []
    predicted_away: list[float] = []
    goals_home: list[int] = []
    goals_away: list[int] = []
    used_ids: set[str] = set()
    target_ids: list[str] = []
    for target in prepared:
        if (
            target.kickoff < CALIBRATION_START
            or target.kickoff + ASSUMED_LAG >= CALIBRATION_END
        ):
            continue
        goals = _goals(target)
        if goals is None:
            continue
        raw = _forecast(prepared, target, config, None)
        if not raw["eligible"]:
            continue
        predicted_home.append(raw["lambda_home"])
        predicted_away.append(raw["lambda_away"])
        goals_home.append(goals[0])
        goals_away.append(goals[1])
        target_ids.append(target.match_id)
        used_ids.update((*raw["history_ids"], target.match_id))
    n_matches = len(predicted_home)
    eligible = n_matches >= config.min_calibration_matches
    prior = config.calibration_prior_exposure
    return {
        "n_matches": n_matches,
        "eligible": eligible,
        "reason": "ELIGIBLE" if eligible else "INSUFFICIENT_CALIBRATION",
        "home_scale": (math.fsum(goals_home) + prior)
        / (math.fsum(predicted_home) + prior)
        if eligible
        else 1.0,
        "away_scale": (math.fsum(goals_away) + prior)
        / (math.fsum(predicted_away) + prior)
        if eligible
        else 1.0,
        "used_match_ids": sorted(used_ids),
        "target_match_ids": target_ids,
        "config_fingerprint": config.fingerprint,
        "training_end": CALIBRATION_START.isoformat(),
        "calibration_end": CALIBRATION_END.isoformat(),
        "availability_policy": AVAILABILITY_POLICY,
        "assumed_lag_hours": 48,
        "status": STATUS,
    }
