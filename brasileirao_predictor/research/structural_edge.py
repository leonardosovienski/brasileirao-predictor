"""Detector governado de divergência Pinnacle versus casa soft.

Este módulo apenas produz candidatos para observação/paper-trading. Ele não
calcula stake, não executa apostas e nunca libera capital.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from numbers import Real
from types import MappingProxyType
from typing import Literal

import numpy as np
from scipy.optimize import brentq

from brasileirao_predictor.math_utils import shin_probabilities

CapitalGate = Literal["CAPITAL_GATE: LOCKED"]
DevigMethod = Literal["shin", "power"]


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _finite(value: object) -> bool:
    try:
        return not isinstance(value, bool) and isinstance(value, Real) and math.isfinite(value)
    except (OverflowError, TypeError):
        return False


@dataclass(frozen=True)
class MarketSnapshot:
    """Caller-declared market and capture clock; no source authentication.

    The caller must supply canonical, complete selections. This legacy
    interface has no publication/receipt split, status revisions or fills.
    """

    event_id: str
    bookmaker: str
    market: str
    line: float | None
    captured_at: datetime
    kickoff_at: datetime
    odds: Mapping[str, float]
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
        if self.line is not None and not _finite(self.line):
            raise ValueError("market line must be finite or absent")
        if not isinstance(self.odds, Mapping) or len(self.odds) < 2:
            raise ValueError("a complete market needs at least two selections")
        copied = dict(self.odds)
        for selection, odd in copied.items():
            if not isinstance(selection, str) or not selection.strip() or not _finite(odd) or odd <= 1.0:
                raise ValueError("selections must be named and decimal odds finite and > 1")
        object.__setattr__(self, "odds", MappingProxyType(copied))


@dataclass(frozen=True)
class StructuralEdgePolicy:
    reference_book: str = "pinnacle"
    ev_threshold: float = 0.03
    max_reference_staleness_seconds: int = 300
    devig_method: DevigMethod = "shin"

    def __post_init__(self) -> None:
        if not _finite(self.ev_threshold) or not 0.0 < self.ev_threshold < 1.0:
            raise ValueError("ev_threshold must be between 0 and 1")
        if not _finite(self.max_reference_staleness_seconds) or self.max_reference_staleness_seconds <= 0:
            raise ValueError("max_reference_staleness_seconds must be positive")
        if not isinstance(self.reference_book, str) or not self.reference_book.strip():
            raise ValueError("reference_book must be explicit")
        if self.devig_method not in {"shin", "power"}:
            raise ValueError("devig_method must be shin or power")


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

    if len(odds) < 2 or any(not _finite(odd) or odd <= 1.0 for odd in odds):
        raise ValueError("power devig requires at least two finite decimal odds > 1")
    implied = np.asarray([1.0 / odd for odd in odds], dtype=float)
    booksum = float(implied.sum())
    if booksum <= 1.0:
        return implied / booksum, 1.0, booksum - 1.0
    # For k >= log(n)/-log(max(q)), every q**k <= 1/n. A factor of two
    # gives a strict upper bracket even for valid odds extremely close to one.
    upper = max(2.0, 2 * math.log(len(odds)) / -math.log(float(implied.max())))
    root, _ = brentq(lambda k: float(np.power(implied, k).sum()) - 1.0, 1.0, upper, full_output=True)
    exponent = float(root)
    probabilities = np.power(implied, exponent)
    return probabilities / probabilities.sum(), exponent, booksum - 1.0


def detect_structural_edges(
    reference: MarketSnapshot,
    soft: MarketSnapshot,
    *,
    evaluated_at: datetime,
    policy: StructuralEdgePolicy = StructuralEdgePolicy(),
) -> StructuralEdgeEvaluation:
    """Compare bounded-age declared markets and emit shadow-only candidates.

    The age bound applies to both sides. It does not prove continuous or
    simultaneous commercial availability; use the stronger quote contracts
    for admission to a new point-in-time study.
    """

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
    if (evaluated_at - soft.captured_at).total_seconds() > policy.max_reference_staleness_seconds:
        raise ValueError("offer snapshot is stale")

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
