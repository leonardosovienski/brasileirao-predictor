"""Conservative shadow-only economic decisions for model candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from brasileirao_predictor.research.market_residual import ResidualPrediction


@dataclass(frozen=True)
class ShadowDecision:
    action: str
    selection: str
    expected_value: float
    conservative_expected_value: float
    best_odds: float
    friction_rate: float
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
    friction_rate: float = 0.0,
    selection: str = "over",
) -> ShadowDecision:
    if best_odds <= 1 or not 0 <= minimum_conservative_edge < 1 or not 0 <= friction_rate < 1:
        raise ValueError("invalid economic policy")
    if selection not in {"over", "under"}:
        raise ValueError("selection must be over or under")
    if selection == "over":
        probability = prediction.probability
        conservative_probability = prediction.lower_probability
    else:
        probability = 1.0 - prediction.probability
        # The conservative lower bound for the complement is 1 - upper.
        conservative_probability = 1.0 - prediction.upper_probability
    ev = probability * best_odds - 1.0 - friction_rate
    conservative_ev = conservative_probability * best_odds - 1.0 - friction_rate
    if conservative_ev <= minimum_conservative_edge:
        return ShadowDecision("NO_BET", selection, ev, conservative_ev, best_odds, friction_rate, 0.0)
    # With a flat friction charged per staked unit, the winning net payoff is
    # b=(odds-1-friction) and the losing amount is l=(1+friction).  The binary
    # Kelly optimum is EV/(b*l); using odds-1 as the denominator is exact only
    # when friction is zero and otherwise overstates the stake.
    win_payoff = best_odds - 1.0 - friction_rate
    loss_amount = 1.0 + friction_rate
    full_kelly = max(0.0, conservative_ev / (win_payoff * loss_amount))
    stake = min(maximum_stake_units, kelly_fraction * full_kelly)
    # Candidate remains shadow-only even when it would have selected a quote.
    return ShadowDecision("SHADOW_BET", selection, ev, conservative_ev, best_odds, friction_rate, stake)


def choose_shadow_side(
    prediction: ResidualPrediction,
    *,
    odds_over: float,
    odds_under: float,
    friction_rate: float = 0.0,
    minimum_conservative_edge: float = 0.02,
) -> ShadowDecision:
    """Choose at most one side using conservative, post-friction EV.

    Both sides are evaluated from the same probabilistic forecast. Returning a
    single decision prevents a binary market from producing contradictory bets.
    """
    candidates = [
        decide_shadow(
            prediction,
            best_odds=odds_over,
            selection="over",
            friction_rate=friction_rate,
            minimum_conservative_edge=minimum_conservative_edge,
        ),
        decide_shadow(
            prediction,
            best_odds=odds_under,
            selection="under",
            friction_rate=friction_rate,
            minimum_conservative_edge=minimum_conservative_edge,
        ),
    ]
    eligible = [candidate for candidate in candidates if candidate.action == "SHADOW_BET"]
    if eligible:
        return max(eligible, key=lambda candidate: candidate.conservative_expected_value)
    return max(candidates, key=lambda candidate: candidate.conservative_expected_value)
