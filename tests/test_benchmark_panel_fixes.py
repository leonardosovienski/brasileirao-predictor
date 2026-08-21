"""Correções do painel canônico (auditoria 2026-08-21).

Cobre: IC95 presente na métrica primária, bootstrap de bloco móvel em vez de
iid, calibration slope ponderado por `n` do bin, e `--baseline` realmente
ligado (em vez de argumento morto).
"""

from __future__ import annotations

import pytest

from scripts import benchmark_predictor as bp

# ---------- delta_ci95 no formato de saída (Roadmap §6) ----------


def test_metric_record_carrega_delta_ci95_quando_fornecido() -> None:
    rec = bp._metric_record("rps", 0.21, baseline_value=0.23, n=100, is_primary=True, delta_ci95=(-0.03, -0.01))
    assert rec["delta_ci95"] == [-0.03, -0.01]
    assert rec["delta"] == pytest.approx(-0.02)


def test_delta_ci95_tem_o_sinal_do_campo_delta() -> None:
    """`delta` é modelo - baseline (negativo = modelo melhor). O IC precisa
    apontar para o mesmo lado, senão o relatório se contradiz."""
    modelo = [0.10] * 300
    baseline = [0.20] * 300
    ci = bp._delta_ci95(modelo, baseline)
    assert ci is not None
    assert ci[0] < 0 and ci[1] < 0, "modelo melhor deve dar IC do delta negativo"

    skill = bp._skill_score_ci(modelo, baseline)
    assert skill is not None
    assert skill[0] > 0, "o mesmo ganho, na orientação de skill score, é positivo"
    assert ci == pytest.approx((-skill[1], -skill[0]))


def test_delta_ci95_recusa_series_desalinhadas() -> None:
    assert bp._delta_ci95([0.1, 0.2], [0.1]) is None
    assert bp._delta_ci95([], []) is None


# ---------- bootstrap de bloco, não iid ----------


def test_bootstrap_usa_bloco_movel() -> None:
    """iid estreita o IC e superestima significância em série temporal. O
    painel é a régua de promoção: tem que ser o instrumento conservador."""
    assert bp.BLOCK_LENGTH > 1
    ci = bp._bootstrap_mean_ci([0.05] * 300)
    assert ci is not None and ci[0] <= ci[1]


def test_bootstrap_mean_ci_vazio_e_none() -> None:
    assert bp._bootstrap_mean_ci([]) is None


# ---------- calibration slope ponderado ----------


def _rows_ou(pairs: list[tuple[float, int]]) -> list[dict]:
    return [{"p_over": p, "actual_over": y} for p, y in pairs]


def test_slope_ignora_bin_minusculo_fora_da_curva() -> None:
    """Um bin com pouquíssimos jogos não pode ter a mesma alavancagem de um bin
    cheio: sem peso, a cauda governa o guardrail."""
    bem_calibrado = [(0.3, 0) for _ in range(200)] + [(0.7, 1) for _ in range(200)]
    ruido_de_cauda = [(0.95, 0), (0.05, 1)]
    com_ruido = bp._guardrails_ou25(_rows_ou(bem_calibrado + ruido_de_cauda))
    sem_ruido = bp._guardrails_ou25(_rows_ou(bem_calibrado))
    assert com_ruido["calibration_slope"] is not None
    assert sem_ruido["calibration_slope"] is not None
    # 2 jogos não podem mover o slope tanto quanto 400 movem.
    assert abs(com_ruido["calibration_slope"] - sem_ruido["calibration_slope"]) < 0.35


def test_guardrails_sem_observacao_devolvem_none() -> None:
    g = bp._guardrails_ou25([])
    assert g == {"ece": None, "calibration_slope": None, "resolution": None, "sharpness": None}


# ---------- --baseline deixou de ser argumento morto ----------


def test_baseline_desconhecido_falha_alto() -> None:
    """A docstring do painel promete NotImplementedError para baseline não
    plugado — devolver skill score contra baseline fantasma seria pior que
    falhar."""
    with pytest.raises(NotImplementedError, match="elo_baseline"):
        bp.run(model_tag="qualquer", start="", end="", baseline="market_no_vig")


def test_climatology_e_o_baseline_suportado() -> None:
    assert "climatology" in bp.SUPPORTED_BASELINES
