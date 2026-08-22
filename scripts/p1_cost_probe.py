"""P1 — sonda de custo e exatidão de `fit_dixon_coles_parameters`.

Responde, SEM tocar em `data/matches.db`, a pergunta do P1 do Roadmap: quanto
custa o objetivo atual, e uma reformulação vetorizada muda a numérica?

Dados sintéticos com a forma do Brasileirão (20 times). Duas verificações:

1. **Identidade do normalizador.** `_build_grid` soma (max_goals+1)² células
   para normalizar; como τ ≡ 1 fora das 4 células magras, a soma dupla colapsa
   em `F(M|λ)·F(M|μ) + Σ_{4 magras} P·P·(τ−1)`. Isso é identidade algébrica,
   não aproximação — a sonda mede o erro relativo contra a grade completa.
2. **Concordância e custo.** Objetivo atual (laço Python, grade por jogo) vs.
   vetorizado (normalizador fechado, numpy), nos mesmos parâmetros, e o fit
   completo dos dois lados.

Nada aqui altera `src/dixon_coles.py`: é medição para instruir a decisão.

Uso:  python scripts/p1_cost_probe.py
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dixon_coles import (  # noqa: E402
    DixonColesMatrix,
    dc_tau,
    fit_dixon_coles_parameters,
    time_decay_weight,
)

MAX_GOALS = 10
XI = math.log(2) / 360.0
PENALTY = 100.0


def _grid_total_loop(lam: float, mu: float, rho: float) -> float:
    """Normalizador como `_build_grid` o calcula hoje: (MAX_GOALS+1)² células."""
    pmf = DixonColesMatrix._poisson_pmf
    return sum(
        pmf(h, lam) * pmf(a, mu) * dc_tau(h, a, lam, mu, rho)
        for h in range(MAX_GOALS + 1)
        for a in range(MAX_GOALS + 1)
    )


def _grid_total_closed(lam: float, mu: float, rho: float) -> float:
    """O mesmo normalizador em forma fechada, O(1) — τ ≡ 1 fora das 4 magras."""
    pmf = DixonColesMatrix._poisson_pmf
    corr = (
        pmf(0, lam) * pmf(0, mu) * (-lam * mu * rho)
        + pmf(0, lam) * pmf(1, mu) * (lam * rho)
        + pmf(1, lam) * pmf(0, mu) * (mu * rho)
        + pmf(1, lam) * pmf(1, mu) * (-rho)
    )
    return float(poisson.cdf(MAX_GOALS, lam) * poisson.cdf(MAX_GOALS, mu) + corr)


def check_normalizer(trials: int = 3000, seed: int = 7) -> float:
    rng = random.Random(seed)
    worst = 0.0
    for _ in range(trials):
        lam, mu = rng.uniform(0.4, 3.5), rng.uniform(0.4, 3.0)
        lo, hi = DixonColesMatrix.valid_rho_bounds(lam, mu)
        rho = rng.uniform(max(lo + 1e-6, -0.35), min(hi - 1e-6, 0.35))
        loop, closed = _grid_total_loop(lam, mu, rho), _grid_total_closed(lam, mu, rho)
        worst = max(worst, abs(loop - closed) / abs(loop))
    return worst


def make_games(n_games: int, n_teams: int = 20, seed: int = 3) -> list[dict]:
    r = random.Random(seed)
    gen = np.random.default_rng(seed)
    teams = [f"T{i:02d}" for i in range(n_teams)]
    atk = {t: math.exp(r.gauss(0, 0.25)) for t in teams}
    dfn = {t: math.exp(r.gauss(0, 0.20)) for t in teams}
    rows = []
    for i in range(n_games):
        home, away = r.sample(teams, 2)
        lam, mu = atk[home] * dfn[away] * 1.3, atk[away] * dfn[home]
        rows.append(
            {
                "home": home,
                "away": away,
                "home_goals": int(min(gen.poisson(lam), MAX_GOALS)),
                "away_goals": int(min(gen.poisson(mu), MAX_GOALS)),
                "days_ago": float(n_games - i) * 3.5,
            }
        )
    return rows


def _team_index(rows: list[dict]) -> tuple[list[str], dict[str, int]]:
    teams = sorted({r["home"] for r in rows} | {r["away"] for r in rows})
    return teams, {t: i for i, t in enumerate(teams)}


def objective_current(rows: list[dict]):
    """Cópia fiel do laço de `fit_dixon_coles_parameters`, para comparação."""
    teams, idx = _team_index(rows)
    n = len(teams)
    weights = [time_decay_weight(float(r["days_ago"]), XI) for r in rows]

    def obj(theta: np.ndarray) -> float:
        log_a, log_b = theta[:n], theta[n : 2 * n]
        log_gamma, rho = theta[2 * n], theta[2 * n + 1]
        total = 0.0
        for r, w in zip(rows, weights):
            lam = math.exp(log_a[idx[r["home"]]] + log_b[idx[r["away"]]] + log_gamma)
            mu = math.exp(log_a[idx[r["away"]]] + log_b[idx[r["home"]]])
            lo, hi = DixonColesMatrix.valid_rho_bounds(lam, mu)
            if not (lo < rho < hi):
                return float("inf")
            m = DixonColesMatrix(lam, mu, rho, max_goals=MAX_GOALS)
            total += -w * math.log(
                m.score_prob(min(int(r["home_goals"]), MAX_GOALS), min(int(r["away_goals"]), MAX_GOALS))
            )
        return total + PENALTY * float(np.mean(log_a)) ** 2

    return obj, n, teams


def objective_vectorized(rows: list[dict]):
    """Mesma matemática, sem construir grade: normalizador fechado + numpy."""
    teams, idx = _team_index(rows)
    n = len(teams)
    hi_i = np.array([idx[r["home"]] for r in rows])
    ai_i = np.array([idx[r["away"]] for r in rows])
    hg = np.minimum(np.array([int(r["home_goals"]) for r in rows]), MAX_GOALS)
    ag = np.minimum(np.array([int(r["away_goals"]) for r in rows]), MAX_GOALS)
    w = np.exp(-XI * np.array([float(r["days_ago"]) for r in rows]))
    lg_h, lg_a = gammaln(hg + 1.0), gammaln(ag + 1.0)

    def obj(theta: np.ndarray) -> float:
        log_a, log_b = theta[:n], theta[n : 2 * n]
        log_gamma, rho = theta[2 * n], theta[2 * n + 1]
        log_lam = log_a[hi_i] + log_b[ai_i] + log_gamma
        log_mu = log_a[ai_i] + log_b[hi_i]
        lam, mu = np.exp(log_lam), np.exp(log_mu)
        lo = np.maximum(-1.0 / lam, -1.0 / mu)
        hi = np.minimum(1.0 / (lam * mu), 1.0)
        if not (np.all(lo < rho) and np.all(rho < hi)):
            return float("inf")
        log_pmf = (-lam + hg * log_lam - lg_h) + (-mu + ag * log_mu - lg_a)
        tau = np.where(
            (hg == 0) & (ag == 0),
            1.0 - lam * mu * rho,
            np.where(
                (hg == 0) & (ag == 1),
                1.0 + lam * rho,
                np.where((hg == 1) & (ag == 0), 1.0 + mu * rho, np.where((hg == 1) & (ag == 1), 1.0 - rho, 1.0)),
            ),
        )
        p0l, p1l = np.exp(-lam), lam * np.exp(-lam)
        p0m, p1m = np.exp(-mu), mu * np.exp(-mu)
        corr = p0l * p0m * (-lam * mu * rho) + p0l * p1m * (lam * rho) + p1l * p0m * (mu * rho) + p1l * p1m * (-rho)
        total = poisson.cdf(MAX_GOALS, lam) * poisson.cdf(MAX_GOALS, mu) + corr
        if np.any(tau <= 0) or np.any(total <= 0):
            return float("inf")
        nll = -float((w * (log_pmf + np.log(tau) - np.log(total))).sum())
        return nll + PENALTY * float(np.mean(log_a)) ** 2

    return obj, n, teams


def _probe_point(n_params: int, seed: int) -> np.ndarray:
    r = random.Random(seed)
    n = (n_params - 2) // 2
    return np.array([r.gauss(0, 0.15) for _ in range(2 * n)] + [math.log(1.3), r.uniform(-0.10, 0.05)])


def main() -> int:
    print(f"[1] normalizador fechado vs grade completa: erro relativo máx = {check_normalizer():.3e}")

    for n_games in (380, 1000):
        rows = make_games(n_games)
        cur, n, _ = objective_current(rows)
        vec, _, _ = objective_vectorized(rows)
        n_params = 2 * n + 2
        diffs = []
        for k in range(5):
            th = _probe_point(n_params, 11 + k)
            a, b = cur(th), vec(th)
            diffs.append(abs(a - b) / abs(a))
        base = _probe_point(n_params, 0)
        t0 = time.perf_counter()
        for _ in range(3):
            cur(base)
        t_cur = (time.perf_counter() - t0) / 3
        t0 = time.perf_counter()
        for _ in range(3):
            vec(base)
        t_vec = (time.perf_counter() - t0) / 3
        evals = n_params + 1  # ~1 gradiente por diferenças finitas
        print(f"[2] n_games={n_games} n_params={n_params}: erro relativo máx do objetivo = {max(diffs):.3e}")
        print(
            f"    1 avaliação: atual {t_cur * 1000:8.2f} ms | vetorizado {t_vec * 1000:7.3f} ms | {t_cur / t_vec:6.0f}x"
        )
        print(f"    1 gradiente ({evals} avaliações): atual {t_cur * evals:7.2f} s | vetorizado {t_vec * evals:6.3f} s")

    rows = make_games(380)
    t0 = time.perf_counter()
    fit_cur = fit_dixon_coles_parameters(rows, XI)
    t_cur = time.perf_counter() - t0

    obj, n, teams = objective_vectorized(rows)
    theta0 = np.zeros(2 * n + 2)
    theta0[2 * n] = math.log(1.3)
    bounds = [(None, None)] * (2 * n + 1) + [(-0.35, 0.35)]
    t0 = time.perf_counter()
    res = minimize(obj, theta0, method="L-BFGS-B", bounds=bounds)
    t_vec = time.perf_counter() - t0

    atk_v = {t: math.exp(res.x[i]) for i, t in enumerate(teams)}
    def_v = {t: math.exp(res.x[n + i]) for i, t in enumerate(teams)}
    gamma_v, rho_v = math.exp(res.x[2 * n]), float(res.x[2 * n + 1])

    print(f"[3] fit completo: atual {t_cur:7.2f} s | vetorizado {t_vec:6.3f} s | {t_cur / t_vec:.0f}x")
    print(f"    wnll  {fit_cur['wnll']:.9f} vs {float(res.fun):.9f}  (Δ {abs(fit_cur['wnll'] - float(res.fun)):.2e})")
    print(f"    rho   {fit_cur['rho']:+.9f} vs {rho_v:+.9f}  (Δ {abs(fit_cur['rho'] - rho_v):.2e})")
    d_gamma = abs(fit_cur["home_advantage"] - gamma_v)
    print(f"    gamma {fit_cur['home_advantage']:.9f} vs {gamma_v:.9f}  (Δ {d_gamma:.2e})")
    print(f"    convergiu: atual {fit_cur['converged']} | vetorizado {bool(res.success)}")
    print(
        f"    máx |Δ| attack {max(abs(fit_cur['attack'][t] - atk_v[t]) for t in teams):.3e}"
        f" | defense {max(abs(fit_cur['defense'][t] - def_v[t]) for t in teams):.3e}"
    )

    worst = 0.0
    pairs = 0
    for t1 in teams[:8]:
        for t2 in teams[:8]:
            if t1 == t2:
                continue
            pairs += 1
            o_cur = DixonColesMatrix(
                fit_cur["attack"][t1] * fit_cur["defense"][t2] * fit_cur["home_advantage"],
                fit_cur["attack"][t2] * fit_cur["defense"][t1],
                fit_cur["rho"],
            ).outcome_probs()
            o_vec = DixonColesMatrix(atk_v[t1] * def_v[t2] * gamma_v, atk_v[t2] * def_v[t1], rho_v).outcome_probs()
            worst = max(worst, max(abs(o_cur[k] - o_vec[k]) for k in o_cur))
    print(f"    máx |Δ| em P(home/draw/away) sobre {pairs} confrontos = {worst:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
