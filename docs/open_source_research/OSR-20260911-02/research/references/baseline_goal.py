import math
import numpy as np
from scipy.stats import nbinom

def _all_dc_factors_positive(lam, mu, rho):
    """Whether all four corrected cells are strictly positive."""
    return (1.0 - lam * mu * rho > 0.0) & (1.0 + lam * rho > 0.0) & (1.0 + mu * rho > 0.0) & (1.0 - rho > 0.0)


def _score_grid(lam_a, lam_b, alpha, rho, max_goals):
    """Grid de probabilidade P(gols_a=i, gols_b=j) — NB + correção Dixon-Coles
    nas quatro células de placar baixo. Fatorado de `predict_match` pra ser
    reaproveitado por `predict_remaining` com lambdas escalados."""
    values = (lam_a, lam_b, alpha, rho)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("lam_a, lam_b, alpha and rho must be finite")
    if lam_a <= 0 or lam_b <= 0 or alpha <= 0:
        raise ValueError("lam_a, lam_b and alpha must be > 0")
    if not isinstance(max_goals, int) or max_goals < 1:
        raise ValueError("max_goals must be an integer >= 1")
    if not bool(_all_dc_factors_positive(lam_a, lam_b, rho)):
        raise ValueError("rho produces a non-positive Dixon-Coles cell")

    k = np.arange(max_goals + 1)
    r = 1.0 / max(alpha, 1e-9)
    pa = nbinom.pmf(k, r, r / (r + lam_a))
    pb = nbinom.pmf(k, r, r / (r + lam_b))
    grid = np.outer(pa, pb)

    grid[0, 0] *= 1.0 - lam_a * lam_b * rho
    grid[0, 1] *= 1.0 + lam_a * rho
    grid[1, 0] *= 1.0 + lam_b * rho
    grid[1, 1] *= 1.0 - rho
    total = float(grid.sum())
    if not math.isfinite(total) or total <= 0.0 or np.any(grid < 0.0):
        raise ValueError("invalid score-grid mass")
    grid /= total
    return grid
