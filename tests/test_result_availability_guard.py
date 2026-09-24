"""BR-F004: o ajuste walk-forward só pode usar resultado JÁ DISPONÍVEL no horizonte.

A guarda antiga cortava por `kickoff < horizonte`. Um jogo que começou antes do alvo e
ainda não terminou passava na guarda e entrava no ajuste com o placar final — vazamento de
futuro (no snapshot real: 2 de 20 refits na cadência do benchmark, 381 de 1956 com refit
a cada jogo). A regra PIT do projeto é `resultado disponível em kickoff + 180 min`
(`brasileirao_predictor.pit.RESULT_LATENCY`).

Cada teste compara o ajuste com e sem um jogo "em andamento" com placar absurdo: se o jogo
em andamento vazar, os parâmetros mudam.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from brasileirao_predictor.elo_baseline import EloBaselineEvaluator
from brasileirao_predictor.evaluator import BrasileiraoDixonColesEvaluator
from brasileirao_predictor.serving_evaluator import H9FrozenPolicyEvaluator, ServingStackEvaluator

TEAMS = ["flamengo", "palmeiras", "gremio", "santos", "bahia", "vitoria"]
HORIZON = datetime(2022, 6, 4, 22, 0, tzinfo=UTC)
CFG = {
    "tournament_name": "Brasileirão Série A",
    "elo": {
        "initial_rating": 1500,
        "home_advantage": 100,
        "window_years": 6,
        "form_half_life_years": 4.0,
        "k_factors": {"Brasileirão Série A": 30, "default": 30},
    },
    "model": {"calibration_window_years": 4, "goal_half_life_days": None, "max_goals": 6},
    "ensemble_xg": {"enabled": False},
}


def _history() -> list[dict]:
    """60 jogos terminados muito antes do horizonte (1 por dia)."""
    out = []
    start = HORIZON - timedelta(days=70)
    for i in range(60):
        home, away = TEAMS[i % 6], TEAMS[(i + 1 + i // 6) % 6]
        if home == away:
            away = TEAMS[(i + 2) % 6]
        kickoff = start + timedelta(days=i)
        out.append(
            {
                "home": home,
                "away": away,
                "kickoff": kickoff,
                "date": kickoff.strftime("%Y-%m-%d"),
                "tournament": "Brasileirão Série A",
                "neutral": 0,
                "result": {"home_goals": (i * 7) % 4, "away_goals": (i * 3) % 3, "home_xg": None, "away_xg": None},
            }
        )
    return out


def _with(minutes_before_horizon: int) -> list[dict]:
    """Histórico + um jogo com placar absurdo que começou `minutes_before_horizon` antes do alvo."""
    kickoff = HORIZON - timedelta(minutes=minutes_before_horizon)
    extra = {
        "home": "gremio",
        "away": "santos",
        "kickoff": kickoff,
        "date": kickoff.strftime("%Y-%m-%d"),
        "tournament": "Brasileirão Série A",
        "neutral": 0,
        "result": {"home_goals": 9, "away_goals": 0, "home_xg": None, "away_xg": None},
    }
    return [*_history(), extra]


def _state(ev) -> object:
    if isinstance(ev, BrasileiraoDixonColesEvaluator):
        return ev.fitted_parameters
    if isinstance(ev, EloBaselineEvaluator):
        return (sorted(ev.ratings.items()), ev.draw_rate)
    return (ev.params, sorted(ev.elo.items()))


def _factories():
    return {
        "dixon_coles": lambda: BrasileiraoDixonColesEvaluator(half_life_days=120, max_goals=4),
        "elo_baseline": lambda: EloBaselineEvaluator(),
        "serving": lambda: ServingStackEvaluator(CFG),
        "h9_frozen": lambda: H9FrozenPolicyEvaluator(dict(CFG, h9_frozen_policy={"params": [0.1, 0.3, 0.05, -0.05]})),
    }


@pytest.mark.parametrize("name", ["dixon_coles", "elo_baseline", "serving", "h9_frozen"])
def test_jogo_em_andamento_no_horizonte_nao_entra_no_ajuste(name: str) -> None:
    make = _factories()[name]
    clean, leaky = make(), make()
    clean._fit(_history(), HORIZON)
    leaky._fit(_with(minutes_before_horizon=60), HORIZON)
    assert _state(leaky) == _state(clean), "jogo que começou 60 min antes do alvo vazou para o ajuste"
    assert leaky.blocked_observations == 1


@pytest.mark.parametrize("name", ["dixon_coles", "elo_baseline", "serving"])
def test_resultado_disponivel_entra_no_ajuste(name: str) -> None:
    """A guarda não pode descartar jogo cujo resultado já existia (kickoff + 180 min < horizonte)."""
    make = _factories()[name]
    clean, used = make(), make()
    clean._fit(_history(), HORIZON)
    used._fit(_with(minutes_before_horizon=181), HORIZON)
    assert _state(used) != _state(clean)
    assert used.blocked_observations == 0
