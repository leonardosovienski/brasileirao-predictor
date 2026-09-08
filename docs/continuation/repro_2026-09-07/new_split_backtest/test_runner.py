"""Independent synthetic tests; no database or real 2026 outcomes are read."""

from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from economics import Policy
from runner import (
    apply_calibrator,
    digest,
    features,
    fit_calibrator,
    model_state,
    predict_frozen,
    probability_vectors,
)


def samples(n=200):
    rows, forecasts = [], []
    for i in range(n):
        score = (2, 0) if i < 110 else (1, 1) if i < 155 else (0, 1)
        rows.append({
            "event_id": i + 1,
            "home": "Home", "away": "Away",
            "kickoff": "2025-01-02T20:00:00Z", "date": "2025-01-02",
            "neutral": 0, "tournament": "Synthetic", "city": None,
            "result": {"home_goals": score[0], "away_goals": score[1]},
            "odds": {"1x2": [2.0, 4.0, 4.0], "ou25": [2.0, 2.0], "btts": [2.0, 2.0]},
        })
        forecasts.append({"event_id": i + 1, "p_1x2": [.6, .2, .2], "p_over25": .65, "p_btts": .65})
    return rows, forecasts


def test_brier_blend_has_known_interior_solution():
    rows, forecasts = samples()
    fitted = fit_calibrator(rows, forecasts, Policy())
    value = fitted["1x2"]
    # 110H/45D/45A gives mean target [.55,.225,.225] = q + .5*(p-q).
    assert value["n"] == 200
    assert value["enabled"] is True
    assert value["weight_model"] == pytest.approx(.5, abs=1e-12)
    assert value["brier_calibrated_2025"] < value["brier_market_2025"]
    assert value["brier_calibrated_2025"] < value["brier_raw_2025"]
    applied = apply_calibrator(forecasts[0], rows[0]["odds"], fitted, Policy())
    assert applied["p_1x2"] == pytest.approx([.55, .225, .225])
    assert sum(applied["p_1x2"]) == pytest.approx(1)


@pytest.mark.parametrize("score,expected", [((2, 0), 1.0), ((0, 2), 0.0)])
def test_blend_coefficient_is_clipped_to_convex_interval(score, expected):
    rows, forecasts = samples()
    for row in rows:
        row["result"] = {"home_goals": score[0], "away_goals": score[1]}
    assert fit_calibrator(rows, forecasts, Policy())["1x2"]["weight_model"] == expected


def test_identical_model_and_market_use_zero_weight_without_division():
    rows, forecasts = samples()
    for forecast in forecasts:
        forecast.update(p_1x2=[.5, .25, .25], p_over25=.5, p_btts=.5)
    result = fit_calibrator(rows, forecasts, Policy())
    assert all(entry["denominator"] == 0 for entry in result.values())
    assert all(entry["weight_model"] == 0 for entry in result.values())


def test_insufficient_calibration_disables_market_without_fallback():
    rows, forecasts = samples(199)
    fitted = fit_calibrator(rows, forecasts, Policy())
    assert all(not entry["enabled"] and entry["weight_model"] is None for entry in fitted.values())
    assert apply_calibrator(forecasts[0], rows[0]["odds"], fitted, Policy()) == {
        "p_1x2": None, "p_over25": None, "p_btts": None,
    }


def test_missing_vector_affects_only_its_market():
    rows, forecasts = samples()
    for row in rows:
        row["odds"]["1x2"][2] = None
    fitted = fit_calibrator(rows, forecasts, Policy())
    assert fitted["1x2"]["n"] == 0
    assert fitted["1x2"]["enabled"] is False
    assert fitted["ou25"]["n"] == fitted["btts"]["n"] == 200


@pytest.mark.parametrize("date,kickoff", [
    ("2026-01-02", "2026-01-02T20:00:00Z"),
    ("2024-01-02", "2024-01-02T20:00:00Z"),
    ("2026-01-02", "2025-01-02T20:00:00Z"),
])
def test_non2025_calibration_input_rejected_before_fit(date, kickoff):
    rows, forecasts = samples()
    rows[-1].update(date=date, kickoff=kickoff)
    with pytest.raises(ValueError, match="only 2025"):
        fit_calibrator(rows, forecasts, Policy())


