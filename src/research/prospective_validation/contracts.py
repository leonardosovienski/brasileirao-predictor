"""Contratos imutáveis para picks e liquidações prospectivas em papel."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _aware_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


class PaperPick(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pick_id: str = Field(min_length=1)
    cohort_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    market: str = Field(min_length=1)
    selection: str = Field(min_length=1)
    model_probability: float = Field(gt=0, lt=1)
    predicted_at: datetime
    kickoff_at: datetime
    odds_captured_at: datetime
    captured_odds: float = Field(gt=1)
    bookmaker: str = Field(min_length=1)
    stake_units: Literal[1.0] = 1.0
    scientific_state: Literal["PAPER_TRADING"] = "PAPER_TRADING"

    @model_validator(mode="after")
    def validate_clocks(self) -> PaperPick:
        for name in ("predicted_at", "kickoff_at", "odds_captured_at"):
            object.__setattr__(self, name, _aware_utc(getattr(self, name), name))
        if self.predicted_at >= self.kickoff_at or self.odds_captured_at > self.predicted_at:
            raise ValueError("pick and captured odds must be known before kickoff and prediction freeze")
        return self

    @property
    def record_hash(self) -> str:
        payload = self.model_dump(mode="json")
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class PaperSettlement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pick_id: str = Field(min_length=1)
    settled_at: datetime
    closing_odds: float = Field(gt=1)
    closing_captured_at: datetime
    won: bool
    result_source: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_clocks(self) -> PaperSettlement:
        for name in ("settled_at", "closing_captured_at"):
            object.__setattr__(self, name, _aware_utc(getattr(self, name), name))
        return self

    def assert_matches(self, pick: PaperPick) -> None:
        if self.pick_id != pick.pick_id:
            raise ValueError("settlement pick_id mismatch")
        if self.closing_captured_at >= pick.kickoff_at:
            raise ValueError("closing odds must be captured strictly before kickoff")
        if self.settled_at < pick.kickoff_at:
            raise ValueError("settlement cannot precede kickoff")
