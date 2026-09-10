import pytest

from brasileirao_predictor.research.residual_gate import evaluate_economic_gate


def rows():
    return [{"event_id": str(i), "pnl": 0.1 if i % 2 else 0.2, "clv": 0.03} for i in range(20)]


def test_repeated_snapshots_cannot_satisfy_independent_sample_floor():
    sample = [{"event_id": "one", "pnl": 0.1 if i % 2 else 0.2, "clv": 0.03} for i in range(30)]
    result = evaluate_economic_gate(sample, dsr=1, minimum_sample=20, n_boot=20)
    assert result["verdict"] == "PENDING_SAMPLE"
    assert result["n_events"] == 1


def test_declared_dsr_cannot_promote_unregistered_experiment():
    result = evaluate_economic_gate(rows(), dsr=1, minimum_sample=10, n_boot=20)
    assert result["verdict"] == "PENDING_DESIGN"
    assert result["dsr_used_for_promotion"] is False


def test_psr_uses_event_returns_and_is_invariant_to_snapshot_repetition():
    sample = [{**row, "pnl": 0.2 if i % 2 else -0.15} for i, row in enumerate(rows())]
    once = evaluate_economic_gate(sample, dsr=1, minimum_sample=10, n_boot=20)
    twice = evaluate_economic_gate(sample * 10, dsr=1, minimum_sample=10, n_boot=20)
    assert once["psr"] == pytest.approx(twice["psr"])
    assert once["n_events"] == twice["n_events"] == 20
