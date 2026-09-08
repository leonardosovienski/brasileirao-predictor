"""Describe reported xG quality without imputing values or certifying provenance."""

import math


def is_numeric_xg(value: object) -> bool:
    """A provider zero is numeric; it is not by itself evidence of missingness."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def classify_xg_pair(home: object, away: object) -> str:
    """Classify the supplied pair, independently of the match outcome.

    NUMERIC_PAIR means finite nonnegative values, not authenticated statistics.
    ZERO_PAIR_UNATTESTED is ambiguous: consult source evidence before deciding
    whether to use it. This function never replaces zero with missing or goals.
    """
    if home is None and away is None:
        return "MISSING_PAIR"
    if home is None or away is None:
        return "PARTIAL_PAIR"
    if not is_numeric_xg(home) or not is_numeric_xg(away):
        return "INVALID_PAIR"
    if home == 0 and away == 0:
        return "ZERO_PAIR_UNATTESTED"
    return "NUMERIC_PAIR"