def test_calibration_identity_and_cardinality_are_guarded():
    rows, forecasts = samples()
    with pytest.raises(ValueError, match="mismatch"):
        fit_calibrator(rows, forecasts[:-1], Policy())
    forecasts[0], forecasts[1] = forecasts[1], forecasts[0]
    with pytest.raises(ValueError, match="identity"):
        fit_calibrator(rows, forecasts, Policy())
    rows, forecasts = samples()
    rows[-1]["event_id"] = rows[0]["event_id"]
    forecasts[-1]["event_id"] = forecasts[0]["event_id"]
    with pytest.raises(ValueError, match="identity"):
        fit_calibrator(rows, forecasts, Policy())


def test_calibration_and_application_do_not_mutate_inputs():
    rows, forecasts = samples()
    before = deepcopy((rows, forecasts))
    fitted = fit_calibrator(rows, forecasts, Policy())
    fitted_before = deepcopy(fitted)
    apply_calibrator(forecasts[0], rows[0]["odds"], fitted, Policy())
    assert (rows, forecasts) == before
    assert fitted == fitted_before


class ForbiddenOutcomeAccess(dict):
    def __getitem__(self, key):
        if key in {"result", "odds", "home_xg", "away_xg", "home_goals", "away_goals"}:
            raise AssertionError(f"Prediction accessed forbidden {key}")
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default


def test_features_project_only_allowed_information():
    row = ForbiddenOutcomeAccess(samples(1)[0][0])
    result = features(row)
    assert set(result) == {"home", "away", "kickoff", "date", "tournament", "city", "neutral"}
    assert result["kickoff"].tzinfo == UTC


def fake_evaluator():
    return SimpleNamespace(
        elo={"Home": 1550.0}, params=(.1, .2, .3, .4), xg_params=None,
        _trained_at=datetime(2024, 12, 8, tzinfo=UTC), dynamic_states=None,
        _pending_history=None, blocked_observations=0, deferred_refits=0, xg_fit_failures=0,
    )


def prediction():
    return SimpleNamespace(value={"home": .6, "draw": .2, "away": .2},
                           metadata={"p_over": .65, "p_btts": .45})


def test_prediction_uses_serving_market_metadata_and_reports_cold_start():
    ev = fake_evaluator()
    ev.predict_step = lambda row: prediction()
    rows = [ForbiddenOutcomeAccess(samples(1)[0][0])]
    before = digest(model_state(ev))
    predicted = predict_frozen(ev, rows, before)
    assert predicted[0]["p_over25"] == .65
    assert predicted[0]["p_btts"] == .45
    assert predicted[0]["cold_start_teams"] == ["Away"]
    assert digest(model_state(ev)) == before


def test_queued_refit_is_rejected_before_prediction():
    ev = fake_evaluator()
    ev._pending_history = [{"anything": "forbidden"}]
    ev.predict_step = lambda row: pytest.fail("Must reject pending refit first")
    with pytest.raises(AssertionError, match="Queued refit"):
        predict_frozen(ev, samples(1)[0], digest(model_state(ev)))


def test_mutation_of_model_during_prediction_is_detected():
    ev = fake_evaluator()
    def mutating_predict(row):
        ev.elo["Home"] += 1
        return prediction()
    ev.predict_step = mutating_predict
    with pytest.raises(AssertionError, match="changed trained model state"):
        predict_frozen(ev, samples(1)[0], digest(model_state(ev)))


def test_digest_is_order_independent_and_sensitive_to_model_changes():
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})
    ev = fake_evaluator()
    before = digest(model_state(ev))
    ev.params = (.1, .2, .3, .5)
    assert digest(model_state(ev)) != before
    with pytest.raises(ValueError):
        digest({"not_finite": float("nan")})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -.1, 1.1, True])
def test_invalid_probability_values_fail(value):
    forecast = {"p_1x2": [.6, .2, .2], "p_over25": value, "p_btts": .45}
    with pytest.raises(ValueError):
        probability_vectors(forecast)


def test_probability_normalization_and_order_are_explicit():
    forecast = {"p_1x2": [.6, .2, .2], "p_over25": .65, "p_btts": .45}
    assert probability_vectors(forecast) == {"1x2": [.6, .2, .2], "ou25": [.65, .35], "btts": [.45, .55]}
    forecast["p_1x2"] = [.6, .3, .2]
    with pytest.raises(ValueError, match="normalization"):
        probability_vectors(forecast)
