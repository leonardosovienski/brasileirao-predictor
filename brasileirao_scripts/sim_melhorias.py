"""Candidatos de melhoria testados em walk-forward pareado sobre 2025+2026.

Candidatos (mesma grade NB+Dixon-Coles do baseline; muda so a fonte dos lambdas):
  C1 forca-unica batch : lam_h=exp(mu+ha+s_h-s_a), lam_a=exp(mu+s_a-s_h),
                         ridge L2 em s, pesos com decaimento temporal.
  C2 ataque/defesa     : lam_h=exp(mu+ha+atk_h-def_a), lam_a=exp(mu+atk_a-def_h),
                         ridge L2 em atk/def, pesos com decaimento temporal.

Protocolo anti-snooping: half-life e reg escolhidos por validacao interna em
2024-H2 (ago-dez/2024, walk-forward mensal), CONGELADOS, e so entao avaliados
em 2025+2026. Comparacao pareada por jogo vs baseline + bootstrap do delta.

Uso: python brasileirao_scripts/sim_melhorias.py [--valida]
"""

import math
import os
import random
import statistics as st
import sys
from datetime import date, timedelta

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.getcwd())
from brasileirao_predictor import db, model, ratings
from brasileirao_predictor.ingest import ROOT, load_config
from brasileirao_predictor.math_utils import shin_probabilities
from brasileirao_predictor.model import _grid_stats, _nb_logpmf, _score_grid, _tau

cfg = load_config()
conn = db.connect(str(ROOT / cfg["database"]), read_only=True)
MAXG = cfg["model"]["max_goals"]
CY = cfg["model"]["calibration_window_years"]

rows = conn.execute(
    "SELECT date, home_team, away_team, home_score, away_score, tournament, neutral "
    "FROM matches WHERE home_score IS NOT NULL ORDER BY date, home_team"
).fetchall()
_, elo_history = ratings.compute_ratings(rows, cfg["elo"])

odds = {}
for r in conn.execute(
    "SELECT date, home_team, away_team, odds_home, odds_draw, odds_away, "
    "odds_over, odds_under FROM sofascore_matches WHERE home_score IS NOT NULL"
):
    odds[(r[0][:10], r[1], r[2])] = r[3:]


# ---------------------------------------------------------------- estimador batch
def fit_batch(train, fit_date, half_life_years, reg, atk_def):
    """Ajusta modelo batch ponderado no tempo.

    train: lista de (date, home, away, hs, as_).  Retorna dict de parametros.
    atk_def=False -> forca unica s_i;  True -> atk_i e def_i separados.
    """
    teams = sorted({t for r in train for t in (r[1], r[2])})
    tix = {t: i for i, t in enumerate(teams)}
    T = len(teams)
    fd = date.fromisoformat(fit_date)
    hl_days = half_life_years * 365.25

    hi = np.array([tix[r[1]] for r in train])
    ai = np.array([tix[r[2]] for r in train])
    hs = np.array([r[3] for r in train], dtype=float)
    as_ = np.array([r[4] for r in train], dtype=float)
    w = np.array([0.5 ** ((fd - date.fromisoformat(r[0])).days / hl_days) for r in train])

    nstr = 2 * T if atk_def else T
    # x = [mu, ha, strengths..., log_alpha, rho]
    x0 = np.r_[math.log(max(np.r_[hs, as_].mean(), 1e-3)), 0.25, np.zeros(nstr), math.log(0.1), -0.03]

    def negll(x):
        mu, ha = x[0], x[1]
        s = x[2 : 2 + nstr]
        log_alpha, rho = x[2 + nstr], x[3 + nstr]
        alpha = math.exp(log_alpha)
        if atk_def:
            atk, dfn = s[:T], s[T:]
            lh = np.exp(mu + ha + atk[hi] - dfn[ai])
            la = np.exp(mu + atk[ai] - dfn[hi])
        else:
            lh = np.exp(mu + ha + s[hi] - s[ai])
            la = np.exp(mu + s[ai] - s[hi])
        tau = _tau(hs, as_, lh, la, rho)
        if np.any(tau <= 1e-12):
            return 1e12
        ll = _nb_logpmf(hs, lh, alpha) + _nb_logpmf(as_, la, alpha) + np.log(tau)
        if not np.isfinite(ll).all():
            return 1e12
        return -float((w * ll).sum()) + reg * float((s**2).sum())

    bounds = [(-3, 3), (-1, 1)] + [(-2.5, 2.5)] * nstr + [(math.log(1e-4), math.log(3)), (-0.35, 0.35)]
    res = minimize(negll, x0, method="L-BFGS-B", bounds=bounds, options={"maxiter": 800})
    x = res.x
    out = {
        "mu": x[0],
        "ha": x[1],
        "log_alpha": x[2 + nstr],
        "rho": x[3 + nstr],
        "teams": tix,
        "atk_def": atk_def,
        "ok": bool(res.success),
    }
    if atk_def:
        out["atk"] = x[2 : 2 + T]
        out["def"] = x[2 + T : 2 + nstr]
    else:
        out["s"] = x[2 : 2 + nstr]
    return out


