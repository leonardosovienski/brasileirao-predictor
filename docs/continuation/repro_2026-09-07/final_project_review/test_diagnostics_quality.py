"""Synthetic audit of forecast metrics and paired round resampling."""

import math
from copy import deepcopy

import pytest
from diagnostics_quality import (
    MARKETS,
    METRICS,
    MODELS,
    cluster_bootstrap,
    estimate_climatology,
    prepare_losses,
    score_forecast,
    valid_quotes,
)


def historical(identifier, year, score):
    return {"event_id": identifier, "kickoff": f"{year}-06-01T20:00:00Z", "date": f"{year}-06-01",
            "result": {"home_goals": score[0], "away_goals": score[1]}}


def test_climatology_uses_only_training_outcomes():
    rows = [historical(1, 2021, (3, 0)), historical(2, 2022, (1, 1)), historical(3, 2023, (0, 2))]
    ignored = historical(4, 2025, (0, 0))
    ignored["result"] = "Cannot be interpreted as an outcome"
    result = estimate_climatology(rows + [ignored])
    assert result["n"] == 3
    assert result["probabilities"]["1x2"] == [1 / 3] * 3
    assert result["probabilities"]["ou25"] == [1 / 3, 2 / 3]
    assert result["probabilities"]["btts"] == [1 / 3, 2 / 3]


def test_climatology_rejects_future_years_and_duplicate_identity():
    with pytest.raises(ValueError, match="2026"):
        estimate_climatology([historical(1, 2026, (1, 1))])
    row = historical(1, 2021, (1, 1))
    with pytest.raises(ValueError, match="Duplicate"):
        estimate_climatology([row, deepcopy(row)])


def test_climatology_has_no_undeclared_zero_class_smoothing():
    with pytest.raises(ValueError, match="zero class"):
        estimate_climatology([historical(1, 2021, (3, 0))])


def test_known_brier_and_log_loss_values():
    assert score_forecast([1, 0, 0], 0) == {"brier": 0, "log_loss": 0}
    uniform = score_forecast([1 / 3] * 3, 2)
    assert uniform["brier"] == pytest.approx(2 / 3)
    assert uniform["log_loss"] == pytest.approx(math.log(3))
    binary = score_forecast([.8, .2], 0)
    assert binary["brier"] == pytest.approx(.04)
    assert binary["log_loss"] == pytest.approx(-math.log(.8))
    assert math.isfinite(score_forecast([0, 1], 0)["log_loss"])


@pytest.mark.parametrize("probability", [float("nan"), float("inf"), -.1, 1.1, True])
def test_invalid_scoring_probabilities_rejected(probability):
    with pytest.raises(ValueError):
        score_forecast([probability, .2], 0)


def loss_row(identifier, round_number, value):
    return {"event_id": identifier, "round": round_number,
            "losses": {model: {metric: value for metric in METRICS} for model in MODELS}}


def test_round_bootstrap_is_paired_deterministic_and_event_weighted():
    rows = [loss_row(1, 1, 0), loss_row(2, 1, 0), loss_row(3, 2, 1)]
    result = cluster_bootstrap(rows, seed=12, replicates=1000)
    assert result == cluster_bootstrap(rows, seed=12, replicates=1000)
    assert result["n"] == 3 and result["cluster_count"] == 2
    assert result["events_by_round"] == {"1": 2, "2": 1}
    assert result["models"]["raw"]["brier"]["mean"] == pytest.approx(1 / 3)
    assert result["models"]["raw"]["brier"]["ci95"] == [0, 1]
    for pair in result["paired_differences"].values():
        for metric in pair.values():
            assert metric == {"mean": 0, "ci95": [0, 0]}


def test_one_round_has_no_fabricated_interval_and_empty_panel_is_explicit():
    result = cluster_bootstrap([loss_row(1, 4, .4)], seed=10)
    assert result["models"]["raw"]["brier"]["ci95"] is None
    assert result["few_clusters_warning"] is True
    assert cluster_bootstrap([], seed=10)["status"] == "NO_COMMON_PANEL"


def selection():
    return {"odds_bounds_inclusive": {"1x2": [1.05, 20], "ou25": [1.2, 5], "btts": [1.2, 5]},
            "overround_inclusive": [1.0, 1.3]}


def test_quote_gates_require_complete_finite_vectors():
    assert valid_quotes([2, 4, 4], "1x2", selection())
    for odds in ([2, None, 4], [2, 4], [2, 8, 8], [1.1, 1.1, 1.1], [2, True, 4]):
        assert not valid_quotes(odds, "1x2", selection())


def derived_rows():
    events, raw, calibrated, forecasts = [], [], [], []
    for i in range(1, 3):
        outcome = {"home_goals": 3, "away_goals": 0} if i == 1 else None
        state = "COMPLETED" if i == 1 else "PENDING_RESULT"
        quotes = {"1x2": [2, 4, 4], "ou25": [2, 2], "btts": [2, 2]}
        base = {"event_id": i, "season": 2026, "round": 1, "role": "test_exploratory",
                "kickoff": f"2026-01-0{i}T20:00:00Z", "completion_state": state,
                "result": outcome, "odds": quotes}
        arm = {"id": i, "round": 1, "role": "test_exploratory", "kickoff_at": base["kickoff"],
               "completion_state": state, "home_goals": outcome["home_goals"] if outcome else None,
               "away_goals": outcome["away_goals"] if outcome else None, "odds": quotes,
               "p_1x2": [.5, .25, .25], "p_over25": .5, "p_btts": .5,
               "candidate_frozen2025_hash": "fixed"}
        events.append(base)
        raw.append(deepcopy(arm))
        calibrated.append(deepcopy(arm))
        forecasts.append({"event_id": i, "p_1x2": [.5, .25, .25], "p_over25": .5, "p_btts": .5})
    return events, {"diagnostic_raw": raw, "primary_calibrated": calibrated}, forecasts


def test_common_panel_keeps_pending_out_of_loss_and_preserves_denominator():
    events, replay, forecasts = derived_rows()
    climate = {"probabilities": {"1x2": [1 / 3] * 3, "ou25": [.5, .5], "btts": [.5, .5]}}
    losses, coverage = prepare_losses(events, replay, forecasts, climate, {"selection": selection()}, "fixed")
    assert len(losses) == 3
    assert {row["event_id"] for row in losses} == {1}
    assert coverage["test_exploratory"]["official_fixtures"] == 2
    for market in MARKETS:
        assert coverage["test_exploratory"]["markets"][market]["excluded_not_completed"] == 1


def test_cross_artifact_prediction_and_result_changes_are_rejected():
    events, replay, forecasts = derived_rows()
    climate = {"probabilities": {"1x2": [1 / 3] * 3, "ou25": [.5, .5], "btts": [.5, .5]}}
    replay["diagnostic_raw"][0]["p_btts"] = .4
    with pytest.raises(ValueError, match="saved forecasts"):
        prepare_losses(events, replay, forecasts, climate, {"selection": selection()}, "fixed")
    events, replay, forecasts = derived_rows()
    replay["primary_calibrated"][0]["home_goals"] = 7
    with pytest.raises(ValueError, match="outcomes differ"):
        prepare_losses(events, replay, forecasts, climate, {"selection": selection()}, "fixed")
