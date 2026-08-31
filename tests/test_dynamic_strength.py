import math

import pytest

from brasileirao_predictor.dynamic_strength import corrections, fit


def test_fit_rejects_invalid_alphas():
    with pytest.raises(ValueError, match="alphas"):
        fit([], (0.0, 0.3), [], alpha_short=0.1, alpha_long=0.2)


def test_balanced_observations_keep_corrections_near_zero():
    states = fit(
        [(0.0, 1, 1)] * 20,
        (0.0, 0.3),
        [("a", "b")] * 20,
        alpha_short=0.3,
        alpha_long=0.05,
    )
    home, away = corrections(states, "a", "b")
    assert home == pytest.approx(0.0)
    assert away == pytest.approx(0.0)


def test_attack_and_defence_are_directional_and_unseen_team_is_neutral():
    states = fit(
        [(0.0, 4, 0)] * 12,
        (0.0, 0.3),
        [("forte", "fraco")] * 12,
        alpha_short=0.3,
        alpha_long=0.05,
    )
    home, away = corrections(states, "forte", "fraco")
    assert home > math.log(2)
    assert away < 0
    assert corrections(states, "novo", "outro") == (0.0, 0.0)
