"""Only manufactured fixtures; no historical project files or financial data."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from brasileirao_predictor.research.price_strength.dynamic_xg import (
    DynamicXGConfig,
    Fixture,
    XGObservation,
    fit_calibration,
    forecast,
)
from conditional_model import (
    AVAILABILITY_POLICY,
    CALIBRATION_END,
    CALIBRATION_START,
    calibrate_conditional,
    forecast_conditional,
)

CONFIG = DynamicXGConfig()


def synthetic_row(
    event_id: int,
    kickoff: datetime,
    home: str = "Synthetic A",
    away: str = "Synthetic B",
) -> dict:
    return {
        "event_id": event_id,
        "home": home,
        "away": away,
        "kickoff": kickoff.isoformat(),
        "result": {
            "home_xg": 1.0 + (event_id % 4) * 0.3,
            "away_xg": 0.6 + (event_id % 3) * 0.2,
            "home_goals": event_id % 4,
            "away_goals": event_id % 3,
        },
        "odds": "UNREAD_SYNTHETIC_SENTINEL",
    }


def manufactured_history() -> list[dict]:
    start = datetime(2023, 10, 1, 18, tzinfo=UTC)
    rows = [synthetic_row(i + 1, start + timedelta(days=i * 7)) for i in range(8)]
    calibration_start = datetime(2024, 1, 5, 18, tzinfo=UTC)
    rows.extend(
        synthetic_row(i + 101, calibration_start + timedelta(days=i * 10))
        for i in range(30)
    )
    return rows


def target_2025() -> dict:
    return synthetic_row(1000, datetime(2025, 2, 1, 18, tzinfo=UTC))


def manufactured_strict_observations(rows: list[dict]) -> list[XGObservation]:
    # These clocks are part of fabricated test records. This conversion must
    # never be applied to project history to invent observed availability.
    observations = []
    for row in rows:
        kickoff = datetime.fromisoformat(row["kickoff"])
        observations.append(
            XGObservation(
                str(row["event_id"]),
                row["home"],
                row["away"],
                kickoff,
                kickoff + timedelta(hours=2),
                kickoff + timedelta(hours=48),
                **row["result"],
            )
        )
    return observations


def strict_target(row: dict) -> Fixture:
    return Fixture(
        str(row["event_id"]),
        row["home"],
        row["away"],
        datetime.fromisoformat(row["kickoff"]),
    )


def test_raw_matches_frozen_candidate_on_manufactured_observed_clocks():
    rows, target = manufactured_history(), target_2025()
    conditional = forecast_conditional(rows, target, CONFIG)
    strict = forecast(
        manufactured_strict_observations(rows),
        strict_target(target),
        datetime.fromisoformat(target["kickoff"])
        - timedelta(minutes=CONFIG.calibration_lead_minutes),
        CONFIG,
    )
    assert conditional["eligible"] and strict.eligible
    assert conditional["lambda_home"] == strict.lambda_home
    assert conditional["lambda_away"] == strict.lambda_away
    assert conditional["probabilities"] == strict.probabilities
    assert conditional["history_ids"] == list(strict.history_match_ids)
    assert conditional["availability_policy"] == AVAILABILITY_POLICY
    assert (
        "available_at" not in conditional and "latest_available_at" not in conditional
    )


def test_calibration_and_calibrated_forecast_match_frozen_candidate_on_synthetic_clocks():
    rows, target = manufactured_history(), target_2025()
    conditional_calibration = calibrate_conditional(rows, CONFIG)
    observations = manufactured_strict_observations(rows)
    strict_calibration = fit_calibration(
        observations, CALIBRATION_START, CALIBRATION_END, CONFIG
    )
    assert conditional_calibration["n_matches"] == strict_calibration.n_matches == 30
    assert conditional_calibration["home_scale"] == strict_calibration.home_scale
    assert conditional_calibration["away_scale"] == strict_calibration.away_scale
    assert conditional_calibration["used_match_ids"] == list(
        strict_calibration.used_match_ids
    )
    conditional = forecast_conditional(rows, target, CONFIG, conditional_calibration)
    strict = forecast(
        observations,
        strict_target(target),
        datetime.fromisoformat(target["kickoff"])
        - timedelta(minutes=CONFIG.calibration_lead_minutes),
        CONFIG,
        strict_calibration,
    )
    assert conditional["probabilities"] == strict.probabilities
    assert conditional["lambda_home"] == strict.lambda_home
    assert conditional["lambda_away"] == strict.lambda_away
    assert conditional["calibration_applied"]


def test_equivalence_with_distinct_opponent_histories_and_wrong_venue_rows():
    rows = manufactured_history()
    for index, row in enumerate(rows):
        if index % 2:
            row["home"] = "Synthetic D"
        else:
            row["away"] = "Synthetic C"
    rows.extend(
        synthetic_row(
            700 + i,
            datetime(2025, 1, 5, tzinfo=UTC) + timedelta(days=i * 4),
            "Synthetic B",
            "Synthetic A",
        )
        for i in range(3)
    )
    target = target_2025()
    actual = forecast_conditional(rows, target, CONFIG)
    expected = forecast(
        manufactured_strict_observations(rows),
        strict_target(target),
        datetime.fromisoformat(target["kickoff"])
        - timedelta(minutes=CONFIG.calibration_lead_minutes),
        CONFIG,
    )
    assert actual["eligible"] and expected.eligible
    assert actual["probabilities"] == expected.probabilities
    assert actual["history_ids"] == list(expected.history_match_ids)
    assert not {"700", "701", "702"}.intersection(actual["history_ids"])


def test_future_rows_and_own_result_do_not_change_raw_forecast():
    rows, target = manufactured_history(), target_2025()
    expected = forecast_conditional(rows, target, CONFIG)
    own = deepcopy(target)
    own["result"] = {
        "home_xg": float("nan"),
        "away_xg": -10,
        "home_goals": 99999,
        "away_goals": 0,
    }
    future = synthetic_row(2000, datetime(2025, 3, 1, tzinfo=UTC))
    future["result"] = {"home_xg": float("inf"), "away_xg": True}
    target["result"] = None
    assert forecast_conditional([*rows, own, future], target, CONFIG) == expected


def test_raw_does_not_read_goal_labels_or_odds():
    class NoLabelsOrOdds(dict):
        def __getitem__(self, key):
            if key in {"odds", "home_goals", "away_goals"}:
                raise AssertionError("forbidden result or odds access")
            return super().__getitem__(key)

        def get(self, key, default=None):
            if key in {"odds", "home_goals", "away_goals"}:
                raise AssertionError("forbidden result or odds access")
            return super().get(key, default)

    rows = manufactured_history()
    guarded = [
        NoLabelsOrOdds({**row, "result": NoLabelsOrOdds(row["result"])}) for row in rows
    ]
    assert forecast_conditional(guarded, target_2025(), CONFIG) == forecast_conditional(
        rows, target_2025(), CONFIG
    )


def test_assumed_48_hour_boundary_is_strict():
    target = target_2025()
    decision = datetime.fromisoformat(target["kickoff"]) - timedelta(
        minutes=CONFIG.calibration_lead_minutes
    )
    old = [synthetic_row(i + 1, decision - timedelta(days=10 + i)) for i in range(3)]
    boundary = synthetic_row(100, decision - timedelta(hours=48))
    expected = forecast_conditional(old, target, CONFIG)
    assert forecast_conditional([*old, boundary], target, CONFIG) == expected
    boundary["kickoff"] = (decision - timedelta(hours=48, microseconds=1)).isoformat()
    assert (
        "100" in forecast_conditional([*old, boundary], target, CONFIG)["history_ids"]
    )


def test_missing_xg_excludes_history_but_not_the_forecast_target():
    rows = manufactured_history()
    rows[-1]["result"]["home_xg"] = None
    target = target_2025()
    target["result"] = None
    actual = forecast_conditional(rows, target, CONFIG)
    expected = forecast_conditional(rows[:-1], target, CONFIG)
    assert actual["eligible"]
    assert actual["probabilities"] == expected["probabilities"]
    assert str(rows[-1]["event_id"]) not in actual["history_ids"]
    assert actual["excluded_missing_xg_ids"] == [str(rows[-1]["event_id"])]


def test_missing_xg_does_not_remove_a_calibration_target_with_goal_labels():
    rows = manufactured_history()
    expected = calibrate_conditional(rows, CONFIG)
    rows[-1]["result"]["home_xg"] = None
    rows[-1]["result"]["away_xg"] = None
    actual = calibrate_conditional(rows, CONFIG)
    assert actual == expected  # Last target xG cannot affect its own raw forecast.


def test_cold_start_never_promotes_priors():
    prediction = forecast_conditional(manufactured_history()[:2], target_2025(), CONFIG)
    assert not prediction["eligible"]
    assert prediction["reason"] == "INSUFFICIENT_HISTORY"
    assert prediction["probabilities"] == {}
    assert prediction["lambda_home"] is None and prediction["lambda_away"] is None


def test_venue_samples_are_required_for_both_teams():
    rows = manufactured_history()
    for row in rows:
        row["home"], row["away"] = row["away"], row["home"]
    assert (
        forecast_conditional(rows, target_2025(), CONFIG)["reason"]
        == "INSUFFICIENT_HISTORY"
    )


def test_duplicate_ids_fail_even_if_identical_or_future():
    rows = manufactured_history()
    with pytest.raises(ValueError, match="duplicate"):
        forecast_conditional([*rows, rows[0]], target_2025(), CONFIG)
    future = synthetic_row(9999, datetime(2026, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="duplicate"):
        calibrate_conditional([*rows, future, deepcopy(future)], CONFIG)


def test_row_order_invariance():
    rows = manufactured_history()
    assert forecast_conditional(
        reversed(rows), target_2025(), CONFIG
    ) == forecast_conditional(rows, target_2025(), CONFIG)
    assert calibrate_conditional(reversed(rows), CONFIG) == calibrate_conditional(
        rows, CONFIG
    )


def test_calibration_uses_2024_targets_with_strict_year_end_lag_only():
    rows = manufactured_history()
    expected = calibrate_conditional(rows, CONFIG)
    boundary = synthetic_row(501, CALIBRATION_END - timedelta(hours=48))
    future = synthetic_row(502, datetime(2025, 1, 2, tzinfo=UTC))
    boundary["result"] = future["result"] = {"home_goals": -999, "away_goals": False}
    assert calibrate_conditional([*rows, boundary, future], CONFIG) == expected
    before = synthetic_row(503, CALIBRATION_END - timedelta(hours=48, microseconds=1))
    actual = calibrate_conditional([*rows, before], CONFIG)
    assert actual["n_matches"] == expected["n_matches"] + 1
    assert "503" in actual["target_match_ids"]
    assert all(100 < int(match_id) < 504 for match_id in actual["target_match_ids"])


def test_calibration_future_labels_and_last_target_xg_are_irrelevant():
    rows = manufactured_history()
    expected = calibrate_conditional(rows, CONFIG)
    rows[-1]["result"]["home_xg"] = 99999
    rows[-1]["result"]["away_xg"] = 99999
    future = synthetic_row(9000, datetime(2025, 9, 1, tzinfo=UTC))
    future["result"] = {"home_goals": 99999, "away_goals": 99999}
    assert calibrate_conditional([*rows, future], CONFIG) == expected


def test_insufficient_calibration_blocks_calibrated_but_not_raw_prediction():
    rows = manufactured_history()[:12]
    calibration = calibrate_conditional(rows, CONFIG)
    assert not calibration["eligible"]
    assert calibration["home_scale"] == calibration["away_scale"] == 1.0
    assert forecast_conditional(rows, target_2025(), CONFIG)["eligible"]
    assert (
        forecast_conditional(rows, target_2025(), CONFIG, calibration)["reason"]
        == "INSUFFICIENT_CALIBRATION"
    )


def test_calibration_rejects_wrong_config_policy_or_nonprior_cutoff():
    rows, target = manufactured_history(), target_2025()
    calibration = calibrate_conditional(rows, CONFIG)
    with pytest.raises(ValueError, match="configuration"):
        forecast_conditional(
            rows, target, replace(CONFIG, window_matches=6), calibration
        )
    with pytest.raises(ValueError, match="conditional"):
        forecast_conditional(
            rows, target, CONFIG, {**calibration, "availability_policy": "OBSERVED"}
        )
    decision = datetime.fromisoformat(target["kickoff"]) - timedelta(
        minutes=CONFIG.calibration_lead_minutes
    )
    with pytest.raises(ValueError, match="strictly before"):
        forecast_conditional(
            rows,
            target,
            CONFIG,
            {**calibration, "calibration_end": decision.isoformat()},
        )
    with pytest.raises(ValueError, match="own calibration"):
        forecast_conditional(
            rows,
            target,
            CONFIG,
            {**calibration, "used_match_ids": [str(target["event_id"])]},
        )


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), -1, True, "1.2", 10**400]
)
def test_visible_invalid_xg_fails_closed(value):
    rows = manufactured_history()
    rows[-1]["result"]["home_xg"] = value
    with pytest.raises((ValueError, TypeError)):
        forecast_conditional(rows, target_2025(), CONFIG)


def test_naive_kickoff_is_rejected():
    target = target_2025()
    target["kickoff"] = "2025-02-01T18:00:00"
    with pytest.raises(ValueError, match="timezone"):
        forecast_conditional(manufactured_history(), target, CONFIG)
