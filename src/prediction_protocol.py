"""Fail-closed readiness checks for official football predictions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictionReadinessInput(BaseModel):
    """Point-in-time evidence required before an official prediction is emitted."""

    model_config = ConfigDict(extra="forbid")

    prediction_kind: Literal["PRE_MATCH", "LIVE", "RETROSPECTIVE_SIMULATION"]
    event_id: str = Field(min_length=1)
    home: str = Field(min_length=1)
    away: str = Field(min_length=1)
    predicted_at: datetime
    kickoff_at: datetime
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    pipeline_fingerprint: str = Field(min_length=1)
    historical_data_cutoff: datetime
    latest_training_match_kickoff: datetime
    latest_training_result_available_at: datetime
    current_season_matches_included: int = Field(ge=0)
    current_season_matches_available: int = Field(ge=0)
    lineup_captured_at: datetime | None = None
    lineup_confirmed: bool | None = None
    odds_captured_at: datetime | None = None
    live_observed_at: datetime | None = None
    observed_minute: int | None = Field(default=None, ge=0, le=130)
    current_score: tuple[int, int] | None = None
    unvalidated_live_features_injected: bool = False
    capital_enabled: bool = False

    @model_validator(mode="after")
    def validate_aware_datetimes(self) -> PredictionReadinessInput:
        for name in (
            "predicted_at",
            "kickoff_at",
            "historical_data_cutoff",
            "latest_training_match_kickoff",
            "latest_training_result_available_at",
            "lineup_captured_at",
            "odds_captured_at",
            "live_observed_at",
        ):
            value = getattr(self, name)
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{name} must be timezone-aware")
        return self


class ReadinessFinding(BaseModel):
    code: str
    message: str


class PredictionReadinessReport(BaseModel):
    protocol_version: Literal["prediction-readiness/1"] = "prediction-readiness/1"
    ready: bool
    designation: Literal["OFFICIAL_PRE_MATCH", "OFFICIAL_LIVE", "RETROSPECTIVE_ONLY", "BLOCKED"]
    blockers: list[ReadinessFinding]
    warnings: list[ReadinessFinding]


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def assess_prediction_readiness(candidate: PredictionReadinessInput | dict[str, Any]) -> PredictionReadinessReport:
    """Apply chronology, completeness and governance gates without touching data."""
    item = (
        candidate
        if isinstance(candidate, PredictionReadinessInput)
        else PredictionReadinessInput.model_validate(candidate)
    )
    blockers: list[ReadinessFinding] = []
    warnings: list[ReadinessFinding] = []

    def block(code: str, message: str) -> None:
        blockers.append(ReadinessFinding(code=code, message=message))

    def warn(code: str, message: str) -> None:
        warnings.append(ReadinessFinding(code=code, message=message))

    predicted = _utc(item.predicted_at)
    kickoff = _utc(item.kickoff_at)
    if item.capital_enabled:
        block("CAPITAL_BLOCKED", "capital must remain disabled")
    if _utc(item.historical_data_cutoff) > predicted:
        block("FUTURE_DATA_CUTOFF", "historical data cutoff is later than predicted_at")
    if _utc(item.latest_training_match_kickoff) >= predicted:
        block("TRAINING_MATCH_NOT_PRIOR", "every training match kickoff must be earlier than predicted_at")
    if _utc(item.latest_training_result_available_at) > predicted:
        block("RESULT_NOT_AVAILABLE", "a training result was not available at predicted_at")
    if item.current_season_matches_included != item.current_season_matches_available:
        block(
            "INCOMPLETE_CURRENT_HISTORY",
            "all eligible current-season matches available at predicted_at must be included",
        )
    if item.lineup_captured_at and _utc(item.lineup_captured_at) > predicted:
        block("FUTURE_LINEUP", "lineup capture is later than predicted_at")
    if item.odds_captured_at and _utc(item.odds_captured_at) > predicted:
        block("FUTURE_ODDS", "odds capture is later than predicted_at")

    designation: Literal["OFFICIAL_PRE_MATCH", "OFFICIAL_LIVE", "RETROSPECTIVE_ONLY", "BLOCKED"]
    if item.prediction_kind == "PRE_MATCH":
        if predicted >= kickoff:
            block("POST_KICKOFF_PRE_MATCH", "a pre-match prediction must be frozen before kickoff")
        if item.lineup_confirmed is None:
            block("LINEUP_STATUS_UNKNOWN", "lineup_confirmed must be explicitly true or false")
        designation = "OFFICIAL_PRE_MATCH"
    elif item.prediction_kind == "LIVE":
        if predicted < kickoff:
            block("LIVE_BEFORE_KICKOFF", "a live prediction cannot precede kickoff")
        if item.live_observed_at is None or item.observed_minute is None or item.current_score is None:
            block("LIVE_STATE_MISSING", "live observed_at, minute and score are mandatory")
        elif _utc(item.live_observed_at) > predicted:
            block("FUTURE_LIVE_STATE", "live state is later than predicted_at")
        if item.unvalidated_live_features_injected:
            block("UNVALIDATED_LIVE_FEATURES", "live features without validated weights cannot enter the model")
        designation = "OFFICIAL_LIVE"
    else:
        designation = "RETROSPECTIVE_ONLY"
        warn("NOT_PROSPECTIVE", "simulation must never be reported as an official prospective prediction")

    if item.lineup_captured_at is None:
        warn("LINEUP_UNAVAILABLE", "prediction may run, but must declare that no point-in-time lineup was available")
    if item.odds_captured_at is None:
        warn("MARKET_UNAVAILABLE", "prediction may run, but no point-in-time market comparison is possible")
    if blockers:
        designation = "BLOCKED"
    return PredictionReadinessReport(
        ready=not blockers,
        designation=designation,
        blockers=blockers,
        warnings=warnings,
    )
