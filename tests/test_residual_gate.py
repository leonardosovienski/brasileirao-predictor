from brasileirao_predictor.research.residual_gate import evaluate_economic_gate


def test_gate_is_pending_below_sample_floor():
    result = evaluate_economic_gate([], dsr=1.0, minimum_sample=10)
    assert result["verdict"] == "PENDING_SAMPLE"
    assert result["capital_enabled"] is False


def test_gate_rejects_negative_economics_even_with_high_dsr():
    rows = [{"event_id": str(index), "pnl": -1.0 if index % 2 else 0.5, "clv": -0.01} for index in range(30)]
    result = evaluate_economic_gate(rows, dsr=0.99, minimum_sample=20, n_boot=200)
    assert result["verdict"] == "NO_GO"
    assert result["capital_enabled"] is False


def test_gate_can_only_return_candidate_not_enable_capital():
    rows = [{"event_id": str(index), "pnl": 0.2, "clv": 0.03} for index in range(30)]
    result = evaluate_economic_gate(rows, dsr=0.99, minimum_sample=20, n_boot=200)
    # Constant returns make PSR undefined, so this deliberately remains NO_GO.
    assert result["verdict"] == "NO_GO"
    assert result["capital_enabled"] is False
