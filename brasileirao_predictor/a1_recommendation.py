"""Escala auditável para candidatos A1, sempre separada da chance do resultado."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Literal

EvidenceStage = Literal["PHASE0", "SHADOW", "CLV_CONFIRMED"]


@dataclass(frozen=True)
class RecommendationInput:
    event_probability: float
    soft_odds: float
    probability_uncertainty: float
    friction_rate: float
    data_quality: float
    reference_complete: bool
    soft_complete: bool
    executable: bool
    reference_stale: bool
    evidence_stage: EvidenceStage = "PHASE0"
    clv_ci95_lower: float | None = None

    def __post_init__(self) -> None:
        for name in ("event_probability", "probability_uncertainty", "friction_rate", "data_quality"):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and between 0 and 1")
        if not math.isfinite(self.soft_odds) or self.soft_odds <= 1:
            raise ValueError("soft_odds must be finite and greater than 1")


@dataclass(frozen=True)
class Recommendation:
    outcome_probability_pct: float
    gross_ev_pct: float
    conservative_net_ev_pct: float
    indication_score: int
    action: Literal["NO_BET", "SHADOW_OBSERVE", "SHADOW_CANDIDATE"]
    score_cap: int
    reasons: tuple[str, ...]
    capital_enabled: Literal[False] = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_recommendation(candidate: RecommendationInput, *, strong_edge: float = 0.05) -> Recommendation:
    """Score 0--100; it is an index of evidence, never a win probability.

    The score uses a lower probability bound and explicit friction. Stage caps
    prevent operational or weak shadow evidence from looking like certainty.
    """
    if not math.isfinite(strong_edge) or strong_edge <= 0:
        raise ValueError("strong_edge must be finite and positive")
    gross_ev = candidate.event_probability * candidate.soft_odds - 1
    lower_probability = max(0.0, candidate.event_probability - candidate.probability_uncertainty)
    conservative_net_ev = lower_probability * candidate.soft_odds - 1 - candidate.friction_rate
    reasons: list[str] = []
    hard_gate = False
    if not candidate.reference_complete:
        reasons.append("reference_incomplete")
        hard_gate = True
    if not candidate.soft_complete:
        reasons.append("soft_market_incomplete")
        hard_gate = True
    if not candidate.executable:
        reasons.append("not_executable")
        hard_gate = True
    if candidate.reference_stale:
        reasons.append("reference_stale")
        hard_gate = True
    if conservative_net_ev <= 0:
        reasons.append("conservative_net_ev_not_positive")
        hard_gate = True

    if candidate.evidence_stage == "PHASE0":
        cap = 10
        reasons.append("phase0_cap")
    elif candidate.evidence_stage == "SHADOW":
        cap = 40
        reasons.append("shadow_without_confirmed_clv_cap")
    else:
        if candidate.clv_ci95_lower is None or candidate.clv_ci95_lower <= 0:
            cap = 40
            reasons.append("clv_ci95_lower_not_positive")
        else:
            cap = 100

    if hard_gate:
        score = 0
        action: Literal["NO_BET", "SHADOW_OBSERVE", "SHADOW_CANDIDATE"] = "NO_BET"
    else:
        raw = 100 * min(1.0, conservative_net_ev / strong_edge) * candidate.data_quality
        score = min(cap, max(1, round(raw)))
        action = "SHADOW_CANDIDATE" if score >= 50 else "SHADOW_OBSERVE"
    return Recommendation(
        outcome_probability_pct=round(100 * candidate.event_probability, 2),
        gross_ev_pct=round(100 * gross_ev, 2),
        conservative_net_ev_pct=round(100 * conservative_net_ev, 2),
        indication_score=score,
        action=action,
        score_cap=cap,
        reasons=tuple(reasons),
    )
