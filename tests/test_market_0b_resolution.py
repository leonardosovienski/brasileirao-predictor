from __future__ import annotations

from src.research import market_0b_resolution as m


def _rows(probabilities, odds=(1.9, 1.9)):
    return [{"p_over": p, "p_btts": p, "market_odds_ou25": odds, "market_odds_btts": odds} for p in probabilities]


def test_odds_invalidas_nao_contam_como_cobertura() -> None:
    rows = _rows([0.4, 0.5, 0.6])
    rows[0]["market_odds_ou25"] = (1.0, 2.0)
    rows[1]["market_odds_ou25"] = (None, 2.0)
    assert m.market_summary(rows, "p_over", "market_odds_ou25", threshold_var=0.02)["odds_complete_n"] == 1


def test_probabilidade_quase_constante_falha_resolucao() -> None:
    result = m.evaluate(_rows([0.499, 0.500, 0.501] * 20))
    assert result["markets"]["ou25"]["structural_verdict"] == "NO_GO_LOW_MODEL_RESOLUTION"
    assert result["full_protocol_candidates"] == []


def test_histograma_range_e_threshold_ficam_no_relatorio() -> None:
    summary = m.market_summary(_rows([0.10, 0.20, 0.30]), "p_over", "market_odds_ou25", threshold_var=0.02)
    assert round(summary["probability_range"], 10) == 0.20
    assert sum(item["n"] for item in summary["histogram"]) == 3
    assert summary["threshold_var"] == 0.02


def test_um_mercado_sem_variancia_produz_no_go_global() -> None:
    rows = _rows([0.35, 0.45, 0.55, 0.65] * 20)
    for row in rows:
        row["p_btts"] = 0.5
    assert m.evaluate(rows)["verdict"] == "NO_GO_STRUCTURAL"


def test_variacao_e_cobertura_suficientes_liberam_protocolo_completo() -> None:
    result = m.evaluate(_rows([0.35, 0.45, 0.55, 0.65] * 20))
    assert result["verdict"] == "PROCEED_TO_FULL_0B"
    assert result["full_protocol_candidates"] == ["ou25", "btts"]


def test_resolucao_sem_odds_nao_e_confundida_com_no_go_estrutural() -> None:
    result = m.evaluate(_rows([0.35, 0.45, 0.55, 0.65] * 20, odds=(1.0, 1.0)))
    assert result["markets"]["ou25"]["resolution_pass"] is True
    assert result["markets"]["ou25"]["odds_coverage_pass"] is False
    assert result["full_protocol_candidates"] == []


def test_protocolo_completo_declara_os_dois_lados_e_dez_celulas() -> None:
    records = [
        {
            "date": f"2023-01-{i + 1:02d}",
            "model_p": 0.35 + i * 0.02,
            "market_p": 0.50,
            "odds": [2.0, 2.0],
            "actual": i % 2,
            "effective_elo_diff": float(i),
        }
        for i in range(12)
    ]
    result = m.full_market_protocol(records, power_reference=records, permutations=2, seed=1)
    assert result["declared_cells"] == 10
    assert set(result["selections"]) == {"side_a", "side_b"}
    assert all(item["permutation"]["n"] == 2 for item in result["selections"].values())


def test_evaluate_reports_lambda_total_distribution() -> None:
    rows = _rows([0.35, 0.45, 0.55])
    for row, value in zip(rows, (2.0, 2.5, 3.0)):
        row["lambda_total"] = value

    summary = m.evaluate(rows)["lambda_total"]

    assert summary["n"] == 3
    assert summary["mean"] == 2.5
    assert summary["min"] == 2.0
    assert summary["max"] == 3.0
    assert summary["range"] == 1.0
