"""H4 — otimizador MLE + walk-forward: recupera força conhecida, sem leakage, PredictionPoint."""

import math
import random
from datetime import UTC, datetime, timedelta

import pytest
from predictor_core.contracts.points import PredictionPoint

from src.dixon_coles import fit_dixon_coles_parameters
from src.evaluator import BrasileiraoDixonColesEvaluator


def _synth_games(n_rounds: int = 30, seed: int = 7) -> list:
    """Liga sintética de 4 times com forças verdadeiras conhecidas:
    'forte' ataca 1.8x a média, 'fraco' 0.6x."""
    rng = random.Random(seed)
    attack = {"forte": 1.8, "medio1": 1.0, "medio2": 0.9, "fraco": 0.6}
    teams = list(attack)
    games = []
    day = 0
    for _ in range(n_rounds):
        rng.shuffle(teams)
        for h, a in [(teams[0], teams[1]), (teams[2], teams[3])]:
            lam, mu = 1.3 * attack[h], attack[a]
            games.append(
                {
                    "home": h,
                    "away": a,
                    "home_goals": _poisson(rng, lam),
                    "away_goals": _poisson(rng, mu),
                    "day": day,
                }
            )
            day += 2
    last = max(g["day"] for g in games)
    for g in games:
        g["days_ago"] = float(last - g.pop("day"))
    return games


def _poisson(rng: random.Random, lam: float) -> int:
    threshold, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= threshold:
            return k
        k += 1


# ---------- fit_dixon_coles_parameters ----------


def test_fit_recovers_strength_ordering():
    params = fit_dixon_coles_parameters(_synth_games(), xi_fixed=0.0)
    assert params["attack"]["forte"] > params["attack"]["medio1"] > params["attack"]["fraco"]
    assert params["home_advantage"] > 1.0
    lo, hi = -0.35, 0.35
    assert lo <= params["rho"] <= hi


def test_fit_identification_mean_attack_near_one():
    params = fit_dixon_coles_parameters(_synth_games(), xi_fixed=0.0)
    logs = [math.log(v) for v in params["attack"].values()]
    assert abs(sum(logs) / len(logs)) < 0.05  # penalidade segura a identificação


def test_fit_rejects_empty_and_single_team():
    with pytest.raises(ValueError):
        fit_dixon_coles_parameters([], xi_fixed=0.0)


# ---------- BrasileiraoDixonColesEvaluator ----------


def _observations(n_rounds: int = 25) -> list:
    t0 = datetime(2026, 4, 1, tzinfo=UTC)
    games = _synth_games(n_rounds)
    games.sort(key=lambda g: -g["days_ago"])
    obs = []
    for i, g in enumerate(games):
        obs.append(
            {
                "home": g["home"],
                "away": g["away"],
                "kickoff": t0 + timedelta(days=2 * i),
                "result": {"home_goals": g["home_goals"], "away_goals": g["away_goals"]},
            }
        )
    return obs


def test_evaluator_xi_from_half_life():
    ev = BrasileiraoDixonColesEvaluator(half_life_days=120)
    assert ev.xi == pytest.approx(math.log(2) / 120)
    with pytest.raises(ValueError):
        BrasileiraoDixonColesEvaluator(half_life_days=0)


def test_walkforward_returns_prediction_points():
    ev = BrasileiraoDixonColesEvaluator(half_life_days=120, max_goals=8)
    results = ev.run(_observations(), min_history=30, retrain_every=10)
    assert results
    for r in results:
        pp = r["prediction"]
        assert isinstance(pp, PredictionPoint)
        assert sum(pp.value.values()) == pytest.approx(1.0)
        assert pp.matures_at >= pp.predicted_at  # invariante do contrato
        assert r["actual"]["home_goals"] >= 0


def test_walkforward_prediction_never_uses_future_kickoff():
    ev = BrasileiraoDixonColesEvaluator(half_life_days=120, max_goals=8)
    results = ev.run(_observations(), min_history=30, retrain_every=10)
    for r in results:
        pp = r["prediction"]
        assert pp.predicted_at < pp.matures_at  # treinado só com jogos anteriores
