"""Modelo ataque/defesa por time estimado em xG + ensemble com o baseline.

Origem: simulação walk-forward 2025+2026 (docs/SIMULACAO_2025_2026.md).
O ensemble 50/50 (baseline Elo+cosh × este modelo) reduziu o Brier 1X2 em
−0,0073 com IC95 fechado [−0,0122, −0,0019], sem degradar OU2.5.

Desenho em duas etapas (isola o que cada dado faz bem):
  1. forças atk/def por time via Poisson ponderado no tempo sobre o alvo
     misto k* = w_xg·xG + (1−w_xg)·gols (menos ruído que o gol puro);
  2. com as forças congeladas, α (NB) e ρ (Dixon-Coles) ajustados nos
     GOLS INTEIROS reais.

Serving: hook único `maybe_blend` — desligado (`ensemble_xg.enabled: false`)
devolve o resultado do baseline intocado, byte a byte. Hiperparâmetros
CONGELADOS pela validação interna em 2024-H2 (não recalibrar sem novo
protocolo anti-snooping).
"""

import math
import sys
from datetime import date

import numpy as np
from scipy.optimize import minimize

from .model import _grid_stats, _nb_logpmf, _score_grid, _tau

# Validados em docs/SIMULACAO_2025_2026.md — mudar exige nova validação.
DEFAULTS = {
    "blend_weight": 0.5,  # peso do BASELINE no ensemble
    "w_xg": 0.85,  # peso do xG no alvo misto da etapa 1
    "half_life_years": 0.75,  # meia-vida do peso temporal dos jogos
    "ridge_reg": 1.0,  # L2 sobre as forças atk/def
}


def _cfg(cfg_xg):
    out = dict(DEFAULTS)
    out.update(cfg_xg or {})
    return out


def fit(matches, xg_map, fit_date, cfg_xg=None):
    """Ajusta o modelo. Devolve dict JSON-serializável (cache do cron).

    matches: iterável de (date, home, away, home_score, away_score), só
    jogos DISPUTADOS, ordenado por data. xg_map: {(date, home, away):
    (home_xg, away_xg)} — jogo sem xG cai nos gols reais (sem viés, só
    mais ruído). fit_date: data ISO de referência do decaimento temporal.
    """
    c = _cfg(cfg_xg)
    matches = list(matches)
    if not matches:
        return None
    teams = sorted({t for r in matches for t in (r[1], r[2])})
    tix = {t: i for i, t in enumerate(teams)}
    T = len(teams)
    fd = date.fromisoformat(fit_date[:10])
    hl_days = c["half_life_years"] * 365.25

    hi = np.array([tix[r[1]] for r in matches])
    ai = np.array([tix[r[2]] for r in matches])
    hs = np.array([r[3] for r in matches], dtype=float)
    as_ = np.array([r[4] for r in matches], dtype=float)
    xg = [xg_map.get((r[0][:10], r[1], r[2])) for r in matches]
    hx = np.array([x[0] if x and x[0] is not None else g for x, g in zip(xg, hs)])
    ax = np.array([x[1] if x and x[1] is not None else g for x, g in zip(xg, as_)])
    w_xg = c["w_xg"]
    kh = w_xg * hx + (1 - w_xg) * hs
    ka = w_xg * ax + (1 - w_xg) * as_
    w = np.array([0.5 ** ((fd - date.fromisoformat(r[0][:10])).days / hl_days) for r in matches])

    # etapa 1: Poisson contínuo ponderado (gammaln aceita alvo não-inteiro),
    # ridge L2 puxa times com pouco jogo (ex.: promovidos) para a média.
    reg = c["ridge_reg"]
    x0 = np.r_[math.log(max(np.r_[kh, ka].mean(), 1e-3)), 0.25, np.zeros(2 * T)]

    def negll1(x):
        mu, ha = x[0], x[1]
        atk, dfn = x[2 : 2 + T], x[2 + T :]
        lh = np.exp(mu + ha + atk[hi] - dfn[ai])
        la = np.exp(mu + atk[ai] - dfn[hi])
        ll = (kh * np.log(lh) - lh) + (ka * np.log(la) - la)
        return -float((w * ll).sum()) + reg * float((x[2:] ** 2).sum())

    b1 = [(-3, 3), (-1, 1)] + [(-2.5, 2.5)] * (2 * T)
    r1 = minimize(negll1, x0, method="L-BFGS-B", bounds=b1, options={"maxiter": 800})
    mu, ha = float(r1.x[0]), float(r1.x[1])
    atk, dfn = r1.x[2 : 2 + T], r1.x[2 + T :]
    lh = np.exp(mu + ha + atk[hi] - dfn[ai])
    la = np.exp(mu + atk[ai] - dfn[hi])

    # etapa 2: dispersão (α) e correlação de placar baixo (ρ) nos gols reais
    def negll2(x):
        log_alpha, rho = x
        alpha = math.exp(log_alpha)
        tau = _tau(hs, as_, lh, la, rho)
        if np.any(tau <= 1e-12):
            return 1e12
        ll = _nb_logpmf(hs, lh, alpha) + _nb_logpmf(as_, la, alpha) + np.log(tau)
        return -float((w * ll).sum())

    r2 = minimize(
        negll2,
        [math.log(0.1), -0.03],
        method="L-BFGS-B",
        bounds=[(math.log(1e-4), math.log(3)), (-0.35, 0.35)],
    )

    return {
        "mu": mu,
        "ha": ha,
        "alpha": float(math.exp(r2.x[0])),
        "rho": float(r2.x[1]),
        "atk": {t: float(atk[tix[t]]) for t in teams},
        "def": {t: float(dfn[tix[t]]) for t in teams},
        "fit_date": fit_date[:10],
        "n_matches": len(matches),
        "hyper": {k: c[k] for k in DEFAULTS},
        "ok": bool(r1.success and r2.success),
    }


