"""Synthetic chronology checks for an unvalidated, independent research candidate."""

import math
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta

import pytest

from brasileirao_predictor.research.price_strength.dynamic_xg import (
    DynamicXGConfig,
    Fixture,
    XGObservation,
    fit_calibration,
    forecast,
)

BASE = datetime(2035, 1, 1, 12, tzinfo=UTC)
CONFIG = DynamicXGConfig(window_matches=3, min_team_matches=2, min_calibration_matches=2)


def observation(day: int, **updates) -> XGObservation:
    kickoff = BASE + timedelta(days=day)
    values = {
        "match_id": f"synthetic-{day}",
        "home_team": "Synthetic Home",
        "away_team": "Synthetic Away",
        "kickoff": kickoff,
        "completed_at": kickoff + timedelta(hours=2),
        "available_at": kickoff + timedelta(hours=3),
        "home_xg": 1.8,
        "away_xg": 0.9,
        "home_goals": 2,
        "away_goals": 1,
    }
    values.update(updates)
    return XGObservation(**values)


HISTORY = [observation(day) for day in (0, 7, 14)]
FIXTURE = Fixture("future-synthetic", "Synthetic Home", "Synthetic Away", BASE + timedelta(days=40))
DECISION = FIXTURE.kickoff - timedelta(hours=1)


def predict(history=HISTORY, **kwargs):
    return forecast(history, FIXTURE, DECISION, CONFIG, **kwargs)


def calibration(history=None):
    if history is None:
        history = [*HISTORY, observation(21), observation(28)]
    return fit_calibration(history, BASE + timedelta(days=20), BASE + timedelta(days=30), CONFIG)


def test_probabilities_are_normalized_and_consistent_with_poisson_rates() -> None:
    prediction = predict()
    assert prediction.eligible
    assert prediction.lambda_home > prediction.lambda_away > 0
    for market in prediction.probabilities.values():
        assert math.fsum(market.values()) == pytest.approx(1)
        assert all(0 <= value <= 1 for value in market.values())
    total = prediction.lambda_home + prediction.lambda_away
    assert prediction.probabilities["ou25"]["under"] == pytest.approx(math.exp(-total) * (1 + total + total**2 / 2))
    assert prediction.probabilities["btts"]["yes"] == pytest.approx(
        (1 - math.exp(-prediction.lambda_home)) * (1 - math.exp(-prediction.lambda_away))
    )


def test_future_results_and_late_statistics_cannot_change_forecast() -> None:
    future = observation(50, home_xg=99, away_xg=80, home_goals=60, away_goals=40)
    late = observation(20, available_at=DECISION + timedelta(seconds=1), home_xg=50, away_xg=50)
    assert predict([*HISTORY, future, late]) == predict()


def test_statistics_at_the_decision_boundary_are_not_available() -> None:
    at_boundary = observation(21, available_at=DECISION, home_xg=10)
    assert predict([*HISTORY, at_boundary]) == predict()
    before_boundary = replace(at_boundary, available_at=DECISION - timedelta(microseconds=1))
    assert predict([*HISTORY, before_boundary]).lambda_home > predict().lambda_home


def test_own_match_id_never_enters_history_even_with_incorrect_external_fixture_identity() -> None:
    own = observation(30, match_id=FIXTURE.match_id, home_xg=40, home_goals=25)
    assert predict([*HISTORY, own]) == predict()


def test_history_is_order_invariant_and_duplicate_delivery_is_counted_once() -> None:
    assert predict(list(reversed(HISTORY)) + HISTORY) == predict()


def test_latest_available_revision_is_used_without_looking_at_future_revision() -> None:
    original = HISTORY[-1]
    future_revision = replace(original, home_xg=90, available_at=DECISION + timedelta(seconds=1))
    assert predict([*HISTORY, future_revision]) == predict()
    revision = replace(original, home_xg=4, available_at=DECISION - timedelta(seconds=1))
    prediction = predict([revision, *HISTORY])
    assert prediction.lambda_home > predict().lambda_home
    assert prediction.n_home == prediction.n_away == 3


def test_conflicting_visible_revision_fails_closed() -> None:
    with pytest.raises(ValueError, match="conflicting statistics"):
        predict([*HISTORY, replace(HISTORY[-1], home_xg=5)])


def test_conflicting_visible_match_identity_fails_closed() -> None:
    with pytest.raises(ValueError, match="conflicting match identity"):
        predict([*HISTORY, replace(HISTORY[-1], home_team="Other Team")])


def test_window_selects_recent_kickoffs_not_recent_delivery_dates() -> None:
    recent_history = [*HISTORY, observation(21)]
    late_old = replace(HISTORY[0], home_xg=50, available_at=DECISION - timedelta(seconds=1))
    assert predict([*recent_history, late_old]) == predict(recent_history)
    assert predict(recent_history).history_match_ids == ("synthetic-14", "synthetic-21", "synthetic-7")


def test_cold_start_does_not_promote_prior_probabilities_into_an_eligible_forecast() -> None:
    result = predict(HISTORY[:1])
    assert not result.eligible
    assert result.reason == "INSUFFICIENT_HISTORY"
    assert result.probabilities == {}
    assert result.lambda_home is None


def test_venue_specific_history_is_required_for_both_teams() -> None:
    wrong_venue = [replace(item, home_team=item.away_team, away_team=item.home_team) for item in HISTORY]
    result = predict(wrong_venue)
    assert not result.eligible
    assert result.n_home == result.n_away == 0


