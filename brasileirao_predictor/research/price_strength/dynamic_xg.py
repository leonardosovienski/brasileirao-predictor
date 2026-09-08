"""Pure, unvalidated rolling-xG candidate in a new research lineage.

This is not the serving xG ensemble, a reproduction of Wheatcroft's GAP model,
or an activation of the legacy PIT scaffold. It has no file, database, network,
capital, or trial access. The current validation scope is synthetic fixtures.
Callers must establish admissible input provenance and a separate research
protocol before using real observations; an availability timestamp is an
assertion supplied by the caller, not independently certified by this module.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from scipy.stats import poisson, skellam

LINEAGE = "rolling-xg-price-strength/1"


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def _number(value: float, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'nonnegative'}")
    return float(value)


def _integer(value: int, name: str, *, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def _identity(match_id: str, home_team: str, away_team: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in (match_id, home_team, away_team)):
        raise ValueError("match_id and team names must be nonempty strings")
    if home_team == away_team:
        raise ValueError("home_team and away_team must differ")


@dataclass(frozen=True)
class DynamicXGConfig:
    """Explicit, untuned defaults; none were selected from project outcomes."""

    window_matches: int = 5
    min_team_matches: int = 3
    half_life_days: float = 90.0
    prior_weight: float = 2.0
    prior_home_xg: float = 1.5
    prior_away_xg: float = 1.2
    min_calibration_matches: int = 20
    calibration_prior_exposure: float = 5.0
    calibration_lead_minutes: int = 60

    def __post_init__(self) -> None:
        for field in ("window_matches", "min_team_matches", "min_calibration_matches", "calibration_lead_minutes"):
            _integer(getattr(self, field), field, minimum=1)
        if self.min_team_matches > self.window_matches:
            raise ValueError("min_team_matches cannot exceed window_matches")
        for field in ("half_life_days", "prior_weight", "prior_home_xg", "prior_away_xg", "calibration_prior_exposure"):
            object.__setattr__(self, field, _number(getattr(self, field), field, positive=True))

    @property
    def fingerprint(self) -> str:
        encoded = json.dumps({"lineage": LINEAGE, **asdict(self)}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True)
class Fixture:
    match_id: str
    home_team: str
    away_team: str
    kickoff: datetime

    def __post_init__(self) -> None:
        _identity(self.match_id, self.home_team, self.away_team)
        object.__setattr__(self, "kickoff", _utc(self.kickoff, "kickoff"))


@dataclass(frozen=True)
class XGObservation:
    """Completed match statistics and their actual first availability/revision."""

    match_id: str
    home_team: str
    away_team: str
    kickoff: datetime
    completed_at: datetime
    available_at: datetime
    home_xg: float
    away_xg: float
    home_goals: int | None = None
    away_goals: int | None = None

    def __post_init__(self) -> None:
        _identity(self.match_id, self.home_team, self.away_team)
        for field in ("kickoff", "completed_at", "available_at"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if not self.kickoff < self.completed_at <= self.available_at:
            raise ValueError("required chronology: kickoff < completed_at <= available_at")
        for field in ("home_xg", "away_xg"):
            object.__setattr__(self, field, _number(getattr(self, field), field))
        if (self.home_goals is None) != (self.away_goals is None):
            raise ValueError("both goal counts must be supplied together")
        if self.home_goals is not None:
            assert self.away_goals is not None
            _integer(self.home_goals, "home_goals")
            _integer(self.away_goals, "away_goals")


@dataclass(frozen=True)
class LambdaCalibration:
    config_fingerprint: str
    training_end: datetime
    calibration_end: datetime
    eligible: bool
    reason: str
    n_matches: int
    home_scale: float
    away_scale: float
    latest_available_at: datetime | None
    used_match_ids: tuple[str, ...]
    lineage: str = LINEAGE
    status: str = "UNVALIDATED_NEW_LINEAGE"

    def __post_init__(self) -> None:
        for field in ("training_end", "calibration_end"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.training_end >= self.calibration_end:
            raise ValueError("training_end must precede calibration_end")
        if type(self.eligible) is not bool:
            raise ValueError("calibration eligible must be a boolean")
        _integer(self.n_matches, "n_matches")
        for field in ("home_scale", "away_scale"):
            object.__setattr__(self, field, _number(getattr(self, field), field, positive=True))
        if self.latest_available_at is not None:
            object.__setattr__(self, "latest_available_at", _utc(self.latest_available_at, "latest_available_at"))
            if self.latest_available_at >= self.calibration_end:
                raise ValueError("calibration data must be available before calibration_end")


@dataclass(frozen=True)
class XGForecast:
    match_id: str
    decision_at: datetime
    eligible: bool
    reason: str
    lambda_home: float | None
    lambda_away: float | None
    probabilities: dict[str, dict[str, float]]
    n_home: int
    n_away: int
    latest_available_at: datetime | None
    history_match_ids: tuple[str, ...]
    config_fingerprint: str
    calibration_applied: bool = False
    calibration_n: int = 0
    calibration_match_ids: tuple[str, ...] = ()
    lineage: str = LINEAGE
    status: str = "UNVALIDATED_NEW_LINEAGE"


def _visible(
    observations: Iterable[XGObservation], cutoff: datetime, excluded_id: str | None = None
) -> list[XGObservation]:
    latest: dict[str, XGObservation] = {}
    versions: dict[tuple[str, datetime], XGObservation] = {}
    for item in observations:
        if item.match_id == excluded_id or item.kickoff >= cutoff or item.available_at >= cutoff:
            continue
        previous = latest.get(item.match_id)
        if previous is not None:
            if (item.home_team, item.away_team, item.kickoff) != (
                previous.home_team,
                previous.away_team,
                previous.kickoff,
            ):
                raise ValueError("conflicting match identity in visible observations")
        version_key = (item.match_id, item.available_at)
        same_time = versions.get(version_key)
        if same_time is not None and item != same_time:
            raise ValueError("conflicting statistics at the same availability timestamp")
        # Retain every visible revision for conflict checks: a newer revision
        # must not hide contradictory older deliveries based on input order.
        versions[version_key] = item
        if previous is None or item.available_at > previous.available_at:
            latest[item.match_id] = item
    return sorted(latest.values(), key=lambda item: (item.kickoff, item.match_id))


def _mean(
    history: list[XGObservation], field: str, prior: float, decision_at: datetime, config: DynamicXGConfig
) -> float:
    weights = [
        0.5 ** ((decision_at - item.kickoff).total_seconds() / 86400 / config.half_life_days) for item in history
    ]
    numerator = math.fsum(
        [config.prior_weight * prior, *(w * getattr(item, field) for item, w in zip(history, weights))]
    )
    return numerator / (config.prior_weight + math.fsum(weights))


def _normalize(values: dict[str, float]) -> dict[str, float]:
    if any(not math.isfinite(value) or value < 0 for value in values.values()):
        raise ValueError("Poisson probabilities are not representable")
    total = math.fsum(values.values())
    if total <= 0:
        raise ValueError("Poisson probabilities have zero mass")
    return {key: value / total for key, value in values.items()}


def _probabilities(home: float, away: float) -> dict[str, dict[str, float]]:
    _number(home, "lambda_home", positive=True)
    _number(away, "lambda_away", positive=True)
    _number(home + away, "total_lambda", positive=True)
    # Analytic distributions avoid dropping the tail of a truncated goal grid.
    result = _normalize(
        {
            "home": float(skellam.sf(0, home, away)),
            "draw": float(skellam.pmf(0, home, away)),
            "away": float(skellam.cdf(-1, home, away)),
        }
    )
    under = float(poisson.cdf(2, home + away))
    btts = (-math.expm1(-home)) * (-math.expm1(-away))
    return {
        "1x2": result,
        "ou25": _normalize({"over": 1 - under, "under": under}),
        "btts": _normalize({"yes": btts, "no": 1 - btts}),
    }


def forecast(
    observations: Iterable[XGObservation],
    fixture: Fixture,
    decision_at: datetime,
    config: DynamicXGConfig,
    calibration: LambdaCalibration | None = None,
) -> XGForecast:
    """Pre-match forecast using only strictly available, completed observations.

    For each team only its most recent ``window_matches`` appearances in the
    fixture's venue role are used. Home intensity averages home attacking xG
    and away-team home xG conceded; away intensity uses the converse. Means
    decay by match kickoff and shrink towards explicit venue-specific priors.
    """
    decision_at = _utc(decision_at, "decision_at")
    if decision_at >= fixture.kickoff:
        raise ValueError("decision_at must precede fixture kickoff")
    if calibration is not None:
        if calibration.config_fingerprint != config.fingerprint:
            raise ValueError("calibration belongs to a different candidate configuration")
        if calibration.calibration_end >= decision_at:
            raise ValueError("calibration must end strictly before decision_at")
        if fixture.match_id in calibration.used_match_ids:
            raise ValueError("the forecast fixture cannot contribute to its own calibration")
    visible = _visible(observations, decision_at, fixture.match_id)
    home = [item for item in visible if item.home_team == fixture.home_team][-config.window_matches :]
    away = [item for item in visible if item.away_team == fixture.away_team][-config.window_matches :]
    history = {item.match_id: item for item in (*home, *away)}
    availability = [item.available_at for item in history.values()]
    if calibration is not None and calibration.latest_available_at is not None:
        availability.append(calibration.latest_available_at)
    metadata = {
        "match_id": fixture.match_id,
        "decision_at": decision_at,
        "n_home": len(home),
        "n_away": len(away),
        "latest_available_at": max(availability, default=None),
        "history_match_ids": tuple(sorted(history)),
        "config_fingerprint": config.fingerprint,
        "calibration_n": calibration.n_matches if calibration is not None else 0,
        "calibration_match_ids": calibration.used_match_ids if calibration is not None else (),
    }
    if len(home) < config.min_team_matches or len(away) < config.min_team_matches:
        return XGForecast(
            eligible=False,
            reason="INSUFFICIENT_HISTORY",
            lambda_home=None,
            lambda_away=None,
            probabilities={},
            **metadata,
        )
    if calibration is not None and (not calibration.eligible or calibration.n_matches < config.min_calibration_matches):
        return XGForecast(
            eligible=False,
            reason="INSUFFICIENT_CALIBRATION",
            lambda_home=None,
            lambda_away=None,
            probabilities={},
            **metadata,
        )
    lambda_home = (
        _mean(home, "home_xg", config.prior_home_xg, decision_at, config)
        + _mean(away, "home_xg", config.prior_home_xg, decision_at, config)
    ) / 2
    lambda_away = (
        _mean(away, "away_xg", config.prior_away_xg, decision_at, config)
        + _mean(home, "away_xg", config.prior_away_xg, decision_at, config)
    ) / 2
    if calibration is not None:
        lambda_home *= calibration.home_scale
        lambda_away *= calibration.away_scale
    return XGForecast(
        eligible=True,
        reason="ELIGIBLE",
        lambda_home=lambda_home,
        lambda_away=lambda_away,
        probabilities=_probabilities(lambda_home, lambda_away),
        calibration_applied=calibration is not None,
        **metadata,
    )


def fit_calibration(
    observations: Iterable[XGObservation],
    training_end: datetime,
    calibration_end: datetime,
    config: DynamicXGConfig,
) -> LambdaCalibration:
    """Fit two goal-rate scales from historical forecasts and available labels.

    Calibration targets have kickoff in [training_end, calibration_end), with
    results strictly available before calibration_end. Each raw forecast is
    reconstructed at kickoff minus the configured lead, excluding its target.
    Rolling strengths may update from earlier available calibration matches;
    neither a target's own statistics nor later observations enter its forecast.
    ``training_end`` is the target-window boundary, not a freeze of dynamic
    strengths. Gamma-style prior exposure shrinks each positive scale to one.
    """
    training_end = _utc(training_end, "training_end")
    calibration_end = _utc(calibration_end, "calibration_end")
    if training_end >= calibration_end:
        raise ValueError("training_end must precede calibration_end")
    observations = tuple(observations)
    targets = [
        item
        for item in _visible(observations, calibration_end)
        if item.kickoff >= training_end and item.home_goals is not None
    ]
    predicted_home: list[float] = []
    predicted_away: list[float] = []
    goals_home: list[int] = []
    goals_away: list[int] = []
    used_ids: set[str] = set()
    latest_available_at: datetime | None = None
    for target in targets:
        raw = forecast(
            observations,
            Fixture(target.match_id, target.home_team, target.away_team, target.kickoff),
            target.kickoff - timedelta(minutes=config.calibration_lead_minutes),
            config,
        )
        if not raw.eligible:
            continue
        assert raw.lambda_home is not None and raw.lambda_away is not None
        assert target.home_goals is not None and target.away_goals is not None
        predicted_home.append(raw.lambda_home)
        predicted_away.append(raw.lambda_away)
        goals_home.append(target.home_goals)
        goals_away.append(target.away_goals)
        used_ids.update((*raw.history_match_ids, target.match_id))
        latest_available_at = max(latest_available_at or target.available_at, target.available_at)
    n_matches = len(predicted_home)
    eligible = n_matches >= config.min_calibration_matches
    prior = config.calibration_prior_exposure
    return LambdaCalibration(
        config_fingerprint=config.fingerprint,
        training_end=training_end,
        calibration_end=calibration_end,
        eligible=eligible,
        reason="ELIGIBLE" if eligible else "INSUFFICIENT_CALIBRATION",
        n_matches=n_matches,
        home_scale=(math.fsum(goals_home) + prior) / (math.fsum(predicted_home) + prior) if eligible else 1.0,
        away_scale=(math.fsum(goals_away) + prior) / (math.fsum(predicted_away) + prior) if eligible else 1.0,
        latest_available_at=latest_available_at,
        used_match_ids=tuple(sorted(used_ids)),
    )
