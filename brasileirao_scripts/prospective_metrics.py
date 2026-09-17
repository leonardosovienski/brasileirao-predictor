"""Pure prospective scoring components; no cohort IO or evaluation authority.

OU uses the project's two-class summed Brier convention (0..2), not the
single-probability convention (0..1). Inputs must be original recorded forecasts.
Holm consumes externally validated p-values; this module does not invent a
p-value estimator from the existing bootstrap confidence intervals.
"""

import math


def brier_ou25(p_over: float, home_goals: int, away_goals: int) -> float:
    if isinstance(p_over, bool) or not isinstance(p_over, (int, float)):
        raise ValueError("OU2.5 probability must be numeric")
    if not math.isfinite(p_over) or not 0 <= p_over <= 1:
        raise ValueError("OU2.5 probability must be finite and in [0, 1]")
    if any(type(score) is not int or score < 0 for score in (home_goals, away_goals)):
        raise ValueError("Final goal counts must be nonnegative integers")
    actual = int(home_goals + away_goals >= 3)
    return 2 * (p_over - actual) ** 2


def holm_family(p_values: dict[str, float], *, expected_ids: tuple[str, ...], alpha: float = 0.05) -> dict:
    """Whole-family Holm step-down; missing members cannot shrink multiplicity."""
    if not expected_ids or len(set(expected_ids)) != len(expected_ids) or set(p_values) != set(expected_ids):
        raise ValueError("Exactly the complete declared family is required")
    if type(alpha) not in (int, float) or not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("Invalid family alpha")
    for value in p_values.values():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ValueError("Invalid p-value")
    ordered = sorted(p_values, key=lambda key: (p_values[key], key))
    adjusted, previous = {}, 0.0
    for rank, key in enumerate(ordered):
        previous = max(previous, min(1.0, (len(ordered) - rank) * p_values[key]))
        adjusted[key] = previous
    return {
        "method": "Holm step-down",
        "alpha": alpha,
        "family_size": len(expected_ids),
        "adjusted_p_values": adjusted,
        "rejected": {key: adjusted[key] <= alpha for key in ordered},
        "capital_enabled": False,
        "scientific_claim_authorized": False,
    }
