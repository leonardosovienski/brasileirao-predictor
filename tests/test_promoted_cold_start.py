import pytest

from src.data.promotions import Promotion
from src.research.promoted_cold_start import (
    PromotedEntry,
    build_entries,
    evaluate_empirical_prior,
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
