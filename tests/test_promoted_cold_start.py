import pytest

from src.data.promotions import Promotion
from src.research.promoted_cold_start import (
    ColdStartMatch,
    PromotedEntry,
    build_entries,
    evaluate_empirical_prior,
    evaluate_first_matches,
    evaluate_goal_priors,
    leave_one_season_out_priors,
    protocol_status,
)


def _entry(season, team, rating):
    return PromotedEntry(season, team, 1, rating, f"source-{season}-{team}")


def test_prior_for_a_season_uses_only_strictly_earlier_seasons():
    entries = [_entry(2022, "a", 1400), _entry(2023, "b", 1420), _entry(2024, "c", 2000)]
    priors = leave_one_season_out_priors(entries)
    assert priors[2023] == 1400
    assert priors[2024] == 1410


def test_missing_metadata_blocks_without_changing_serving():
    assert protocol_status([])["status"] == "BLOCKED_MISSING_PROMOTION_METADATA"
    assert protocol_status([])["serving_changed"] is False


def test_duplicate_or_insufficient_history_fails_closed():
    duplicate = [_entry(2022, "a", 1400), _entry(2022, "a", 1410), _entry(2023, "b", 1420)]
    with pytest.raises(ValueError, match="at least|duplicate"):
        leave_one_season_out_priors(duplicate)


def test_build_entries_fails_closed_without_point_in_time_rating():
    promotion = Promotion(2024, 2023, 1, "vitoria", "Vitoria", "https://www.cbf.com.br/source")
    with pytest.raises(ValueError, match="missing point-in-time"):
        build_entries([promotion], {}, as_of_season=2024)


def test_empirical_prior_blocks_small_samples_and_never_changes_serving():
    entries = [_entry(2022, "a", 1400), _entry(2023, "b", 1420), _entry(2024, "c", 1410)]
    report = evaluate_empirical_prior(entries)
    assert report["status"] == "BLOCKED_DATA"
    assert report["serving_changed"] is False


def test_first_matches_cold_start_runs_oos_and_never_changes_serving():
    entries = [_entry(2022, "a", 1400), _entry(2023, "b", 1410), _entry(2024, "c", 1420), _entry(2025, "d", 1430)]
    matches = [
        ColdStartMatch(season, team, number, 1500.0, number % 2 == 0, number % 3, (number + 1) % 3)
        for season, team in ((2023, "b"), (2024, "c"), (2025, "d"))
        for number in range(1, 11)
    ]
    report = evaluate_first_matches(
        entries,
        matches,
        first_n=10,
        baseline_rating=1500.0,
        home_advantage=65.0,
        draw_rate=0.27,
        base_k=20.0,
        bootstrap_seed=13,
        bootstrap_iterations=200,
    )
    assert report["status"] in {"GO_CANDIDATE", "NO_GO"}
    assert report["n"] == 30
    assert report["serving_changed"] is False
    assert report["bootstrap"]["scheme"] == "season_cluster"


def test_goal_prior_arm_is_isolated_from_serving():
    matches = [ColdStartMatch(2024, "c", number, 1500, True, 1, 2) for number in range(1, 31)]
    report = evaluate_goal_priors(
        matches,
        {2024: (0.9, 1.1)},
        baseline_goals_for=1.3,
        baseline_goals_against=1.3,
        bootstrap_seed=42,
        bootstrap_iterations=100,
    )
    assert report["status"] in {"GO_CANDIDATE", "NO_GO"}
    assert report["serving_changed"] is False
    assert "goal_log_loss_delta_ci95" in report
