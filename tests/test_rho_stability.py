from src.research.rho_stability import evaluate_rho


def test_rho_diagnostic_blocks_without_holdout_data() -> None:
    assert evaluate_rho([(0.0, 1, 0)] * 20)["status"] == "BLOCKED_DATA"


def test_rho_diagnostic_returns_finite_oos_metrics() -> None:
    history = [
        ((index % 7 - 3) * 40.0, (index * 3) % 4, (index * 5 + 1) % 3)
        for index in range(140)
    ]
    report = evaluate_rho(history, minimum_matches=100)
    assert report["status"] == "PASS_STABLE"
    assert set(report["metrics"]) == {
        "rps_delta",
        "rps_delta_ci95",
        "log_loss_delta",
        "log_loss_delta_ci95",
    }
    assert report["verdict"] in {"GO_CANDIDATE", "NO_GO"}
