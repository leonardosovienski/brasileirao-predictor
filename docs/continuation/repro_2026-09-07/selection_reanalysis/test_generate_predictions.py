"""Temporal leakage tests and a real serving probability integration test."""

from __future__ import annotations

import copy
import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("isolated_generate_predictions", HERE / "generate_predictions.py")
gp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gp)

CFG = {
    "tournament_name": "Brasileirão Série A",
    "elo": {"initial_rating": 1500, "home_advantage": 100, "window_years": 6, "form_half_life_years": 4, "k_factors": {"default": 30}},
    "model": {"calibration_window_years": 4, "goal_half_life_days": None, "max_goals": 12},
    "ensemble_xg": {"enabled": False},
}


def event(number, kickoff, *, home="A", away="B", goals=(1, 0)):
    return {"event_id": number, "home": home, "away": away, "kickoff": kickoff.isoformat(), "date": kickoff.date().isoformat(), "tournament": "Brasileirão Série A", "city": None, "neutral": 0, "result": {"home_goals": goals[0], "away_goals": goals[1], "home_xg": None, "away_xg": None}, "odds": {"1x2": [2, 3, 4]}}


class SpyEvaluator:
    fits = []
    features = []

    def __init__(self, cfg, *, max_goals):
        assert max_goals == 12
        self.elo = {"A": 1500, "B": 1500}
        self.params = None

    def _fit(self, history, horizon):
        assert all(row["kickoff"] <= horizon - timedelta(hours=48) for row in history)
        assert all("odds" not in row for row in history)
        self.fits.append(([row["event_id"] for row in history], horizon))
        self.params = [1]

    def predict_step(self, features):
        assert "result" not in features and "odds" not in features
        assert "home_xg" not in features and "away_xg" not in features
        self.features.append(features)
        return SimpleNamespace(value={"home": 0.5, "draw": 0.3, "away": 0.2}, metadata={"p_over": 0.4, "p_btts": 0.45, "ensemble": False})


@pytest.fixture(autouse=True)
def clear_spy():
    SpyEvaluator.fits = []
    SpyEvaluator.features = []


class NoLabelAccess(dict):
    def __getitem__(self, key):
        if key in {"result", "odds"}:
            raise AssertionError(f"Target/future {key} accessed before prediction")
        return super().__getitem__(key)


def test_inclusive_48h_buffer_excludes_nearby_and_simultaneous_labels():
    target = datetime(2024, 2, 10, 20, tzinfo=UTC)
    cutoff = target - timedelta(hours=49)
    rows = [event(1, cutoff - timedelta(days=1)), event(2, cutoff), NoLabelAccess(event(3, cutoff + timedelta(seconds=1))), NoLabelAccess(event(4, target)), NoLabelAccess(event(5, target))]
    result = gp.generate(rows, CFG, SpyEvaluator, min_history=2, refit_every=100)
    assert SpyEvaluator.fits == [([1, 2], target - timedelta(hours=1))]
    assert [row["event_id"] for row in result["forecasts"]] == [4, 5]
    assert result["forecasts"][0]["metadata"]["fit_training_last_kickoff"] == cutoff.isoformat(timespec="seconds")


def test_refits_count_new_eligible_matches_and_ignore_odds_presence():
    first = datetime(2023, 1, 1, 20, tzinfo=UTC)
    rows = [event(i, first + timedelta(days=3 * i)) for i in range(9)]
    for row in rows:
        row.pop("odds")
    result = gp.generate(list(reversed(rows)), CFG, SpyEvaluator, min_history=2, refit_every=3)
    assert [len(ids) for ids, _time in SpyEvaluator.fits] == [2, 5, 8]
    assert len(result["forecasts"]) == 7
    assert [row["metadata"]["refit_number"] for row in result["forecasts"]] == [1, 1, 1, 2, 2, 2, 3]
    assert all("odds" not in row and "result" not in row for row in result["forecasts"])


def test_future_year_and_duplicate_id_fail_before_any_fit():
    first = datetime(2024, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="2021--2025"):
        gp.generate([NoLabelAccess(event(1, first.replace(year=2026)))], CFG, SpyEvaluator, min_history=2)
    with pytest.raises(ValueError, match="Duplicate"):
        gp.generate([event(1, first), event(1, first + timedelta(days=3))], CFG, SpyEvaluator, min_history=2)
    assert not SpyEvaluator.fits


def test_invalid_model_probabilities_fail_instead_of_renormalizing():
    class InvalidEvaluator(SpyEvaluator):
        def predict_step(self, features):
            pred = super().predict_step(features)
            pred.value["away"] = 0.8
            return pred

    first = datetime(2023, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="not normalized"):
        gp.generate([event(i, first + timedelta(days=i * 3)) for i in range(3)], CFG, InvalidEvaluator, min_history=2)


def test_real_serving_normalized_and_adversarial_target_label_invariant():
    sys.path.insert(0, str(gp.DEFAULT_REPO))
    from brasileirao_predictor.serving_evaluator import ServingStackEvaluator

    first = datetime(2022, 1, 1, 20, tzinfo=UTC)
    teams = ["A", "B", "C", "D"]
    rows = [event(i, first + timedelta(days=7 * i), home=teams[i % 4], away=teams[(i + 1) % 4], goals=((i * 3 + 1) % 4, (i * 7) % 3)) for i in range(26)]
    baseline = gp.generate(rows, CFG, ServingStackEvaluator, min_history=20, refit_every=100)
    changed = copy.deepcopy(rows)
    for row in changed[20:]:
        row["result"] = {"home_goals": 100, "away_goals": 99, "home_xg": 1e5, "away_xg": 1e5}
        row["odds"] = {"injected": "must never reach the forecast"}
    altered = gp.generate(changed, CFG, ServingStackEvaluator, min_history=20, refit_every=100)
    for left, right in zip(baseline["forecasts"], altered["forecasts"], strict=True):
        assert left["p_1x2"] == right["p_1x2"]
        assert left["p_over25"] == right["p_over25"]
        assert left["p_btts"] == right["p_btts"]
        assert sum(left["p_1x2"]) == pytest.approx(1, abs=1e-9)
        assert all(0 <= p <= 1 for p in [*left["p_1x2"], left["p_over25"], left["p_btts"]])
