from src.research.rho_stability import evaluate_rho


def test_rho_diagnostic_blocks_without_holdout_data() -> None:
    assert evaluate_rho([(0.0, 1, 0)] * 20)["status"] == "BLOCKED_DATA"


def test_rho_diagnostic_returns_finite_oos_metrics() -> None:
    history = [((index % 7 - 3) * 40.0, (index * 3) % 4, (index * 5 + 1) % 3) for index in range(140)]
    groups = [f"round-{index // 10}" for index in range(len(history))]
    report = evaluate_rho(history, group_keys=groups, minimum_matches=100)
    assert report["status"] == "PASS_STABLE"
    assert set(report["metrics"]) == {
        "rps_delta",
        "rps_delta_ci95",
        "log_loss_delta",
        "log_loss_delta_ci95",
    }
    assert report["verdict"] in {"GO_CANDIDATE", "NO_GO"}
    assert report["bootstrap_unit"] == "consecutive_kickoff_group"


def test_rho_rejects_misaligned_temporal_groups() -> None:
    import pytest

    with pytest.raises(ValueError, match="align"):
        evaluate_rho([(0.0, 1, 0)] * 100, group_keys=["one"])