def test_more_opponent_xg_conceded_increases_home_scoring_probability() -> None:
    home_history = [replace(item, away_team="Other Away") for item in HISTORY]
    away_history = [observation(day, home_team="Other Home") for day in (1, 8, 15)]
    regular = predict([*home_history, *away_history])
    weaker_defense = predict([*home_history, *(replace(item, home_xg=4) for item in away_history)])
    assert weaker_defense.lambda_home > regular.lambda_home
    assert weaker_defense.probabilities["1x2"]["home"] > regular.probabilities["1x2"]["home"]


def test_raw_forecast_uses_xg_not_realized_goals() -> None:
    assert predict([replace(item, home_goals=30, away_goals=25) for item in HISTORY]) == predict()


def test_calibration_uses_only_prior_forecasts_and_observed_labels() -> None:
    labels = [observation(21), observation(28)]
    fitted = calibration([*HISTORY, *labels])
    earlier_predictions = [
        forecast(
            [*HISTORY, *labels],
            Fixture(item.match_id, item.home_team, item.away_team, item.kickoff),
            item.kickoff - timedelta(hours=1),
            CONFIG,
        )
        for item in labels
    ]
    assert fitted.eligible and fitted.n_matches == 2
    assert fitted.home_scale == pytest.approx(
        (4 + CONFIG.calibration_prior_exposure)
        / (sum(item.lambda_home for item in earlier_predictions) + CONFIG.calibration_prior_exposure)
    )
    assert fitted.used_match_ids == ("synthetic-0", "synthetic-14", "synthetic-21", "synthetic-28", "synthetic-7")


def test_calibration_is_invariant_to_future_results_and_late_labels() -> None:
    history = [*HISTORY, observation(21), observation(28)]
    future = observation(35, home_xg=90, home_goals=50)
    late = observation(25, available_at=BASE + timedelta(days=31), home_xg=30, home_goals=20)
    assert calibration([future, *history, late]) == calibration(history)


def test_last_calibration_matches_own_xg_cannot_change_its_prediction_or_fitted_scales() -> None:
    history = [*HISTORY, observation(21), observation(28)]
    changed_own_xg = [*history[:-1], replace(history[-1], home_xg=90, away_xg=80)]
    assert calibration(changed_own_xg) == calibration(history)


def test_result_at_calibration_end_is_excluded() -> None:
    at_boundary = observation(28, available_at=BASE + timedelta(days=30))
    result = calibration([*HISTORY, observation(21), at_boundary])
    assert not result.eligible
    assert result.n_matches == 1


def test_calibration_has_explicit_cold_start_and_optional_outcomes() -> None:
    no_labels = [
        replace(item, home_goals=None, away_goals=None) for item in [*HISTORY, observation(21), observation(28)]
    ]
    fitted = calibration(no_labels)
    assert not fitted.eligible
    assert fitted.n_matches == 0
    assert fitted.reason == "INSUFFICIENT_CALIBRATION"
    prediction = predict(calibration=fitted)
    assert not prediction.eligible
    assert prediction.reason == "INSUFFICIENT_CALIBRATION"
    assert prediction.probabilities == {}


def test_calibration_is_applied_coherently_and_records_input_lineage() -> None:
    fitted = calibration()
    prediction = predict(calibration=fitted)
    assert prediction.eligible and prediction.calibration_applied
    assert prediction.lambda_home == pytest.approx(predict().lambda_home * fitted.home_scale)
    assert prediction.calibration_n == 2
    assert prediction.calibration_match_ids == fitted.used_match_ids
    assert prediction.latest_available_at == fitted.latest_available_at
    assert asdict(prediction)["status"] == "UNVALIDATED_NEW_LINEAGE"


def test_calibration_from_the_decision_boundary_or_future_is_rejected() -> None:
    fitted = replace(calibration(), calibration_end=DECISION)
    with pytest.raises(ValueError, match="strictly before"):
        predict(calibration=fitted)


def test_calibration_cannot_be_applied_to_its_own_target_or_different_candidate() -> None:
    fitted = calibration()
    with pytest.raises(ValueError, match="own calibration"):
        forecast(HISTORY, replace(FIXTURE, match_id="synthetic-28"), DECISION, CONFIG, fitted)
    with pytest.raises(ValueError, match="different candidate"):
        forecast(HISTORY, FIXTURE, DECISION, replace(CONFIG, half_life_days=45), fitted)


@pytest.mark.parametrize(
    "decision", [FIXTURE.kickoff, FIXTURE.kickoff + timedelta(seconds=1), BASE.replace(tzinfo=None)]
)
def test_invalid_decision_clocks_are_rejected(decision) -> None:
    with pytest.raises(ValueError):
        forecast(HISTORY, FIXTURE, decision, CONFIG)


@pytest.mark.parametrize(
    "updates",
    [
        {"available_at": BASE},
        {"completed_at": BASE},
        {"kickoff": BASE.replace(tzinfo=None)},
        {"home_xg": float("nan")},
        {"away_xg": float("inf")},
        {"home_xg": True},
        {"home_xg": -1},
        {"home_goals": True},
        {"home_goals": 1.5},
        {"away_goals": None},
        {"match_id": ""},
    ],
)
def test_invalid_observations_fail_closed(updates) -> None:
    with pytest.raises(ValueError):
        observation(0, **updates)


@pytest.mark.parametrize(
    "updates",
    [
        {"window_matches": 0},
        {"min_team_matches": 6},
        {"prior_weight": 0},
        {"half_life_days": float("inf")},
        {"prior_home_xg": -1},
        {"calibration_lead_minutes": 0},
        {"min_calibration_matches": True},
    ],
)
def test_invalid_configuration_is_rejected(updates) -> None:
    with pytest.raises(ValueError):
        DynamicXGConfig(**updates)
