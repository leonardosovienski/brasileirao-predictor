"""BR-F018: o método novo otimiza a MESMA função objetivo, só com gradiente exato.

* o gradiente analítico bate com diferenças finitas centrais da negll (o menor erro entre três
  passos, porque a própria negll tem ruído de arredondamento na direção da dispersão: é esse ruído
  que tornava o gradiente numérico inútil e o ajuste instável);
* o ponto devolvido é a raiz do gradiente analítico nas coordenadas livres (KKT nos bounds);
* o ótimo novo nunca é pior, na mesma negll, que o do método antigo (L-BFGS-B com gradiente
  numérico a partir do mesmo x0 e dos mesmos bounds).
Dados sintéticos com seed; nenhum dado real.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.optimize import minimize

from brasileirao_predictor import model

N = 900
BOUNDS_4 = [(-3, 3), (-1, 4), (math.log(1e-4), math.log(3)), (None, None)]


def _arrays(seed: int, gamma_shape: float | None):
    rng = np.random.default_rng(seed)
    diffs = rng.normal(0.0, 250.0, N) / 400.0
    lam = np.exp(0.15 + 0.6 * diffs)
    mu = np.exp(0.15 - 0.6 * diffs)
    if gamma_shape is not None:
        lam = rng.gamma(gamma_shape, lam / gamma_shape)
        mu = rng.gamma(gamma_shape, mu / gamma_shape)
    hs = rng.poisson(lam).astype(float)
    as_ = rng.poisson(mu).astype(float)
    weights = np.exp(-math.log(2.0) * (N - np.arange(N)) / 730.0)
    dxg = rng.normal(0.0, 0.5, N)
    return diffs, hs, as_, weights, dxg


def _history(diffs, hs, as_):
    return [(float(d) * 400.0, int(h), int(a)) for d, h, a in zip(diffs, hs, as_, strict=True)]


@pytest.mark.parametrize("with_xg", [False, True])
def test_analytic_gradient_matches_central_differences(with_xg: bool) -> None:
    diffs, hs, as_, weights, dxg = _arrays(11, None)
    negll, gradient = model._goal_model_objective(diffs, hs, as_, weights, dxg if with_xg else np.zeros(N))
    rng = np.random.default_rng(12)
    checked = 0
    while checked < 12:
        theta = [
            rng.uniform(-0.3, 0.4),
            rng.uniform(0.0, 1.2),
            rng.uniform(math.log(1e-4), math.log(1.5)),
            rng.uniform(-1.5, 1.5),
        ]
        if with_xg:
            theta.append(rng.uniform(-1.0, 1.0))
        theta = np.array(theta)
        if negll(theta) >= 1e11:
            continue
        checked += 1
        analytic = gradient(theta)
        for j in range(theta.size):
            errors = []
            for step in (1e-3, 1e-4, 1e-5):
                h = step * max(1.0, abs(theta[j]))
                e = np.zeros_like(theta)
                e[j] = h
                numeric = (negll(theta + e) - negll(theta - e)) / (2.0 * h)
                errors.append(abs(numeric - analytic[j]))
            assert min(errors) <= 1e-5 * max(1.0, abs(analytic[j])), (j, theta, analytic[j], errors)


@pytest.mark.parametrize(("seed", "gamma_shape"), [(21, None), (22, 8.0)])
def test_solution_is_a_root_of_the_analytic_gradient(seed: int, gamma_shape: float | None) -> None:
    diffs, hs, as_, weights, dxg = _arrays(seed, gamma_shape)
    a, b, alpha, rho = model.fit_goal_model(_history(diffs, hs, as_), sample_weights=weights)
    theta = np.array([a, b, math.log(alpha), math.atanh(rho / model._RHO_SCALE)])
    _negll, gradient = model._goal_model_objective(diffs, hs, as_, weights, np.zeros(N))
    grad = gradient(theta)
    lower = np.array([-3.0, -1.0, math.log(1e-4), -np.inf])
    upper = np.array([3.0, 4.0, math.log(3.0), np.inf])
    free = model._projected_free(theta, grad, lower, upper)
    # escala: a soma dos pesos (~ centenas); 1e-7 dela é muito abaixo de qualquer parada por tolerância
    assert float(np.max(np.abs(grad[free]))) <= 1e-7 * float(weights.sum())


@pytest.mark.parametrize(("seed", "gamma_shape"), [(31, None), (32, 8.0), (33, 3.0)])
def test_new_optimum_is_never_worse_on_the_same_objective(seed: int, gamma_shape: float | None) -> None:
    diffs, hs, as_, weights, dxg = _arrays(seed, gamma_shape)
    negll, _gradient = model._goal_model_objective(diffs, hs, as_, weights, np.zeros(N))
    base = math.log(max(float(np.average(np.r_[hs, as_], weights=np.r_[weights, weights])), 1e-3))
    x0 = [base, 0.3, math.log(0.1), math.atanh(-0.03 / model._RHO_SCALE)]
    old = minimize(negll, x0, method="L-BFGS-B", bounds=BOUNDS_4)  # o método antigo, gradiente numérico
    a, b, alpha, rho = model.fit_goal_model(_history(diffs, hs, as_), sample_weights=weights)
    new_value = negll(np.array([a, b, math.log(alpha), math.atanh(rho / model._RHO_SCALE)]))
    assert new_value <= old.fun + 1e-9 * abs(old.fun)
