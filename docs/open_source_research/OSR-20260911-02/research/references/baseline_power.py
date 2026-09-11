import math
from numbers import Real
import numpy as np
from scipy.optimize import brentq

def _finite(value: object) -> bool:
    try:
        return not isinstance(value, bool) and isinstance(value, Real) and math.isfinite(value)
    except (OverflowError, TypeError):
        return False


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
