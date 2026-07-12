"""dixon_coles — matemática de correlação base de Dixon & Coles (1997), Python puro.

Roadmap de setembro/2026. NÃO é o motor de previsão (esse é `src/model.py`,
Binomial Negativa + correção DC via scipy): esta é a CLASSE BASE da matemática
de correlação, stdlib pura, isolada para ser testável célula a célula e
candidata a promoção futura ao predictor_core.

Dois ingredientes de Dixon & Coles, "Modelling Association Football Scores and
Inefficiencies in the Football Betting Market" (JRSS-C 46, 1997):

  ρ (rho)  — a independência Poisson×Poisson erra sistematicamente nos placares
             MAGROS (0-0, 1-0, 0-1, 1-1): empates baixos são mais frequentes do
             que o produto das marginais prevê. τ(x, y) reponta essas 4 células
             (só elas) por um fator dependente de ρ; ρ<0 é o regime típico do
             futebol (infla 0-0 e 1-1, deflaciona 1-0 e 0-1).

  ξ (xi)   — decaimento temporal: um jogo de 8 meses atrás informa menos que um
             da semana passada. Peso φ(Δt) = exp(-ξ·Δt) multiplicando a
             log-verossimilhança de cada partida no ajuste. (No paper é φ; o
             masterplan a chama de "função tau de decaimento" — aqui os nomes
             seguem o paper para não colidir com o τ de correlação.)
"""
from __future__ import annotations

import math

__all__ = ["dc_tau", "time_decay_weight", "DixonColesMatrix"]


def dc_tau(home_goals: int, away_goals: int, lam: float, mu: float,
           rho: float) -> float:
    """Fator de ajuste τ(x, y) de Dixon-Coles para o placar (x=casa, y=fora).

    lam/mu: médias esperadas de gols de casa/fora. Fora das 4 células magras,
    τ = 1 (a independência fica intacta). O chamador é responsável por manter
    ρ numa faixa em que τ > 0 para os (lam, mu) do dataset — `valid_rho_bounds`
    da classe dá a faixa segura; aqui, τ <= 0 é erro explícito (probabilidade
    negativa é corrupção silenciosa da matriz)."""
    if home_goals == 0 and away_goals == 0:
        t = 1.0 - lam * mu * rho
    elif home_goals == 0 and away_goals == 1:
        t = 1.0 + lam * rho
    elif home_goals == 1 and away_goals == 0:
        t = 1.0 + mu * rho
    elif home_goals == 1 and away_goals == 1:
        t = 1.0 - rho
    else:
        return 1.0
    if t <= 0.0:
        raise ValueError(
            f"tau({home_goals},{away_goals}) = {t:.4g} <= 0 com rho={rho}, "
            f"lam={lam}, mu={mu} — rho fora da faixa válida para estas médias")
    return t


def time_decay_weight(days_ago: float, xi: float) -> float:
    """Peso exponencial φ(Δt) = exp(-ξ·Δt) de uma partida jogada há `days_ago` dias.

    ξ = 0 → todo o histórico pesa igual (sem decaimento). ξ típico do paper
    (half-life ~4 meses em unidades de dia): ξ = ln(2)/120 ≈ 0.0058.
    Δt negativo (jogo no futuro) é erro — o decaimento nunca deve mascarar
    lookahead do chamador."""
    if xi < 0:
        raise ValueError(f"xi deve ser >= 0 (recebido {xi})")
    if days_ago < 0:
        raise ValueError(
            f"days_ago negativo ({days_ago}) — partida no futuro do corte; "
            "isso é lookahead do chamador, não decaimento")
    return math.exp(-xi * days_ago)


class DixonColesMatrix:
    """Matriz de placar Poisson×Poisson com correção ρ nas células magras.

    dc = DixonColesMatrix(lam=1.4, mu=1.1, rho=-0.05)
    dc.score_prob(0, 0)      # P(0-0), corrigida e renormalizada
    dc.grid(max_goals=8)     # matriz completa [(casa)][(fora)]
    dc.outcome_probs()       # {"home", "draw", "away"} somando 1

    A correção τ quebra a soma-1 da grade; a classe renormaliza pela massa
    total truncada em max_goals — as probabilidades devolvidas são sempre uma
    distribuição própria. Puro e imutável após a construção: o ajuste de
    (lam, mu, rho, xi) por verossimilhança pesada é papel do motor de domínio
    (src/model.py), não desta base."""

    def __init__(self, lam: float, mu: float, rho: float = 0.0,
                 max_goals: int = 10):
        if lam <= 0 or mu <= 0:
            raise ValueError(f"lam e mu devem ser > 0 (lam={lam}, mu={mu})")
        if max_goals < 1:
            raise ValueError("max_goals >= 1")
        lo, hi = self.valid_rho_bounds(lam, mu)
        if not (lo < rho < hi):
            raise ValueError(
                f"rho={rho} fora da faixa válida ({lo:.4g}, {hi:.4g}) "
                f"para lam={lam}, mu={mu} — tau ficaria <= 0")
        self.lam = lam
        self.mu = mu
        self.rho = rho
        self.max_goals = max_goals
        self._grid = self._build_grid()

    @staticmethod
    def valid_rho_bounds(lam: float, mu: float) -> tuple:
        """Faixa aberta de ρ que mantém τ > 0 nas 4 células (Dixon & Coles, eq. 4.3):
        max(-1/λ, -1/μ) < ρ < min(1/(λμ), 1)."""
        return (max(-1.0 / lam, -1.0 / mu), min(1.0 / (lam * mu), 1.0))

    @staticmethod
    def _poisson_pmf(k: int, rate: float) -> float:
        return math.exp(-rate + k * math.log(rate) - math.lgamma(k + 1))

    def _build_grid(self) -> list:
        n = self.max_goals + 1
        grid = [[self._poisson_pmf(h, self.lam) * self._poisson_pmf(a, self.mu)
                 * dc_tau(h, a, self.lam, self.mu, self.rho)
                 for a in range(n)] for h in range(n)]
        total = sum(sum(row) for row in grid)
        return [[cell / total for cell in row] for row in grid]

    def score_prob(self, home_goals: int, away_goals: int) -> float:
        """P(placar exato), renormalizada na grade truncada."""
        if not (0 <= home_goals <= self.max_goals and 0 <= away_goals <= self.max_goals):
            raise ValueError(f"placar fora da grade 0..{self.max_goals}")
        return self._grid[home_goals][away_goals]

    def grid(self) -> list:
        """Cópia da matriz completa: grid()[h][a] = P(h x a). Soma 1."""
        return [row[:] for row in self._grid]

    def outcome_probs(self) -> dict:
        """Agrega a grade no 1X2: {"home", "draw", "away"} — ordinal, pronto
        para `predictor_core.rps` com classes [home, draw, away]."""
        home = draw = away = 0.0
        for h in range(self.max_goals + 1):
            for a in range(self.max_goals + 1):
                p = self._grid[h][a]
                if h > a:
                    home += p
                elif h == a:
                    draw += p
                else:
                    away += p
        return {"home": home, "draw": draw, "away": away}
