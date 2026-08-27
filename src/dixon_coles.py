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
from typing import Any

__all__ = ["dc_tau", "time_decay_weight", "DixonColesMatrix", "fit_dixon_coles_parameters"]


def dc_tau(home_goals: int, away_goals: int, lam: float, mu: float, rho: float) -> float:
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
            f"lam={lam}, mu={mu} — rho fora da faixa válida para estas médias"
        )
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
            f"days_ago negativo ({days_ago}) — partida no futuro do corte; isso é lookahead do chamador, não decaimento"
        )
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

    def __init__(self, lam: float, mu: float, rho: float = 0.0, max_goals: int = 10):
        if lam <= 0 or mu <= 0:
            raise ValueError(f"lam e mu devem ser > 0 (lam={lam}, mu={mu})")
        if max_goals < 1:
            raise ValueError("max_goals >= 1")
        lo, hi = self.valid_rho_bounds(lam, mu)
        if not (lo < rho < hi):
            raise ValueError(
                f"rho={rho} fora da faixa válida ({lo:.4g}, {hi:.4g}) para lam={lam}, mu={mu} — tau ficaria <= 0"
            )
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
        grid = [
            [
                self._poisson_pmf(h, self.lam)
                * self._poisson_pmf(a, self.mu)
                * dc_tau(h, a, self.lam, self.mu, self.rho)
                for a in range(n)
            ]
            for h in range(n)
        ]
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


# ---------------------------------------------------------------------------
# H4 — Otimizador MLE (roadmap de setembro). scipy é importado LAZY dentro da
# função (padrão A do core): o módulo continua "Python puro" para quem só usa
# a matemática de correlação acima.
# ---------------------------------------------------------------------------


def fit_dixon_coles_parameters(
    games: Any,
    xi_fixed: float,
    *,
    max_goals: int = 10,
    rho_bounds: tuple[float, float] = (-0.35, 0.35),
    mean_attack_penalty: float = 100.0,
) -> dict:
    """Estima (α por time, β por time, γ, ρ) por MV pesada no tempo (WNLL).

    `games`: DataFrame OU lista de dicts, cada jogo com as chaves/colunas
      home, away (str), home_goals, away_goals (int), days_ago (float,
      relativo ao corte do treino — 0 = jogo mais recente).
    `xi_fixed`: decaimento temporal ξ FIXO (hiperparâmetro do domínio, não é
      otimizado aqui — otimizar ξ dentro do fit contaminaria a seleção com o
      próprio conjunto de avaliação; escolha-o por walk-forward externo).

    Modelo: λ = α_casa · β_fora · γ  e  μ = α_fora · β_casa, com o placar
    tirado da DixonColesMatrix (Poisson×Poisson · τ(ρ), renormalizada).
    Objetivo: Σ_i φ(Δt_i) · [-log P_i(placar_i)] + penalidade de identificação
    `mean_attack_penalty · mean(log α)²` (sem ela, multiplicar todo α por c e
    dividir todo β por c dá o MESMO ajuste — colinearidade estrita).

    Otimização: scipy L-BFGS-B sobre (log α, log β, log γ, ρ) — o log garante
    α, β, γ > 0 sem bounds ativos; ρ tem bounds explícitos e, se um par
    (λ, μ) tornar ρ inválido pela Eq. 4.3, o objetivo devolve +inf (o
    otimizador recua sozinho).

    Retorna {"attack": {time: α}, "defense": {time: β}, "home_advantage": γ,
    "rho": ρ, "xi": ξ, "converged": bool, "wnll": float}."""
    import numpy as np
    from scipy.optimize import minimize

    rows: list[dict] = games.to_dict("records") if hasattr(games, "to_dict") else list(games)
    if not rows:
        raise ValueError("fit_dixon_coles_parameters: sem jogos")
    teams: list[str] = sorted({r["home"] for r in rows} | {r["away"] for r in rows})
    if len(teams) < 2:
        raise ValueError("fit exige >= 2 times distintos")
    idx: dict[str, int] = {t: i for i, t in enumerate(teams)}
    n = len(teams)

    weights = [time_decay_weight(float(r["days_ago"]), xi_fixed) for r in rows]

    def objective(theta: np.ndarray) -> float:
        log_a, log_b = theta[:n], theta[n : 2 * n]
        log_gamma, rho = theta[2 * n], theta[2 * n + 1]
        total = 0.0
        for r, w in zip(rows, weights):
            lam = math.exp(log_a[idx[r["home"]]] + log_b[idx[r["away"]]] + log_gamma)
            mu = math.exp(log_a[idx[r["away"]]] + log_b[idx[r["home"]]])
            lo, hi = DixonColesMatrix.valid_rho_bounds(lam, mu)
            if not (lo < rho < hi):
                return float("inf")
            h = int(r["home_goals"])
            a = int(r["away_goals"])
            if h < 0 or a < 0:
                return float("inf")
            probability = (
                DixonColesMatrix._poisson_pmf(h, lam)
                * DixonColesMatrix._poisson_pmf(a, mu)
                * dc_tau(h, a, lam, mu, rho)
            )
            total += -w * math.log(probability)
        total += mean_attack_penalty * float(np.mean(log_a)) ** 2
        return total

    theta0 = np.zeros(2 * n + 2)
    theta0[2 * n] = math.log(1.3)  # chute inicial: vantagem de casa típica
    bounds = [(None, None)] * (2 * n + 1) + [(rho_bounds[0], rho_bounds[1])]
    res = minimize(objective, theta0, method="L-BFGS-B", bounds=bounds)

    log_a, log_b = res.x[:n], res.x[n : 2 * n]
    return {
        "attack": {t: float(math.exp(log_a[idx[t]])) for t in teams},
        "defense": {t: float(math.exp(log_b[idx[t]])) for t in teams},
        "home_advantage": float(math.exp(res.x[2 * n])),
        "rho": float(res.x[2 * n + 1]),
        "xi": xi_fixed,
        "converged": bool(res.success),
        "wnll": float(res.fun),
    }
