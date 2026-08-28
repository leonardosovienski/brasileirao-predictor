"""Motor de gols: Binomial Negativa (overdispersion) + correção Dixon-Coles.

ZONA 3 — Kernel Purista (PROMPT 5)
  • Zero dependências de banco de dados ou arquivos de configuração neste módulo.
  • API interna estrita: predict_match(elo_a, elo_b, params, **kwargs)
  • params pode ser tupla (a, b, alpha, rho) OU dict com chave "theta" para VORP.
  • Link function com injeção de perturbação θ·Δvorp:
      λ_a = exp(a + b·elo_diff/400 + θ·delta_vorp_a)
      λ_b = exp(a − b·elo_diff/400 + θ·delta_vorp_b)
  • Modo determinístico (seeded) disponível via np.random.default_rng(seed).
"""

import math
import warnings
from datetime import date
from numbers import Integral, Real

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import nbinom


def exponential_recency_weights(match_dates, asof, half_life_days):
    """Return exponential weights with the configured half-life.

    This is the single wiring point shared by serving, cache refresh and the
    canonical backtests. Future observations fail closed instead of receiving
    a weight greater than one.
    """
    if half_life_days is None:
        return [1.0] * len(match_dates)
    half_life = float(half_life_days)
    if not math.isfinite(half_life) or half_life <= 0:
        raise ValueError("model.goal_half_life_days must be finite and > 0")
    reference = date.fromisoformat(str(asof)[:10])
    weights = []
    for value in match_dates:
        age_days = (reference - date.fromisoformat(str(value)[:10])).days
        if age_days < 0:
            raise ValueError("recency weighting received a match after asof")
        weights.append(math.exp(-math.log(2.0) * age_days / half_life))
    return weights


# Tipo dos hiperparâmetros: tupla legada (a, b, alpha, rho) ou dict estendido
type Params = tuple[float, float, float, float] | tuple[float, float, float, float, float] | dict[str, float]


class ModelIntegrityError(ValueError):
    """Training data violates the goal-model input contract."""


class OptimizationFailedError(RuntimeError):
    """All configured numerical optimization attempts failed to converge."""


