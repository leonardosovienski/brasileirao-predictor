"""Assíntota do motor: a Binomial Negativa com dispersão α→0 (e sem correção
Dixon-Coles, rho=0) tem que colapsar na Poisson clássica. É o teste que prova
que o embasamento estatístico está correto, não só calibrado."""

import numpy as np
import pytest
from scipy.stats import poisson

from brasileirao_predictor.model import _dc_normalizer_nb, predict_match, predict_remaining


def test_nb_colapsa_em_poisson_quando_alpha_zero():
    # rho=0 desliga a correção nos cantos; α→0 zera a sobredispersão.
    # O grid bivariado tem que ser o produto externo de duas Poissons puras.
    a, b = 0.2, 1.0
    params = (a, b, 1e-9, 0.0)
    elo_a, elo_b, adv, mg = 1900.0, 1750.0, 0.0, 12
    r = predict_match(elo_a, elo_b, params, adv, mg)

    diff = (elo_a - elo_b) / 400.0
    lam_a = np.exp(a + b * diff)
    lam_b = np.exp(a - b * diff)
    k = np.arange(mg + 1)
    expected = np.outer(poisson.pmf(k, lam_a), poisson.pmf(k, lam_b))
    expected /= expected.sum()

    np.testing.assert_allclose(r["grid"], expected, atol=1e-6)


def test_probabilidades_1x2_somam_um():
    r = predict_match(1850.0, 1850.0, (0.2, 1.0, 0.1, 0.05), 0.0, 12)
    assert abs(r["p_win"] + r["p_draw"] + r["p_loss"] - 1.0) < 1e-9


def test_nb_dixon_coles_expoe_normalizador_nao_trivial():
    assert _dc_normalizer_nb(1.3, 1.3, 1.0, 0.2) == pytest.approx(0.9795876944407718)


def test_rho_que_gera_celula_negativa_falha_em_vez_de_clipar():
    with pytest.raises(ValueError, match="non-positive Dixon-Coles"):
        predict_match(1500, 1500, (1.0, 0.5, 0.2, 0.4), max_goals=12)


@pytest.mark.parametrize(
    "params,max_goals",
    [((0.2, 0.7, 0.0, 0.0), 12), ((0.2, 0.7, 0.1, float("nan")), 12), ((0.2, 0.7, 0.1, 0.0), 0)],
)
def test_parametros_invalidos_falham_alto(params, max_goals):
    with pytest.raises(ValueError):
        predict_match(1500, 1500, params, max_goals=max_goals)


def test_draw_diagnostics_expose_all_discussed_hypotheses_without_decision_rule():
    r = predict_match(1500, 1500, (0.2, 0.7, 0.1, -0.03), home_adv=0, max_goals=8)
    d = r["draw_diagnostics"]

    assert d["p_draw_1x2"] == pytest.approx(r["p_draw"])
    assert sum(d["diagonal_score_probs"].values()) == pytest.approx(r["p_draw"])
    assert d["modal_score"] == [int(r["top_scores"][0][0][0]), int(r["top_scores"][0][0][1])]
    assert d["modal_score_is_draw"] is True
    assert d["p_modal_score"] == pytest.approx(r["top_scores"][0][1])
    assert d["draw_rank_1x2"] in {1, 2, 3}
    assert d["top_1x2_gap"] >= 0
    assert d["side_probability_gap"] == pytest.approx(abs(r["p_win"] - r["p_loss"]))
    assert d["draw_vs_best_side_gap"] == pytest.approx(r["p_draw"] - max(r["p_win"], r["p_loss"]))
    assert d["entropy_1x2_nats"] > 0
    assert 0 < d["diagonal_concentration"] <= 1
    assert d["categorical_policy"] == "ARGMAX_DIAGNOSTIC_ONLY"
    assert d["robust_choice"] is None


def test_mando_favorece_o_mandante():
    # mesmo Elo, com vantagem de mando → p_win > p_loss.
    r = predict_match(1800.0, 1800.0, (0.2, 1.0, 0.1, 0.05), home_adv=80.0)
    assert r["p_win"] > r["p_loss"]


def test_predict_remaining_fraction_1_bate_com_predict_match():
    # fraction=1.0 (jogo inteiro) tem que reproduzir o predict_match original
    # (mesmos lambdas, mesmo grid) — é o mesmo link function, só escalado.
    params = (0.2, 1.0, 0.1, 0.05)
    full = predict_match(1850.0, 1750.0, params, home_adv=60.0)
    rem = predict_remaining(1850.0, 1750.0, params, home_adv=60.0, fraction=1.0)
    assert abs(rem["lambda_a"] - full["lambda_a"]) < 1e-9
    assert abs(rem["lambda_b"] - full["lambda_b"]) < 1e-9
    np.testing.assert_allclose(rem["grid"], full["grid"], atol=1e-9)


def test_predict_remaining_fraction_meio_escala_lambda_pela_metade():
    params = (0.2, 1.0, 0.1, 0.05)
    full = predict_match(1850.0, 1750.0, params, home_adv=0.0)
    metade = predict_remaining(1850.0, 1750.0, params, home_adv=0.0, fraction=0.5)
    assert abs(metade["lambda_a"] - full["lambda_a"] / 2.0) < 1e-9
    assert abs(metade["lambda_b"] - full["lambda_b"] / 2.0) < 1e-9


def test_predict_remaining_grid_soma_um():
    r = predict_remaining(1850.0, 1750.0, (0.2, 1.0, 0.1, 0.05), fraction=0.5)
    assert abs(r["grid"].sum() - 1.0) < 1e-9


def test_predict_remaining_fraction_zero_is_exactly_no_more_goals():
    r = predict_remaining(1850.0, 1750.0, (0.2, 1.0, 0.1, 0.05), fraction=0.0)
    assert r["lambda_a"] == 0.0
    assert r["lambda_b"] == 0.0
    assert r["grid"][0, 0] == 1.0
    assert np.count_nonzero(r["grid"]) == 1


@pytest.mark.parametrize("fraction", [-0.1, 1.1, float("nan"), float("inf")])
def test_predict_remaining_rejeita_fracao_invalida(fraction):
    with pytest.raises(ValueError, match="fraction"):
        predict_remaining(1500, 1500, (0.2, 0.7, 0.1, 0.0), fraction=fraction)
