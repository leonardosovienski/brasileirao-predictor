"""elo_baseline — H0: probabilidades próprias, determinístico, favorito coerente."""
from datetime import datetime, timedelta, timezone

import pytest

from src.elo_baseline import EloBaselineEvaluator
from predictor_core.contracts.points import PredictionPoint


def _obs(n: int = 40) -> list:
    """'forte' vence sempre em casa e fora; 'fraco' perde sempre."""
    t0 = datetime(2026, 4, 1, tzinfo=timezone.utc)
    teams = [("forte", "fraco"), ("fraco", "forte"), ("forte", "medio"),
             ("medio", "fraco")]
    obs = []
    for i in range(n):
        home, away = teams[i % len(teams)]
        hg, ag = (2, 0) if home == "forte" else ((0, 2) if away == "forte" else (1, 1))
        obs.append({"home": home, "away": away,
                    "kickoff": t0 + timedelta(days=3 * i),
                    "result": {"home_goals": hg, "away_goals": ag}})
    return obs


def test_predictions_are_proper_distributions():
    ev = EloBaselineEvaluator()
    results = ev.run(_obs(), min_history=12)
    assert results
    for r in results:
        pp = r["prediction"]
        assert isinstance(pp, PredictionPoint)
        assert sum(pp.value.values()) == pytest.approx(1.0)
        assert all(0.0 <= v <= 1.0 for v in pp.value.values())


def test_strong_team_is_favored():
    ev = EloBaselineEvaluator()
    results = ev.run(_obs(), min_history=20)
    for r in results:
        md = r["prediction"].metadata
        v = r["prediction"].value
        if md["home"] == "forte":
            assert v["home"] > v["away"]
        elif md["away"] == "forte":
            assert v["away"] > v["home"]


def test_deterministic_across_runs():
    r1 = EloBaselineEvaluator().run(_obs(), min_history=12)
    r2 = EloBaselineEvaluator().run(_obs(), min_history=12)
    assert [r["prediction"].value for r in r1] == [r["prediction"].value for r in r2]


def test_draw_rate_comes_from_training_history():
    ev = EloBaselineEvaluator()
    ev.run(_obs(), min_history=12)
    assert 0.0 < ev.draw_rate < 1.0  # há empates (medio x fraco) no sintético
