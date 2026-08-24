from __future__ import annotations

import pytest

from src.research import market_edge_ordering as m


def _record(date: str, outcome: int, *, elo: float = 20.0):
    return {
        "date": date,
        "event_key": f"{date}|A|B",
        "model": [0.25, 0.35, 0.40],
        "market": [0.30, 0.30, 0.40],
        "odds": [3.2, 3.3, 2.4],
        "outcome": outcome,
        "effective_elo_diff": elo,
    }


def test_grade_declara_sessenta_tentativas() -> None:
    assert m.DECLARED_FAMILY_TRIALS == 60


def test_devig_rejeita_placeholder_e_preserva_ordem_away_draw_home() -> None:
    assert m.devig_1x2((2.0, 1.0, 4.0)) is None
    probabilities = m.devig_1x2((2.0, 3.5, 4.0))
    assert probabilities is not None
    assert sum(probabilities) == pytest.approx(1.0)
    assert probabilities[2] > probabilities[0]


def test_bins_tem_fronteiras_deterministicas() -> None:
    assert m.divergence_bin(-0.05) == "-5_0pp"
    assert m.divergence_bin(0.0) == "0_5pp"
    assert m.divergence_bin(0.10) == "ge_10pp"
    assert m.odds_bin(2.0) == "2_3"
    assert m.odds_bin(5.0) == "ge_5"


def test_permutacao_preserva_resultados_dentro_de_cada_estrato() -> None:
    records = [
        _record("2024-01-01", 0, elo=20),
        _record("2024-01-02", 1, elo=25),
        _record("2024-02-01", 2, elo=150),
        _record("2024-02-02", 1, elo=170),
    ]
    permuted = m.permute_outcomes(records, 7)
    assert [row["date"] for row in permuted] == [row["date"] for row in records]
    assert sorted(row["outcome"] for row in permuted[:2]) == [0, 1]
    assert sorted(row["outcome"] for row in permuted[2:]) == [1, 2]


def test_permutacao_nao_altera_previsoes_odds_ou_elo() -> None:
    records = [_record("2024-01-01", 0), _record("2024-01-02", 1)]
    permuted = m.permute_outcomes(records, 11)
    for original, changed in zip(records, permuted):
        assert changed["model"] == original["model"]
        assert changed["market"] == original["market"]
        assert changed["odds"] == original["odds"]
        assert changed["effective_elo_diff"] == original["effective_elo_diff"]


def test_power_cresce_com_variancia_e_recusa_amostra_inutil() -> None:
    assert m.required_n_for_roi([]) is None
    low = m.required_n_for_roi([-0.1, 0.1] * 20)
    high = m.required_n_for_roi([-1.0, 1.0] * 20)
    assert low is not None and high is not None and high > low


def test_celula_pequena_serializa_psr_e_dsr_indefinidos_como_none() -> None:
    cell = m.cells([_record("2024-01-01", 0)], [None])[0]
    assert cell["psr"] is None
    assert cell["dsr"]["dsr"] is None


def test_validacao_pode_usar_referencia_de_poder_do_desenvolvimento() -> None:
    development = [_record(f"2023-01-{i + 1:02d}", i % 3) for i in range(20)]
    validation = [_record(f"2024-01-{i + 1:02d}", 1) for i in range(10)]
    report = m.evaluate(
        validation,
        requested_n=10,
        historical_trial_sharpes=[],
        permutations=2,
        seed=1,
        power_reference=development,
    )
    assert report["draw_power_requirements_from_development"] == m.draw_power_requirements(development)


def test_draw_ordering_exige_tres_faixas_e_monotonicidade() -> None:
    rows = []
    for divergence, outcomes in ((-0.06, [0, 0]), (0.02, [1, 0]), (0.12, [1, 1])):
        for i, outcome in enumerate(outcomes):
            market_draw = 0.30
            model_draw = market_draw + divergence
            rows.append(
                {
                    "date": f"2024-01-{len(rows) + 1:02d}",
                    "event_key": str(len(rows)),
                    "model": [(1 - model_draw) / 2, model_draw, (1 - model_draw) / 2],
                    "market": [0.35, market_draw, 0.35],
                    "odds": [3.0, 3.0, 3.0],
                    "outcome": outcome,
                    "effective_elo_diff": float(i),
                }
            )
    assert m.draw_ordering(rows)["monotonic_roi"] is True


def test_paired_records_nao_aceita_linha_sem_elo_pit() -> None:
    row = {
        "date": "2024-01-01",
        "home": "A",
        "away": "B",
        "p_loss": 0.2,
        "p_draw": 0.3,
        "p_win": 0.5,
        "market_odds_1x2": (2.0, 3.5, 4.0),
        "actual_1x2": 2,
        "effective_elo_diff": None,
    }
    assert m.paired_records([row], "2024-01-01", "2024-12-31") == []