def predict_batch(p, home, away):
    tix = p["teams"]
    alpha = math.exp(p["log_alpha"])
    if p["atk_def"]:
        ah = p["atk"][tix[home]] if home in tix else 0.0
        dh = p["def"][tix[home]] if home in tix else 0.0
        aa = p["atk"][tix[away]] if away in tix else 0.0
        da = p["def"][tix[away]] if away in tix else 0.0
        lh = math.exp(p["mu"] + p["ha"] + ah - da)
        la = math.exp(p["mu"] + aa - dh)
    else:
        sh = p["s"][tix[home]] if home in tix else 0.0
        sa = p["s"][tix[away]] if away in tix else 0.0
        lh = math.exp(p["mu"] + p["ha"] + sh - sa)
        la = math.exp(p["mu"] + sa - sh)
    grid = _score_grid(lh, la, alpha, p["rho"], MAXG)
    g = _grid_stats(grid, MAXG)
    return {
        "pm": (g["p_win"], g["p_draw"], g["p_loss"]),
        "p_over25": g["over"][2.5],
        "lam_h": lh,
        "lam_a": la,
    }


# ------------------------------------------------------- C3: atk/def em xG
xg_map = {}
for r in conn.execute(
    "SELECT date, home_team, away_team, home_xg, away_xg FROM sofascore_matches "
    "WHERE home_score IS NOT NULL AND home_xg IS NOT NULL"
):
    xg_map[(r[0][:10], r[1], r[2])] = (r[3], r[4])


def fit_batch_xg(train, fit_date, half_life_years, reg, w_xg):
    """Duas etapas: (1) forcas atk/def por Poisson ponderado sobre o alvo misto
    k* = w_xg*xG + (1-w_xg)*gols (gammaln aceita k continuo); (2) com as forcas
    congeladas, alpha e rho do NB+DC ajustados nos GOLS inteiros reais."""
    teams = sorted({t for r in train for t in (r[1], r[2])})
    tix = {t: i for i, t in enumerate(teams)}
    T = len(teams)
    fd = date.fromisoformat(fit_date)
    hl_days = half_life_years * 365.25

    hi = np.array([tix[r[1]] for r in train])
    ai = np.array([tix[r[2]] for r in train])
    hs = np.array([r[3] for r in train], dtype=float)
    as_ = np.array([r[4] for r in train], dtype=float)
    xg = [xg_map.get((r[0][:10], r[1], r[2])) for r in train]
    hx = np.array([x[0] if x and x[0] is not None else g for x, g in zip(xg, hs)])
    ax = np.array([x[1] if x and x[1] is not None else g for x, g in zip(xg, as_)])
    kh = w_xg * hx + (1 - w_xg) * hs
    ka = w_xg * ax + (1 - w_xg) * as_
    w = np.array([0.5 ** ((fd - date.fromisoformat(r[0])).days / hl_days) for r in train])

    # etapa 1: Poisson continuo ponderado, ridge nas forcas
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
    mu, ha = r1.x[0], r1.x[1]
    atk, dfn = r1.x[2 : 2 + T], r1.x[2 + T :]
    lh = np.exp(mu + ha + atk[hi] - dfn[ai])
    la = np.exp(mu + atk[ai] - dfn[hi])

    # etapa 2: alpha e rho nos gols reais, forcas congeladas
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
        "atk": atk,
        "def": dfn,
        "teams": tix,
        "atk_def": True,
        "log_alpha": r2.x[0],
        "rho": r2.x[1],
        "ok": bool(r1.success and r2.success),
    }


