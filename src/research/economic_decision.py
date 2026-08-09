"""Conservative shadow-only economic decisions for model candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from src.research.market_residual import ResidualPrediction


@dataclass(frozen=True)
class ShadowDecision:
    action: str
    expected_value: float
    conservative_expected_value: float
    best_odds: float
    stake_units: float
    scientific_state: str = "SHADOW"
    capital_enabled: bool = False

    def to_dict(self):
        return asdict(self)


def decide_shadow(
    prediction: ResidualPrediction,
    *,
    best_odds: float,
    minimum_conservative_edge: float = 0.02,
    kelly_fraction: float = 0.10,
    maximum_stake_units: float = 0.25,
) -> ShadowDecision:
    if best_odds <= 1 or not 0 <= minimum_conservative_edge < 1:
        raise ValueError("invalid economic policy")
    ev = prediction.probability * best_odds - 1.0
    conservative_ev = prediction.lower_probability * best_odds - 1.0
    if conservative_ev <= minimum_conservative_edge:
        return ShadowDecision("NO_BET", ev, conservative_ev, best_odds, 0.0)
    full_kelly = max(0.0, (prediction.lower_probability * best_odds - 1.0) / (best_odds - 1.0))
    stake = min(maximum_stake_units, kelly_fraction * full_kelly)
    # Candidate remains shadow-only even when it would have selected a quote.
    return ShadowDecision("SHADOW_BET", ev, conservative_ev, best_odds, stake)
