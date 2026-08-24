from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.research.prospective_validation import (
    CohortPolicy,
    PaperPick,
    PaperSettlement,
    evaluate_cohort,
    required_sample_size,
)
from src.research.prospective_validation.ledger import append_pick, append_settlement

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


def test_metricas_e_gate_so_tem_duas_saidas(monkeypatch) -> None:
    import src.research.prospective_validation.metrics as metrics

    rows = [pick(i) for i in range(1, 11)]
    results = [settlement(i, won=i <= 6) for i in range(1, 11)]
    policy = CohortPolicy(min_matured=10, declared_trials=5, bootstrap_iterations=100)
    monkeypatch.setattr(metrics.registry_module, "deflated_sharpe_ratio", lambda *_: {"dsr": 0.96})
    report = evaluate_cohort(rows, results, policy)
    assert report["capital_gate"] == "CAPITAL_GATE: ELIGIBLE_FOR_REVIEW"
    assert report["capital_decision_authority"] == "HUMAN_REVIEW_OUTSIDE_CODE"
    assert report["coverage"] == 1.0
    assert report["roi_bootstrap_ci95"] is not None
    assert report["calibration"]["n"] == 10


def test_dsr_abaixo_do_gate_mantem_capital_locked(monkeypatch) -> None:
    import src.research.prospective_validation.metrics as metrics

    monkeypatch.setattr(metrics.registry_module, "deflated_sharpe_ratio", lambda *_: {"dsr": 0.949})
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
