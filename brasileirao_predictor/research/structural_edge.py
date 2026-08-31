"""Detector governado de divergência Pinnacle versus casa soft.

Este módulo apenas produz candidatos para observação/paper-trading. Ele não
calcula stake, não executa apostas e nunca libera capital.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import numpy as np
from scipy.optimize import brentq

from brasileirao_predictor.math_utils import shin_probabilities

CapitalGate = Literal["CAPITAL_GATE: LOCKED"]
DevigMethod = Literal["shin", "power"]


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


@dataclass(frozen=True)
class MarketSnapshot:
    """Complete, canonical market observed at one real point in time."""

    event_id: str
    bookmaker: str
    market: str
    line: float | None
    captured_at: datetime
    kickoff_at: datetime
    odds: dict[str, float]
    mapping_version: str

    def __post_init__(self) -> None:
        _require_aware(self.captured_at, "captured_at")
        _require_aware(self.kickoff_at, "kickoff_at")
        if not self.event_id.strip() or not self.bookmaker.strip() or not self.market.strip():
            raise ValueError("event_id, bookmaker and market are required")
        if not self.mapping_version.strip():
            raise ValueError("mapping_version is required for auditable identity")
        if self.captured_at >= self.kickoff_at:
            raise ValueError("snapshot must be available strictly before kickoff")
        if len(self.odds) < 2:
            raise ValueError("a complete market needs at least two selections")
        for selection, odd in self.odds.items():
            if not selection.strip() or not np.isfinite(odd) or odd <= 1.0:
                raise ValueError("selections must be named and decimal odds finite and > 1")


@dataclass(frozen=True)
class StructuralEdgePolicy:
    reference_book: str = "pinnacle"
    ev_threshold: float = 0.03
    max_reference_staleness_seconds: int = 300
    devig_method: DevigMethod = "shin"

    def __post_init__(self) -> None:
        if not 0.0 < self.ev_threshold < 1.0:
            raise ValueError("ev_threshold must be between 0 and 1")
        if self.max_reference_staleness_seconds <= 0:
            raise ValueError("max_reference_staleness_seconds must be positive")


@dataclass(frozen=True)
class StructuralEdgeAlert:
    event_id: str
    market: str
    line: float | None
    selection: str
    reference_book: str
    soft_book: str
    fair_probability: float
    soft_odds: float
    expected_value: float
    evaluated_at: datetime
    signal: Literal["PAPER_CANDIDATE"] = "PAPER_CANDIDATE"
    scientific_state: Literal["SHADOW_ONLY"] = "SHADOW_ONLY"
    economic_evidence_eligible: Literal[False] = False
    capital_gate: CapitalGate = "CAPITAL_GATE: LOCKED"


@dataclass(frozen=True)
class StructuralEdgeEvaluation:
    fair_probabilities: dict[str, float]
    reference_overround: float
    alerts: tuple[StructuralEdgeAlert, ...]
    capital_gate: CapitalGate = "CAPITAL_GATE: LOCKED"


def power_probabilities(odds: list[float]) -> tuple[np.ndarray, float, float]:
    """Remove overround with the power method, returning probabilities, k, margin."""

    if len(odds) < 2 or any(not np.isfinite(odd) or odd <= 1.0 for odd in odds):
        raise ValueError("power devig requires at least two finite decimal odds > 1")
    implied = np.asarray([1.0 / odd for odd in odds], dtype=float)
    booksum = float(implied.sum())
    if booksum <= 1.0:
        return implied / booksum, 1.0, booksum - 1.0
    exponent = float(brentq(lambda k: float(np.power(implied, k).sum()) - 1.0, 1.0, 20.0))
    probabilities = np.power(implied, exponent)
    return probabilities / probabilities.sum(), exponent, booksum - 1.0


def detect_structural_edges(
    reference: MarketSnapshot,
    soft: MarketSnapshot,
    *,
    evaluated_at: datetime,
    policy: StructuralEdgePolicy = StructuralEdgePolicy(),
) -> StructuralEdgeEvaluation:
    """Compare synchronous canonical markets and emit shadow-only candidates."""

    _require_aware(evaluated_at, "evaluated_at")
    if reference.bookmaker.casefold() != policy.reference_book.casefold():
        raise ValueError("reference snapshot is not from the frozen reference book")
    if soft.bookmaker.casefold() == reference.bookmaker.casefold():
        raise ValueError("soft book must differ from reference book")
    reference_key = (reference.event_id, reference.market, reference.line, reference.mapping_version)
    soft_key = (soft.event_id, soft.market, soft.line, soft.mapping_version)
    if reference_key != soft_key or set(reference.odds) != set(soft.odds):
        raise ValueError("event, market, line, mapping version and selections must match exactly")
    if reference.kickoff_at != soft.kickoff_at or evaluated_at >= reference.kickoff_at:
        raise ValueError("kickoff identity must match and evaluation must be pre-kickoff")
    if reference.captured_at > evaluated_at or soft.captured_at > evaluated_at:
        raise ValueError("future snapshots are forbidden")
    staleness = (evaluated_at - reference.captured_at).total_seconds()
    if staleness > policy.max_reference_staleness_seconds:
        raise ValueError("reference snapshot is stale")

    selections = sorted(reference.odds)
    reference_odds = [reference.odds[selection] for selection in selections]
    if policy.devig_method == "shin":
        probabilities, _, overround = shin_probabilities(reference_odds)
    else:
        probabilities, _, overround = power_probabilities(reference_odds)
    fair = {selection: float(probability) for selection, probability in zip(selections, probabilities, strict=True)}
    alerts = tuple(
        StructuralEdgeAlert(
            event_id=reference.event_id,
            market=reference.market,
            line=reference.line,
            selection=selection,
            reference_book=reference.bookmaker,
            soft_book=soft.bookmaker,
            fair_probability=fair[selection],
            soft_odds=soft.odds[selection],
            expected_value=fair[selection] * soft.odds[selection] - 1.0,
            evaluated_at=evaluated_at,
        )
        for selection in selections
        if fair[selection] * soft.odds[selection] - 1.0 > policy.ev_threshold
    )
    return StructuralEdgeEvaluation(fair_probabilities=fair, reference_overround=float(overround), alerts=alerts)
