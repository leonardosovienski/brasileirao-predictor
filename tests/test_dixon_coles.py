"""dixon_coles — base de correlação: tau só nas células magras, decaimento, grade própria."""

import math

import pytest

from src.dixon_coles import DixonColesMatrix, dc_tau, time_decay_weight

# ---------- dc_tau ----------


def test_tau_is_one_outside_thin_cells():
    for h, a in [(2, 0), (0, 2), (2, 2), (3, 1), (5, 4)]:
        assert dc_tau(h, a, 1.4, 1.1, -0.1) == 1.0


def test_tau_negative_rho_inflates_draws_deflates_one_zero():
    lam, mu, rho = 1.4, 1.1, -0.08
    assert dc_tau(0, 0, lam, mu, rho) > 1.0
    assert dc_tau(1, 1, lam, mu, rho) > 1.0
    assert dc_tau(1, 0, lam, mu, rho) < 1.0
    assert dc_tau(0, 1, lam, mu, rho) < 1.0


def test_tau_zero_rho_is_identity():
    for h, a in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        assert dc_tau(h, a, 1.4, 1.1, 0.0) == 1.0


def test_tau_out_of_range_rho_raises():
    with pytest.raises(ValueError):
        dc_tau(1, 1, 1.4, 1.1, 1.5)  # 1 - rho < 0


# ---------- time_decay_weight ----------


def test_decay_today_is_one_and_monotone():
    xi = math.log(2) / 120
    assert time_decay_weight(0, xi) == 1.0
    assert time_decay_weight(30, xi) > time_decay_weight(240, xi)


def test_decay_halflife():
    xi = math.log(2) / 120
    assert time_decay_weight(120, xi) == pytest.approx(0.5)


def test_decay_zero_xi_is_flat():
    assert time_decay_weight(500, 0.0) == 1.0


def test_decay_rejects_future_match_and_negative_xi():
    with pytest.raises(ValueError):
        time_decay_weight(-1, 0.01)
    with pytest.raises(ValueError):
        time_decay_weight(10, -0.01)


# ---------- DixonColesMatrix ----------


def test_grid_sums_to_one():
    dc = DixonColesMatrix(lam=1.4, mu=1.1, rho=-0.05)
    assert sum(sum(row) for row in dc.grid()) == pytest.approx(1.0)


def test_outcome_probs_sum_to_one_and_favor_home():
    probs = DixonColesMatrix(lam=1.8, mu=0.9, rho=-0.05).outcome_probs()
    assert sum(probs.values()) == pytest.approx(1.0)
    assert probs["home"] > probs["away"]


def test_negative_rho_raises_draw_prob_vs_independent():
    ind = DixonColesMatrix(lam=1.4, mu=1.1, rho=0.0).outcome_probs()
    dc = DixonColesMatrix(lam=1.4, mu=1.1, rho=-0.08).outcome_probs()
    assert dc["draw"] > ind["draw"]


def test_rho_bounds_enforced_at_construction():
    lo, hi = DixonColesMatrix.valid_rho_bounds(1.4, 1.1)
    assert lo < 0 < hi
    with pytest.raises(ValueError):
        DixonColesMatrix(lam=1.4, mu=1.1, rho=hi + 0.1)
    with pytest.raises(ValueError):
        DixonColesMatrix(lam=1.4, mu=1.1, rho=lo - 0.1)


def test_score_prob_matches_grid_and_validates_range():
    dc = DixonColesMatrix(lam=1.4, mu=1.1, rho=-0.05, max_goals=6)
    assert dc.score_prob(1, 1) == dc.grid()[1][1]
    with pytest.raises(ValueError):
        dc.score_prob(7, 0)


def test_invalid_means_raise():
    with pytest.raises(ValueError):
        DixonColesMatrix(lam=0.0, mu=1.0)
