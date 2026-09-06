from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from brasileirao_predictor.research.prospective_validation import (
    CohortPolicy,
    PaperPick,
    PaperSettlement,
    evaluate_cohort,
    required_sample_size,
)
from brasileirao_predictor.research.prospective_validation.ledger import append_pick, append_settlement

KICKOFF = datetime(2026, 9, 1, 22, tzinfo=UTC)


def pick(index: int = 1, **changes) -> PaperPick:
    row = {
        "pick_id": f"pick-{index}",
        "cohort_id": "market04-prospective",
        "event_id": str(index),
        "market": "ou25",
        "selection": "over",
        "model_probability": 0.55,
        "predicted_at": KICKOFF - timedelta(hours=2),
        "kickoff_at": KICKOFF,
        "odds_captured_at": KICKOFF - timedelta(hours=2, minutes=5),
        "captured_odds": 2.0,
        "bookmaker": "named-book",
    }
    row.update(changes)
    return PaperPick.model_validate(row)


def settlement(index: int = 1, won: bool = True, **changes) -> PaperSettlement:
    row = {
        "pick_id": f"pick-{index}",
        "settled_at": KICKOFF + timedelta(hours=2),
        "closing_odds": 1.9,
        "closing_captured_at": KICKOFF - timedelta(minutes=1),
        "won": won,
        "result_source": "official",
    }
    row.update(changes)
    return PaperSettlement.model_validate(row)


def test_pick_exige_stake_flat_e_relogios_pre_kickoff() -> None:
    assert pick().stake_units == 1.0
    with pytest.raises(ValidationError):
        pick(stake_units=0.5)
    with pytest.raises(ValidationError, match="before kickoff"):
        pick(predicted_at=KICKOFF)


def test_closing_line_pos_kickoff_e_rejeitada() -> None:
    with pytest.raises(ValueError, match="strictly before kickoff"):
        settlement(closing_captured_at=KICKOFF).assert_matches(pick())


def test_ledger_e_append_only_e_recusa_duplicatas(tmp_path) -> None:
    path = tmp_path / "paper.jsonl"
    item, result = pick(), settlement()
    append_pick(path, item)
    append_settlement(path, result, item)
    with pytest.raises(ValueError, match="duplicate"):
        append_pick(path, item)
    with pytest.raises(ValueError, match="duplicate"):
        append_settlement(path, result, item)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def _dsr_stub(valor: float):
    """Duble do DSR que respeita o contrato inteiro do core 3.2.0.

    Um duble que devolve só {"dsr": x} esconde exatamente o que o achado 2 da
    auditoria adversarial de 2026-09-05 expôs: um DSR sem desconto aplicado é
    indistinguível de um descontado. O duble declara desconto aplicado para que
    o teste exercite o caminho normal, e não o de degeneração.
    """
    return lambda *_args, **_kwargs: {
        "dsr": valor,
        "sr0": 0.5,
        "n_trials": 6,
        "n_sharpes": 4,
        "sr0_estimable": True,
        "deflation_applied": True,
        "sharpe_coverage": 4 / 6,
    }


def test_metricas_e_gate_so_tem_duas_saidas(monkeypatch) -> None:
    import brasileirao_predictor.research.prospective_validation.metrics as metrics

    rows = [pick(i) for i in range(1, 11)]
    results = [settlement(i, won=i <= 6) for i in range(1, 11)]
    policy = CohortPolicy(min_matured=10, declared_trials=5, bootstrap_iterations=100)
    monkeypatch.setattr(metrics.registry_module, "deflated_sharpe_ratio", _dsr_stub(0.96))
    report = evaluate_cohort(rows, results, policy)
    assert report["capital_gate"] == "CAPITAL_GATE: ELIGIBLE_FOR_REVIEW"
    assert report["capital_decision_authority"] == "HUMAN_REVIEW_OUTSIDE_CODE"
    assert report["coverage"] == 1.0
    assert report["roi_bootstrap_ci95"] is not None
    assert report["calibration"]["n"] == 10


def test_dsr_abaixo_do_gate_mantem_capital_locked(monkeypatch) -> None:
    import brasileirao_predictor.research.prospective_validation.metrics as metrics

    monkeypatch.setattr(metrics.registry_module, "deflated_sharpe_ratio", _dsr_stub(0.949))
    report = evaluate_cohort(
        [pick(1), pick(2)],
        [settlement(1), settlement(2, won=False)],
        CohortPolicy(min_matured=2, declared_trials=1, bootstrap_iterations=100),
    )
    assert report["capital_gate"] == "CAPITAL_GATE: LOCKED"


def test_power_analysis_depende_da_odd_media() -> None:
    assert required_sample_size(3.0) > required_sample_size(1.9)
    with pytest.raises(ValueError):
        required_sample_size(1.01)


def test_gate_de_capital_trava_quando_o_desconto_nao_e_estimavel() -> None:
    """Achado 2 da auditoria adversarial de 2026-09-05, virado teste.

    Com menos de dois sharpes finitos no denominador o SR0 não é estimável e o
    Deflated Sharpe degenera em PSR puro — um número alto que parece descontado
    e não é. Antes do core 3.2.0 isso passava em silêncio e podia DESTRAVAR o
    gate de capital. Agora `strict=True` levanta, e este caminho TRAVA.

    `historical_trial_sharpes` vazio com `declared_trials=5` é exatamente o
    formato do denominador em produção quando nenhuma trial histórica publicou
    sharpe: cinco `None` e nada mais.
    """
    policy = CohortPolicy(
        min_matured=2,
        declared_trials=5,
        historical_trial_sharpes=(),
        bootstrap_iterations=100,
    )
    report = evaluate_cohort([pick(1), pick(2)], [settlement(1), settlement(2, won=False)], policy)

    assert report["capital_gate"] == "CAPITAL_GATE: LOCKED"
    assert report["dsr"] is None
    assert report["dsr_sr0_estimable"] is False
    assert report["dsr_deflation_applied"] is False
    # A razão é registrada, não engolida: um None sem motivo é indistinguível de
    # "ainda não calculado".
    assert report["dsr_not_estimable_reason"]


def test_o_desconto_aplicado_aparece_no_relatorio() -> None:
    """O contrário do teste acima: com sharpes históricos suficientes o desconto
    é estimável, e o relatório afirma isso explicitamente em vez de deixar o
    leitor supor a partir do valor do DSR."""
    policy = CohortPolicy(
        min_matured=2,
        declared_trials=5,
        historical_trial_sharpes=(0.1, 0.4, -0.2),
        bootstrap_iterations=100,
    )
    report = evaluate_cohort([pick(1), pick(2)], [settlement(1), settlement(2, won=False)], policy)

    assert report["dsr_sr0_estimable"] is True
    assert report["dsr_deflation_applied"] is True
    assert report["dsr_not_estimable_reason"] is None
    assert report["dsr_sharpe_coverage"] == 3 / 8
