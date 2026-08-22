"""Estados ofensivos/defensivos curto+longo como residuos do motor Elo."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable


def fit(
    history: Iterable[tuple[float, int, int]],
    params: tuple[float, ...],
    teams: Iterable[tuple[str, str]],
    *,
    alpha_short: float,
    alpha_long: float,
    ridge_reg: float = 1.0,
    eps: float = 0.1,
) -> dict[str, dict[str, float]]:
    """Estima razoes observados/esperados causais com prior neutro."""
    if not 0 < alpha_long <= alpha_short <= 1:
        raise ValueError("alphas exigem 0 < alpha_long <= alpha_short <= 1")
    if ridge_reg < 0 or eps <= 0:
        raise ValueError("ridge_reg deve ser >= 0 e eps deve ser > 0")

    a, b = float(params[0]), float(params[1])
    states: dict[str, dict[str, list[float]]] = defaultdict(dict)

    def update(team: str, key: str, observed: float, expected: float, alpha: float) -> None:
        num, den = states[team].get(key, [0.0, 0.0])
        states[team][key] = [(1 - alpha) * num + alpha * observed, (1 - alpha) * den + alpha * expected]

    for (diff, home_goals, away_goals), (home, away) in zip(history, teams, strict=True):
        lam_home = math.exp(a + b * float(diff) / 400.0)
        lam_away = math.exp(a - b * float(diff) / 400.0)
        for suffix, alpha in (("short", alpha_short), ("long", alpha_long)):
            update(home, f"attack_{suffix}", home_goals + eps, lam_home + eps, alpha)
            update(away, f"defence_{suffix}", home_goals + eps, lam_home + eps, alpha)
            update(away, f"attack_{suffix}", away_goals + eps, lam_away + eps, alpha)
            update(home, f"defence_{suffix}", away_goals + eps, lam_away + eps, alpha)

    return {
        team: {
            key: math.log(max(num + ridge_reg, eps) / max(den + ridge_reg, eps)) for key, (num, den) in values.items()
        }
        for team, values in states.items()
    }


def corrections(states: dict[str, dict[str, float]], home: str, away: str) -> tuple[float, float]:
    """Retorna correcoes log-rate com pesos simetricos e previamente fixos."""

    def value(team: str, key: str) -> float:
        return float(states.get(team, {}).get(key, 0.0))

    home_short = 0.5 * (value(home, "attack_short") + value(away, "defence_short"))
    home_long = 0.5 * (value(home, "attack_long") + value(away, "defence_long"))
    away_short = 0.5 * (value(away, "attack_short") + value(home, "defence_short"))
    away_long = 0.5 * (value(away, "attack_long") + value(home, "defence_long"))
    return 0.5 * (home_short + home_long), 0.5 * (away_short + away_long)
