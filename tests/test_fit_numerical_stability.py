"""BR-F018: o ajuste do modelo de gols não pode depender do último bit da entrada.

O mesmo pedido real, com a mesma wheel e o mesmo snapshot, dava parâmetros e probabilidades
diferentes no Windows e no Linux: o L-BFGS-B com gradiente por diferenças finitas parava em
pontos diferentes conforme o ruído de ponto flutuante de cada plataforma. Estes testes usam só a
API pública e dados SINTÉTICOS com seed (nenhum dado real).

Tolerâncias declaradas ANTES de medir (predictor-qualification,
qualification/brasileirao/BR_F018_FIX_PLAN.json, commit 497715f):
  * mesma entrada, mesmo processo: parâmetros bit a bit;
  * pesos multiplicados por (1 + 2**-52): |Δ| <= 1e-6 em cada parâmetro devolvido e
    |Δ| <= 1e-9 em cada probabilidade e lambda da previsão.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from brasileirao_predictor.model import fit_goal_model, predict_match

PARAM_ATOL = 1e-6
PROB_ATOL = 1e-9
ULP = 1.0 + 2.0**-52
N_MATCHES = 1200
MATCHUPS = [(1500.0 + diff, 1500.0) for diff in (-300.0, -150.0, 0.0, 150.0, 300.0)]


def _history(seed: int, gamma_shape: float | None) -> list[tuple[float, int, int]]:
    """Histórico sintético (elo_diff, gols_mandante, gols_visitante) com seed.

    Sem ``gamma_shape`` os gols são Poisson: a dispersão alpha fica perto do limite de Poisson, a
    direção mais plana da verossimilhança e a que mais amplificava o ruído (BR-F018)."""
    rng = np.random.default_rng(seed)
    history = []
    for _ in range(N_MATCHES):
        diff = float(rng.normal(0.0, 250.0))
        lam_h = math.exp(0.15 + 0.6 * diff / 400.0)
        lam_a = math.exp(0.15 - 0.6 * diff / 400.0)
        if gamma_shape is not None:
            lam_h = float(rng.gamma(gamma_shape, lam_h / gamma_shape))
            lam_a = float(rng.gamma(gamma_shape, lam_a / gamma_shape))
        history.append((diff, int(rng.poisson(lam_h)), int(rng.poisson(lam_a))))
    return history


def _weights() -> list[float]:
    """Pesos de recência como os do serving (meia-vida de 730 dias, um jogo por dia)."""
    return [math.exp(-math.log(2.0) * (N_MATCHES - index) / 730.0) for index in range(N_MATCHES)]


def _delta_xg(seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    return [float(x) for x in rng.normal(0.0, 0.5, N_MATCHES)]


def _predictions(params) -> list[float]:
    values = []
    for elo_home, elo_away in MATCHUPS:
        r = predict_match(elo_home, elo_away, params, home_adv=100.0, max_goals=12)
        values += [r["p_win"], r["p_draw"], r["p_loss"], r["over"][2.5], r["lambda_a"], r["lambda_b"]]
    return values


CASES = [pytest.param(20260924, None, id="poisson"), pytest.param(20260925, 8.0, id="binomial-negativa")]


@pytest.mark.parametrize(("seed", "gamma_shape"), CASES)
def test_same_input_gives_bit_identical_parameters(seed: int, gamma_shape: float | None) -> None:
    history, weights = _history(seed, gamma_shape), _weights()
    assert fit_goal_model(history, sample_weights=weights) == fit_goal_model(history, sample_weights=weights)


@pytest.mark.parametrize(("seed", "gamma_shape"), CASES)
def test_last_bit_perturbation_stays_within_declared_tolerance(seed: int, gamma_shape: float | None) -> None:
    history, weights = _history(seed, gamma_shape), _weights()
    base = fit_goal_model(history, sample_weights=weights)
    perturbed = fit_goal_model(history, sample_weights=[w * ULP for w in weights])
    param_gap = max(abs(x - y) for x, y in zip(base, perturbed, strict=True))
    assert param_gap <= PARAM_ATOL, f"parâmetros mudaram {param_gap:.3e} com 1 ULP nos pesos"
    prob_gap = max(abs(x - y) for x, y in zip(_predictions(base), _predictions(perturbed), strict=True))
    assert prob_gap <= PROB_ATOL, f"probabilidades mudaram {prob_gap:.3e} com 1 ULP nos pesos"


def test_last_bit_perturbation_with_delta_xg_stays_within_declared_tolerance() -> None:
    history, weights, delta_xg = _history(20260926, None), _weights(), _delta_xg(20260927)
    base = fit_goal_model(history, delta_xg=delta_xg, sample_weights=weights)
    perturbed = fit_goal_model(history, delta_xg=delta_xg, sample_weights=[w * ULP for w in weights])
    assert len(base) == 5
    param_gap = max(abs(x - y) for x, y in zip(base, perturbed, strict=True))
    assert param_gap <= PARAM_ATOL, f"parâmetros mudaram {param_gap:.3e} com 1 ULP nos pesos"
