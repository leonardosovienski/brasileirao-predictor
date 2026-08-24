"""Contratos fail-closed para futuras features PIT pré-jogo."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

FeatureFamily = Literal["absences", "lineup", "isolated_xg", "hierarchical_home_advantage"]


class FeatureDeclaration(BaseModel):
    """Mecanismo congelável antes de qualquer materialização ou teste de efeito."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feature_family: FeatureFamily
    version: str = Field(min_length=1)
    mechanism_ex_ante: str = Field(min_length=20)
    required_source_fields: tuple[str, ...] = Field(min_length=1)
    output_contract: tuple[str, ...] = Field(min_length=1)
    provenance_policy: str = Field(min_length=20)
    training_status: Literal["SCAFFOLD_ONLY_TRAINING_BLOCKED"] = "SCAFFOLD_ONLY_TRAINING_BLOCKED"


class PITFeatureEvidence(BaseModel):
    """Envelope cuja elegibilidade é decidida pelo relógio de disponibilidade real."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(min_length=1)
    feature_family: FeatureFamily
    declaration_version: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_record_id: str = Field(min_length=1)
    observed_at: datetime
    available_at: datetime
    ingested_at: datetime
    kickoff_at: datetime
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_point_in_time_clocks(self) -> PITFeatureEvidence:
        clocks = ("observed_at", "available_at", "ingested_at", "kickoff_at")
        for name in clocks:
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
            object.__setattr__(self, name, value.astimezone(UTC))
        if self.available_at < self.observed_at:
            raise ValueError("available_at cannot precede observed_at")
        if self.ingested_at < self.available_at:
            raise ValueError("ingested_at cannot precede available_at")
        if self.available_at >= self.kickoff_at:
            raise ValueError("feature information must be available strictly before kickoff")
        return self

    def assert_matches(self, declaration: FeatureDeclaration) -> None:
        if self.feature_family != declaration.feature_family:
            raise ValueError("evidence feature_family does not match declaration")
        if self.declaration_version != declaration.version:
            raise ValueError("evidence declaration_version does not match declaration")
        missing = set(declaration.required_source_fields) - self.payload.keys()
        if missing:
            raise ValueError(f"payload missing declared source fields: {sorted(missing)}")


@runtime_checkable
class PITFeatureExtractor(Protocol):
    """Future extractors must expose declaration and preserve evidence clocks."""

    declaration: FeatureDeclaration

    def materialize(self, evidence: PITFeatureEvidence) -> dict[str, float | int | str | bool | None]: ...


class ExternalResearchGate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    phase0b_go: bool = False
    live_viability_go: bool = False
    evidence_reference: str | None = None


def assert_training_unlocked(gate: ExternalResearchGate) -> None:
    """Training remains impossible until one external workstream produces GO."""
    if not (gate.phase0b_go or gate.live_viability_go):
        raise RuntimeError("PIT feature training blocked until Phase 0B or live viability produces GO")
    if not gate.evidence_reference:
        raise RuntimeError("training GO requires an immutable evidence reference")