# ---------------------------------------------------------------- baseline
def fit_baseline_before(cut_date):
    lo = (date.fromisoformat(cut_date) - timedelta(days=int(CY * 365.25))).isoformat()
    hist = [h for h, r in zip(elo_history, rows) if lo <= r[0] < cut_date]
    return model.fit_goal_model(hist)


def walkforward(test_pred, model_kind, hl=None, reg=None):
    """Roda walk-forward com refit mensal. test_pred: funcao date_str -> bool."""
    idx = [i for i, r in enumerate(rows) if test_pred(r[0])]
    cache = {}
    out = []
    for i in idx:
        d, h, a, hs, as_, _t, _n = rows[i]
        mkey = d[:7]
        if mkey not in cache:
            if model_kind == "baseline":
                cache[mkey] = fit_baseline_before(d)
            else:
                train = [(r[0], r[1], r[2], r[3], r[4]) for r in rows if r[0] < d]
                if model_kind.startswith("xg"):
                    w_xg = float(model_kind.split(":")[1])
                    cache[mkey] = fit_batch_xg(train, d, hl, reg, w_xg)
                else:
                    cache[mkey] = fit_batch(train, d, hl, reg, atk_def=(model_kind == "atkdef"))
        p = cache[mkey]
        if model_kind == "baseline":
            r = model.predict_match(elo_history[i][0], 0.0, p, 0.0, max_goals=MAXG)
            pred = {
                "pm": (r["p_win"], r["p_draw"], r["p_loss"]),
                "p_over25": r["over"][2.5],
                "lam_h": r["lambda_a"],
                "lam_a": r["lambda_b"],
            }
        else:
            pred = predict_batch(p, h, a)
        y = 0 if hs > as_ else (1 if hs == as_ else 2)
        rec = {
            "date": d,
            "home": h,
            "away": a,
            "hs": hs,
            "as": as_,
            "y": y,
            "over_real": int(hs + as_ > 2.5),
            **pred,
        }
        o = odds.get((d, h, a))
        if o and o[0] and o[1] and o[2]:
            rec["mk"] = tuple(shin_probabilities([o[0], o[1], o[2]])[0])
        if o and o[3] and o[4]:
            rec["mk_over"] = shin_probabilities([o[3], o[4]])[0][0]
        out.append(rec)
    return out


def brier3(p, y):
    return sum((p[k] - (1 if k == y else 0)) ** 2 for k in range(3))


def summarize(tag, recs):
    br = st.mean(brier3(r["pm"], r["y"]) for r in recs)
    ll = st.mean(-math.log(max(r["pm"][r["y"]], 1e-9)) for r in recs)
    acc = st.mean(int(max(range(3), key=lambda k: r["pm"][k]) == r["y"]) for r in recs)
    ob = st.mean((r["p_over25"] - r["over_real"]) ** 2 for r in recs)
    oacc = st.mean(int((r["p_over25"] > 0.5) == r["over_real"]) for r in recs)
    pmax = st.mean(max(r["pm"]) for r in recs)
    tot = [r["lam_h"] + r["lam_a"] for r in recs]
    print(
        f"{tag:28s} Brier {br:.4f} | LL {ll:.4f} | acc {acc:.1%} | "
        f"BrierOU {ob:.4f} | accOU {oacc:.1%} | probMax {pmax:.1%} | "
        f"lamTot {st.mean(tot):.2f}±{st.pstdev(tot):.2f}"
    )
    return br


