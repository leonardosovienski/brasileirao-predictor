from typing import List,Optional
import numpy as np
from scipy import optimize
from pbmodels import ImpliedMethod,ImpliedProbabilities

def _power(
    odds: List[float],
    market_names: Optional[List[str]] = None,
) -> ImpliedProbabilities:
    """
    Calculate implied probabilities using the power method.

    The power method computes the implied probabilities by solving for the
    power coefficient that normalizes the inverse of the odds to sum to 1.0.

    Parameters
    ----------
    odds : List[float]
        List of decimal odds for each outcome
    market_names : List[str], optional
        Names for each market outcome

    Returns
    -------
    ImpliedProbabilities
        Object containing the calculated probabilities, method metadata,
        and the power coefficient 'k' in method_params
    """
    odds_arr = np.array(odds, dtype=np.float64)
    inv_odds = 1.0 / odds_arr
    margin = float(np.sum(inv_odds) - 1)

    def _power_func(k: float, inv_odds: np.ndarray) -> np.ndarray:
        implied = inv_odds**k
        return implied

    def _power_error(k: float, inv_odds: np.ndarray) -> float:
        implied = _power_func(k, inv_odds)
        return float(1 - np.sum(implied))

    k = float(optimize.ridder(_power_error, 0, 100, args=(inv_odds,)))
    normalized = _power_func(k, inv_odds).tolist()

    return ImpliedProbabilities(
        probabilities=normalized,
        method=ImpliedMethod.POWER,
        margin=margin,
        market_names=market_names,
        method_params={"k": k},
    )


def _shin(
    odds: List[float],
    market_names: Optional[List[str]] = None,
) -> ImpliedProbabilities:
    """
    Calculate implied probabilities using Shin's method (1992, 1993).

    Shin's method models the bookmaker's overround as being proportional to
    the sum of the square roots of the implied probabilities.

    Parameters
    ----------
    odds : List[float]
        List of decimal odds for each outcome
    market_names : List[str], optional
        Names for each market outcome

    Returns
    -------
    ImpliedProbabilities
        Object containing the calculated probabilities, method metadata,
        and the Shin 'z' parameter in method_params
    """
    odds_arr = np.array(odds, dtype=np.float64)
    inv_odds = 1.0 / odds_arr
    margin = float(np.sum(inv_odds) - 1)

    def _shin_func(z: float, inv_odds: np.ndarray) -> np.ndarray:
        implied = (
            (z**2 + 4 * (1 - z) * inv_odds**2 / np.sum(inv_odds)) ** 0.5 - z
        ) / (2 - 2 * z)
        return implied

    def _shin_error(z: float, inv_odds: np.ndarray) -> float:
        implied = _shin_func(z, inv_odds)
        return float(1 - np.sum(implied))

    z = float(optimize.ridder(_shin_error, 0, 100, args=(inv_odds,)))
    normalized = _shin_func(z, inv_odds).tolist()

    return ImpliedProbabilities(
        probabilities=normalized,
        method=ImpliedMethod.SHIN,
        margin=margin,
        market_names=market_names,
        method_params={"z": z},
    )