def _validate_goal_model_inputs(history, delta_xg=None, sample_weights=None) -> None:
    """Validate non-empty training inputs before NumPy or SciPy can coerce them.

    The canonical history item is ``(elo_diff, home_goals, away_goals)``.
    Goal counts must be actual integral values (booleans and integral-looking
    floats are rejected) so corrupt schemas cannot silently reach the solver.
    """
    for index, item in enumerate(history):
        if isinstance(item, (str, bytes, dict)) or not hasattr(item, "__len__") or len(item) != 3:
            raise ModelIntegrityError(f"history[{index}] must be a three-item (elo_diff, home_goals, away_goals) tuple")
        elo_diff, home_goals, away_goals = item
        if isinstance(elo_diff, bool) or not isinstance(elo_diff, Real) or not math.isfinite(float(elo_diff)):
            raise ModelIntegrityError(f"history[{index}].elo_diff must be a finite real number")
        for field, value in (("home_goals", home_goals), ("away_goals", away_goals)):
            if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
                raise ModelIntegrityError(f"history[{index}].{field} must be a non-negative integer")

    if sample_weights is not None:
        try:
            weights = np.asarray(sample_weights, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ModelIntegrityError("sample_weights must be numeric") from exc
        if weights.shape != (len(history),) or not np.isfinite(weights).all() or np.any(weights <= 0):
            raise ModelIntegrityError("sample_weights must be finite, positive and match history length")

    if delta_xg is not None:
        try:
            values = np.asarray(delta_xg, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ModelIntegrityError("delta_xg must be numeric") from exc
        if values.shape != (len(history),) or not np.isfinite(values).all():
            raise ModelIntegrityError("delta_xg must be finite and match history length")


def _nb_logpmf(k, mu, alpha):
    """log P(k) da NB em parametrização média-dispersão: Var = mu + alpha*mu^2.
    alpha -> 0 recupera o Poisson."""
    r = 1.0 / alpha
    return gammaln(k + r) - gammaln(r) - gammaln(k + 1.0) + r * np.log(r / (r + mu)) + k * np.log(mu / (r + mu))


def _tau(hs, as_, lam, mu, rho):
    """Função de ajuste de Dixon-Coles nas quatro células de placar baixo."""
    t = np.ones_like(lam, dtype=float)
    t = np.where((hs == 0) & (as_ == 0), 1.0 - lam * mu * rho, t)
    t = np.where((hs == 0) & (as_ == 1), 1.0 + lam * rho, t)
    t = np.where((hs == 1) & (as_ == 0), 1.0 + mu * rho, t)
    t = np.where((hs == 1) & (as_ == 1), 1.0 - rho, t)
    return t


def _nb_low_score_probabilities(mu, alpha):
    """Return NB probabilities for 0 and 1 goals in mean/dispersion form."""
    r = 1.0 / alpha
    q = r / (r + mu)
    p0 = np.power(q, r)
    p1 = p0 * r * (1.0 - q)
    return p0, p1


def _dc_normalizer_nb(lam, mu, alpha, rho):
    """Mass of NB x NB after the four Dixon-Coles corrections."""
    h0, h1 = _nb_low_score_probabilities(lam, alpha)
    a0, a1 = _nb_low_score_probabilities(mu, alpha)
    return 1.0 + rho * (-lam * mu * h0 * a0 + lam * h0 * a1 + mu * h1 * a0 - h1 * a1)


def _all_dc_factors_positive(lam, mu, rho):
    """Whether all four corrected cells are strictly positive."""
    return (1.0 - lam * mu * rho > 0.0) & (1.0 + lam * rho > 0.0) & (1.0 + mu * rho > 0.0) & (1.0 - rho > 0.0)


def valid_dc_rho_bounds(lam: float, mu: float) -> tuple[float, float]:
    """Open rho interval that keeps all four Dixon-Coles cells positive."""
    return max(-1.0 / lam, -1.0 / mu), min(1.0 / (lam * mu), 1.0)


def clamp_dc_rho(rho: float, lam: float, mu: float, margin: float = 1e-9) -> float:
    """Clamp a global fitted rho for a new matchup and expose the used value."""
    lo, hi = valid_dc_rho_bounds(lam, mu)
    return min(max(rho, lo + margin), hi - margin)


def fit_goal_model(history, delta_xg=None, sample_weights=None):
    """Estima (a, b, alpha, rho, [theta_xg]) por maxima verossimilhanca.
    Se delta_xg for fornecido (lista com um valor por jogo), theta_xg e'
    estimado como 5o parametro. ``sample_weights`` pondera a contribuição de
    cada jogo à log-verossimilhança (peso 1 preserva o comportamento legado).
    Retorna tupla de 4 (sem delta_xg) ou 5 (com delta_xg).
    """
    history = list(history)
    if not history:
        if sample_weights is not None and len(sample_weights) != 0:
            raise ModelIntegrityError("sample_weights must match empty history")
        if delta_xg is not None and len(delta_xg) != 0:
            raise ModelIntegrityError("delta_xg must match empty history")
        cold_start = (0.0, 0.3, 1e-4, 0.0)
        return (*cold_start, 0.0) if delta_xg is not None else cold_start

    _validate_goal_model_inputs(history, delta_xg=delta_xg, sample_weights=sample_weights)

    diffs = np.array([h[0] for h in history], dtype=float) / 400.0
    hs = np.array([h[1] for h in history], dtype=float)
    as_ = np.array([h[2] for h in history], dtype=float)
    if sample_weights is None:
        weights = np.ones(len(diffs), dtype=float)
    else:
        weights = np.asarray(sample_weights, dtype=float)
    base = math.log(max(float(np.average(np.r_[hs, as_], weights=np.r_[weights, weights])), 1e-3))

    has_xg = delta_xg is not None
    if has_xg:
        dxg = np.array(delta_xg, dtype=float)
    else:
        dxg = np.zeros(len(diffs), dtype=float)

    rho_scale = 0.4

    def negll(theta):
        if len(theta) == 5:
            a, b, log_alpha, rho_raw, theta_xg = theta
        else:
            a, b, log_alpha, rho_raw = theta
            theta_xg = 0.0
        rho = rho_scale * math.tanh(rho_raw)

        alpha = math.exp(log_alpha)
        lam = np.exp(a + b * diffs)
        mu = np.exp(a - b * diffs)

        lam = lam * np.exp(theta_xg * dxg)
        mu = mu * np.exp(-theta_xg * dxg)

        tau = _tau(hs, as_, lam, mu, rho)
        if np.any(tau <= 1e-12) or not np.all(_all_dc_factors_positive(lam, mu, rho)):
            return 1e12
        normalizer = _dc_normalizer_nb(lam, mu, alpha, rho)
        if np.any(normalizer <= 1e-12) or not np.isfinite(normalizer).all():
            return 1e12
        ll = _nb_logpmf(hs, lam, alpha) + _nb_logpmf(as_, mu, alpha) + np.log(tau) - np.log(normalizer)
        if not np.isfinite(ll).all():
            return 1e12
        return -float(np.dot(weights, ll))

    if has_xg:
        x0 = [base, 0.3, math.log(0.1), math.atanh(-0.03 / rho_scale), 0.5]
        bounds = [(-3, 3), (-1, 4), (math.log(1e-4), math.log(3)), (None, None), (-5, 5)]
    else:
        x0 = [base, 0.3, math.log(0.1), math.atanh(-0.03 / rho_scale)]
        bounds = [(-3, 3), (-1, 4), (math.log(1e-4), math.log(3)), (None, None)]

    try:
        res = minimize(negll, x0, method="L-BFGS-B", bounds=bounds)
        if not res.success:
            retry = minimize(
                negll,
                res.x if np.isfinite(res.x).all() else x0,
                method="Powell",
                bounds=bounds,
                options={"maxiter": 2000, "xtol": 1e-8, "ftol": 1e-10},
            )
            if retry.success or retry.fun < res.fun:
                res = retry
    except (ArithmeticError, FloatingPointError, OverflowError, ValueError) as exc:
        raise OptimizationFailedError(f"goal-model optimizer raised {type(exc).__name__}: {exc}") from exc

    if not res.success:
        raise OptimizationFailedError(f"goal-model optimizer did not converge: {res.message}")
    if not np.isfinite(res.x).all() or not math.isfinite(float(res.fun)) or res.fun >= 1e11:
        raise OptimizationFailedError("goal-model optimizer returned an invalid solution")

    if len(res.x) == 5:
        a, b, log_alpha, rho_raw, theta_xg = res.x
    else:
        a, b, log_alpha, rho_raw = res.x
        theta_xg = 0.0
    rho = rho_scale * math.tanh(rho_raw)
    # Auditoria P10: parâmetros cravados num bound indicam dado mal-formado ou
    # modelo mal-especificado. A integridade estrutural já falha antes do solver;
    # este warning preserva o diagnóstico de uma solução numericamente limítrofe.
    _names = ("a", "b", "log_alpha", "rho_raw", "theta_xg")
    for name, val, (lo, hi) in zip(_names, res.x, bounds):
        if lo is not None and hi is not None and min(abs(val - lo), abs(val - hi)) < 1e-6:
            if name == "log_alpha" and abs(val - lo) < 1e-6:
                continue
            warnings.warn(
                f"fit_goal_model: parametro {name}={val:.4f} cravado no bound "
                f"[{lo}, {hi}] — verifique o formato do history (diff, hs, as)",
                RuntimeWarning,
                stacklevel=2,
            )
    if has_xg:
        return (float(a), float(b), float(math.exp(log_alpha)), float(rho), float(theta_xg))
    return (float(a), float(b), float(math.exp(log_alpha)), float(rho))


def _unpack_params(params: Params) -> tuple[float, float, float, float, float]:
    """Extrai (a, b, alpha, rho, theta) de tupla legada ou dict estendido.
    Aceita tupla de 4 (theta=0) ou tupla de 5 (theta no 5o elemento)."""
    if isinstance(params, dict):
        return (params["a"], params["b"], params["alpha"], params["rho"], params.get("theta", 0.0))
    if len(params) >= 5:
        return (params[0], params[1], params[2], params[3], params[4])
    return (params[0], params[1], params[2], params[3], 0.0)


def predict_match(
    elo_a: float,
    elo_b: float,
    params: Params,
    home_adv: float = 0.0,
    delta_vorp_a: float = 0.0,
    delta_vorp_b: float = 0.0,
    delta_xg: float = 0.0,
    max_goals: int = 12,
    seed: int | None = None,
) -> dict:
    """Previsão completa de uma partida.

    Link function com injeção de VORP e delta_xg (θ=0 → comportamento original):
        λ_a = exp(a + b·elo_diff/400 + θ·(delta_vorp_a + delta_xg))
        λ_b = exp(a − b·elo_diff/400 + θ·(delta_vorp_b − delta_xg))

    seed: se fornecido, cria um RNG determinístico para amostragem interna —
          torna o resultado reproduzível em testes unitários.
    """
    a, b, alpha, rho, theta = _unpack_params(params)
    diff = (elo_a + home_adv - elo_b) / 400.0
    lam_a = math.exp(a + b * diff + theta * (delta_vorp_a + delta_xg))
    lam_b = math.exp(a - b * diff + theta * (delta_vorp_b - delta_xg))

    grid = _score_grid(lam_a, lam_b, alpha, rho, max_goals)
    return {
        "lambda_a": lam_a,
        "lambda_b": lam_b,
        "total_goals": lam_a + lam_b,
        **_grid_stats(grid, max_goals),
    }


def _score_grid(lam_a, lam_b, alpha, rho, max_goals):
    """Grid de probabilidade P(gols_a=i, gols_b=j) — NB + correção Dixon-Coles
    nas quatro células de placar baixo. Fatorado de `predict_match` pra ser
    reaproveitado por `predict_remaining` com lambdas escalados."""
    values = (lam_a, lam_b, alpha, rho)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("lam_a, lam_b, alpha and rho must be finite")
    if lam_a <= 0 or lam_b <= 0 or alpha <= 0:
        raise ValueError("lam_a, lam_b and alpha must be > 0")
    if not isinstance(max_goals, int) or max_goals < 1:
        raise ValueError("max_goals must be an integer >= 1")
    if not bool(_all_dc_factors_positive(lam_a, lam_b, rho)):
        raise ValueError("rho produces a non-positive Dixon-Coles cell")

    k = np.arange(max_goals + 1)
    r = 1.0 / max(alpha, 1e-9)
    pa = nbinom.pmf(k, r, r / (r + lam_a))
    pb = nbinom.pmf(k, r, r / (r + lam_b))
    grid = np.outer(pa, pb)

    grid[0, 0] *= 1.0 - lam_a * lam_b * rho
    grid[0, 1] *= 1.0 + lam_a * rho
    grid[1, 0] *= 1.0 + lam_b * rho
    grid[1, 1] *= 1.0 - rho
    total = float(grid.sum())
    if not math.isfinite(total) or total <= 0.0 or np.any(grid < 0.0):
        raise ValueError("invalid score-grid mass")
    grid /= total
    return grid


def _grid_stats(grid, max_goals):
    """p_win/draw/loss, over/btts e top-5 placares a partir de um grid já
    pronto — mesma leitura pra `predict_match` (placar final) e
    `predict_remaining` (gols do tempo restante, não placar final)."""
    k = np.arange(max_goals + 1)
    p_win = float(np.tril(grid, -1).sum())
    p_draw = float(np.trace(grid))
    p_loss = float(np.triu(grid, 1).sum())

    i_idx = k.reshape(-1, 1)
    j_idx = k.reshape(1, -1)
    totals = i_idx + j_idx
    over = {t: float(grid[totals > t].sum()) for t in (1.5, 2.5, 3.5)}
    btts = float(grid[(i_idx >= 1) & (j_idx >= 1)].sum())

    flat = [((i, j), float(grid[i, j])) for i in k for j in k]
    top = sorted(flat, key=lambda t: -t[1])[:5]
    probs = {"home": p_win, "draw": p_draw, "away": p_loss}
    ranked = sorted(probs, key=lambda outcome: probs[outcome], reverse=True)
    ordered = sorted(probs.values(), reverse=True)
    modal_score, modal_probability = top[0]
    diagonal = {f"{i}-{i}": float(grid[i, i]) for i in range(max_goals + 1)}
    entropy = -sum(p * math.log(p) for p in probs.values() if p > 0)
    draw_diagnostics = {
        "p_draw_1x2": p_draw,
        "diagonal_score_probs": diagonal,
        "modal_score": [int(modal_score[0]), int(modal_score[1])],
        "modal_score_is_draw": bool(modal_score[0] == modal_score[1]),
        "p_modal_score": modal_probability,
        "draw_is_1x2_argmax": ranked[0] == "draw",
        "draw_rank_1x2": ranked.index("draw") + 1,
        "top_1x2_gap": ordered[0] - ordered[1],
        "side_probability_gap": abs(p_win - p_loss),
        "draw_vs_best_side_gap": p_draw - max(p_win, p_loss),
        "entropy_1x2_nats": entropy,
        "diagonal_concentration": max(diagonal.values()) / p_draw if p_draw > 0 else None,
        # Não existe threshold validado para converter estes diagnósticos
        # em escolha. O argmax continua sendo apenas um resumo diagnóstico.
        "categorical_policy": "ARGMAX_DIAGNOSTIC_ONLY",
        "robust_choice": None,
    }

    return {
        "p_win": p_win,
        "p_draw": p_draw,
        "p_loss": p_loss,
        "over": over,
        "btts": btts,
        "top_scores": top,
        "draw_diagnostics": draw_diagnostics,
        "grid": grid,  # exposto para o simulador amostrar placares
    }


def predict_remaining(
    elo_a: float,
    elo_b: float,
    params: Params,
    home_adv: float = 0.0,
    fraction: float = 0.5,
    max_goals: int = 12,
) -> dict:
    """Distribuição de gols só do tempo RESTANTE de um jogo em andamento —
    mesma link function do `predict_match`, com os λ pré-jogo escalados por
    `fraction` (0.5 = um tempo inteiro de 45min).

    HIPÓTESE NÃO CALIBRADA: assume taxa de gol constante ao longo dos 90min
    (mesma simplificação que Dixon-Coles original usa). Sem dado de minuto
    de gol no projeto, não dá pra checar se o 2o tempo tem taxa maior — na
    prática, times cansam e fazem mais gol depois dos 60min, então isto
    provavelmente subestima o tempo restante. Sem CLV validado (não existe
    mercado ao vivo no backtest) — ver docs/HYPERPARAMETERS.md.

    Os p_win/p_draw/p_loss e top_scores devolvidos são do TEMPO RESTANTE,
    não do placar final — some ao placar atual pra projetar o jogo inteiro."""
    if not math.isfinite(fraction) or not 0.0 <= fraction <= 1.0:
        raise ValueError("fraction must be finite and between 0 and 1")
    a, b, alpha, rho, _theta = _unpack_params(params)
    diff = (elo_a + home_adv - elo_b) / 400.0
    lam_a = math.exp(a + b * diff) * fraction
    lam_b = math.exp(a - b * diff) * fraction

    if fraction == 0.0:
        grid = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
        grid[0, 0] = 1.0
    else:
        grid = _score_grid(lam_a, lam_b, alpha, rho, max_goals)
    return {
        "lambda_a": lam_a,
        "lambda_b": lam_b,
        "total_goals": lam_a + lam_b,
        **_grid_stats(grid, max_goals),
    }