def predict(xgp, home, away, neutral=False, max_goals=12):
    """Previsão do modelo atk/def-xG — mesmas chaves de model.predict_match.
    Time fora do ajuste (sem histórico) recebe força 0 = média da liga
    (mesmo shrinkage que o ridge aplicaria a um time sem jogos)."""
    ah = xgp["atk"].get(home, 0.0)
    dh = xgp["def"].get(home, 0.0)
    aa = xgp["atk"].get(away, 0.0)
    da = xgp["def"].get(away, 0.0)
    ha = 0.0 if neutral else xgp["ha"]
    lam_h = math.exp(xgp["mu"] + ha + ah - da)
    lam_a = math.exp(xgp["mu"] + aa - dh)
    grid = _score_grid(lam_h, lam_a, xgp["alpha"], xgp["rho"], max_goals)
    return {
        "lambda_a": lam_h,
        "lambda_b": lam_a,
        "total_goals": lam_h + lam_a,
        **_grid_stats(grid, max_goals),
    }


def blend(r_base, r_xg, w_base=0.5):
    """Mistura das GRADES de placar (não das probabilidades finais): garante
    1X2/OU/BTTS/placares todos consistentes com a mesma distribuição."""
    grid = w_base * r_base["grid"] + (1 - w_base) * r_xg["grid"]
    grid = grid / grid.sum()
    max_goals = grid.shape[0] - 1
    lam_h = w_base * r_base["lambda_a"] + (1 - w_base) * r_xg["lambda_a"]
    lam_a = w_base * r_base["lambda_b"] + (1 - w_base) * r_xg["lambda_b"]
    return {
        "lambda_a": lam_h,
        "lambda_b": lam_a,
        "total_goals": lam_h + lam_a,
        "ensemble": True,
        **_grid_stats(grid, max_goals),
    }


def maybe_blend(r, conn, cfg, name_a, name_b, neutral):
    """Hook de serving: se `ensemble_xg.enabled` e o cache do cron existir,
    devolve o resultado blended; senão devolve `r` INTOCADO. Nunca lança —
    qualquer falha degrada para o baseline com aviso em stderr."""
    ecfg = (cfg or {}).get("ensemble_xg") or {}
    if not ecfg.get("enabled") or conn is None:
        return r
    try:
        from . import db

        row = db.load_xg_params(conn)
        if not row:
            print(
                "[ensemble_xg ligado mas sem cache — rode `python -m src.cron_update_models`; usando baseline]",
                file=sys.stderr,
            )
            return r
        xgp = row[0]
        max_goals = r["grid"].shape[0] - 1
        rx = predict(xgp, name_a, name_b, neutral=neutral, max_goals=max_goals)
        w = _cfg(ecfg)["blend_weight"]
        return blend(r, rx, w_base=w)
    except Exception as e:  # serving nunca cai por causa do ensemble
        print(f"[ensemble_xg falhou ({e}) — usando baseline]", file=sys.stderr)
        return r