def paired_bootstrap(base, cand, key=lambda r: brier3(r["pm"], r["y"]), n_iter=2000, seed=13):
    """IC95 do delta (cand - base) pareado por jogo."""
    assert len(base) == len(cand)
    d = [key(c) - key(b) for b, c in zip(base, cand)]
    rng = random.Random(seed)
    n = len(d)
    means = sorted(st.mean(rng.choices(d, k=n)) for _ in range(n_iter))
    return st.mean(d), means[int(0.025 * n_iter)], means[int(0.975 * n_iter)]


# ---------------------------------------------------------------- execucao
if "--valida" in sys.argv:
    # validacao interna 2024-H2 para escolher (half-life, reg) — nao toca 2025/26
    def tp(d):
        return "2024-08-01" <= d < "2025-01-01"

    print("== validacao 2024-H2 (escolha de hiperparametros) ==")
    base = walkforward(tp, "baseline")
    summarize("baseline", base)
    for kind in ("forca", "atkdef"):
        for hl in (0.75, 1.5, 3.0):
            for reg in (1.0, 3.0, 10.0):
                recs = walkforward(tp, kind, hl, reg)
                summarize(f"{kind} hl={hl} reg={reg}", recs)
    sys.exit(0)

# Hiperparametros CONGELADOS pela validacao 2024-H2 (rodar --valida primeiro):
#   C1/C2: hl=0.75, reg=10  |  C3 (xG): w=0.85, hl=0.75, reg=1
HL = float(os.environ.get("SIM_HL", "0.75"))
REG = float(os.environ.get("SIM_REG", "10"))


def ensemble(b, c, w=0.5):
    r = dict(c)
    r["pm"] = tuple(w * x + (1 - w) * y for x, y in zip(b["pm"], c["pm"]))
    r["p_over25"] = w * b["p_over25"] + (1 - w) * c["p_over25"]
    return r


def compara(base, recs, nome):
    summarize(nome, recs)
    m, lo, hi = paired_bootstrap(base, recs)
    sig = "SIGNIFICATIVO" if hi < 0 else ("pior sig." if lo > 0 else "nao sig.")
    print(f"    dBrier vs baseline {m:+.4f}  IC95 [{lo:+.4f}, {hi:+.4f}] -> {sig}")
    m2, lo2, hi2 = paired_bootstrap(base, recs, key=lambda r: (r["p_over25"] - r["over_real"]) ** 2)
    sig2 = "SIGNIFICATIVO" if hi2 < 0 else ("pior sig." if lo2 > 0 else "nao sig.")
    print(f"    dBrierOU vs baseline {m2:+.4f}  IC95 [{lo2:+.4f}, {hi2:+.4f}] -> {sig2}")


for periodo in ("2025", "2026", "2025+2026"):
    tp = (
        (lambda d: d.startswith("2025") or d.startswith("2026"))
        if periodo == "2025+2026"
        else (lambda d, y=periodo: d.startswith(y))
    )
    print(f"\n== teste {periodo} ==")
    base = walkforward(tp, "baseline")
    summarize("baseline (Elo+cosh)", base)
    mrecs = [r for r in base if "mk" in r]
    if mrecs:
        print(
            f"{'mercado (Shin fechamento)':28s} Brier "
            f"{st.mean(brier3(r['mk'], r['y']) for r in mrecs):.4f} (n={len(mrecs)})"
        )
    c1 = walkforward(tp, "forca", HL, REG)
    compara(base, c1, "C1 forca-unica batch")
    c2 = walkforward(tp, "atkdef", HL, REG)
    compara(base, c2, "C2 ataque/defesa batch")
    c3 = walkforward(tp, "xg:0.85", 0.75, 1.0)
    compara(base, c3, "C3 atk/def xG")
    compara(base, [ensemble(b, c) for b, c in zip(base, c3)], "C4 ensemble 50/50 base+C3")
