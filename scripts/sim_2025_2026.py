"""Simulacao walk-forward do pipeline ATUAL sobre 2025 (temporada completa)
e 2026 (17 rodadas jogadas), com diagnostico de causa.

Metodologia identica ao backtest oficial (Elo forward via compute_ratings,
Poisson/NB+DC recalibrado so com jogos passados), refit MENSAL, janela de
calibracao do config (calibration_window_years). Read-only no banco.

Uso: python scripts/sim_2025_2026.py
"""

import math
import os
import statistics as st
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.getcwd())
from src import db, model, ratings
from src.ingest import ROOT, load_config
from src.math_utils import shin_probabilities

cfg = load_config()
conn = db.connect(str(ROOT / cfg["database"]), read_only=True)

rows = conn.execute(
    "SELECT date, home_team, away_team, home_score, away_score, tournament, neutral "
    "FROM matches WHERE home_score IS NOT NULL ORDER BY date, home_team"
).fetchall()

# Elo forward: history[i] = (diff_pre_jogo_com_mando, hs, as)
_, history = ratings.compute_ratings(rows, cfg["elo"])

# odds de fechamento e abertura por (date, home, away) — nomes identicos entre tabelas
odds = {}
for r in conn.execute(
    "SELECT date, home_team, away_team, odds_home, odds_draw, odds_away, "
    "odds_over, odds_under FROM sofascore_matches WHERE home_score IS NOT NULL"
):
    odds[(r[0][:10], r[1], r[2])] = r[3:]

MAXG = cfg["model"]["max_goals"]
CY = cfg["model"]["calibration_window_years"]


def fit_before(cut_date):
    """Recalibra o modelo de gols so com jogos < cut_date (janela CY anos)."""
    lo = (date.fromisoformat(cut_date) - timedelta(days=int(CY * 365.25))).isoformat()
    hist = [h for h, r in zip(history, rows) if lo <= r[0] < cut_date]
    return model.fit_goal_model(hist)


def brier3(p, y):
    return sum((p[k] - (1 if k == y else 0)) ** 2 for k in range(3))


def evaluate(year):
    idx = [i for i, r in enumerate(rows) if r[0].startswith(year)]
    params_cache = {}
    out = []
    for i in idx:
        d, h, a, hs, as_, _t, _n = rows[i]
        mkey = d[:7]
        if mkey not in params_cache:
            params_cache[mkey] = fit_before(d)
        p = model.predict_match(history[i][0], 0.0, params_cache[mkey], 0.0, max_goals=MAXG)
        y = 0 if hs > as_ else (1 if hs == as_ else 2)
        rec = {
            "date": d,
            "home": h,
            "away": a,
            "hs": hs,
            "as": as_,
            "y": y,
            "pm": (p["p_win"], p["p_draw"], p["p_loss"]),
            "lam_h": p["lambda_a"],
            "lam_a": p["lambda_b"],
            "p_over25": p["over"][2.5],
            "total_real": hs + as_,
            "diff": history[i][0],
        }
        o = odds.get((d, h, a))
        if o and o[0] and o[1] and o[2]:
            sh, _z, _ov = shin_probabilities([o[0], o[1], o[2]])
            rec["mk"] = tuple(sh)
        if o and o[3] and o[4]:
            sh2, _z, _ov = shin_probabilities([o[3], o[4]])
            rec["mk_over"] = sh2[0]
        out.append(rec)
    return out


def report(tag, recs):
    n = len(recs)
    acc = st.mean(int(max(range(3), key=lambda k: r["pm"][k]) == r["y"]) for r in recs)
    br = st.mean(brier3(r["pm"], r["y"]) for r in recs)
    ll = st.mean(-math.log(max(r["pm"][r["y"]], 1e-9)) for r in recs)
    draws_pred = sum(1 for r in recs if max(range(3), key=lambda k: r["pm"][k]) == 1)
    draws_real = sum(1 for r in recs if r["y"] == 1)
    pmax = st.mean(max(r["pm"]) for r in recs)
    tot = [r["lam_h"] + r["lam_a"] for r in recs]
    print(f"\n=== {tag} — {n} jogos ===")
    print(f"1X2: acerto {acc:.1%} | Brier {br:.4f} (acaso 0.6667) | logloss {ll:.4f}")
    print(
        f"empates: previstos como pick {draws_pred} | reais {draws_real} "
        f"({draws_real / n:.0%}) | P(empate) media {st.mean(r['pm'][1] for r in recs):.1%}"
    )
    print(
        f"nitidez: probMax media {pmax:.1%} | lambda_total media {st.mean(tot):.2f} "
        f"dp {st.pstdev(tot):.2f} | gols reais media {st.mean(r['total_real'] for r in recs):.2f}"
    )

    wm = [r for r in recs if "mk" in r]
    if wm:
        mbr = st.mean(brier3(r["pm"], r["y"]) for r in wm)
        kbr = st.mean(brier3(r["mk"], r["y"]) for r in wm)
        macc = st.mean(int(max(range(3), key=lambda k: r["pm"][k]) == r["y"]) for r in wm)
        kacc = st.mean(int(max(range(3), key=lambda k: r["mk"][k]) == r["y"]) for r in wm)
        kpmax = st.mean(max(r["mk"]) for r in wm)
        print(
            f"vs MERCADO (fechamento Shin, n={len(wm)}): "
            f"Brier modelo {mbr:.4f} | mercado {kbr:.4f} (dif {mbr - kbr:+.4f})"
        )
        print(f"  acerto modelo {macc:.1%} | mercado {kacc:.1%} | probMax mercado {kpmax:.1%}")
    wo = [r for r in recs if "mk_over" in r]
    if wo:
        oacc = st.mean(int((r["p_over25"] > 0.5) == (r["total_real"] > 2.5)) for r in wo)
        obr = st.mean((r["p_over25"] - (r["total_real"] > 2.5)) ** 2 for r in wo)
        kbr2 = st.mean((r["mk_over"] - (r["total_real"] > 2.5)) ** 2 for r in wo)
        kacc2 = st.mean(int((r["mk_over"] > 0.5) == (r["total_real"] > 2.5)) for r in wo)
        over_rate = st.mean(int(r["total_real"] > 2.5) for r in wo)
        print(
            f"OU2.5 (n={len(wo)}): acerto modelo {oacc:.1%} | mercado {kacc2:.1%} | "
            f"Brier modelo {obr:.4f} | mercado {kbr2:.4f} | taxa over real {over_rate:.1%}"
        )
        print(
            f"  P(over) media modelo {st.mean(r['p_over25'] for r in wo):.1%} | "
            f"mercado {st.mean(r['mk_over'] for r in wo):.1%}"
        )
    return recs


def team_bias(recs, tag):
    """Gols reais - esperados por time (ataque e defesa), pra localizar vies."""
    atk = defaultdict(float)
    dfs = defaultdict(float)
    nj = defaultdict(int)
    for r in recs:
        atk[r["home"]] += r["hs"] - r["lam_h"]
        dfs[r["home"]] += r["lam_a"] - r["as"]
        atk[r["away"]] += r["as"] - r["lam_a"]
        dfs[r["away"]] += r["lam_h"] - r["hs"]
        nj[r["home"]] += 1
        nj[r["away"]] += 1
    print(f"\n--- vies por time ({tag}): dAtq = gols feitos - esperados; dDef = esperados - sofridos ---")
    for t in sorted(nj, key=lambda t: -(abs(atk[t]) + abs(dfs[t]))):
        print(f"  {t:24s} J={nj[t]:2d}  dAtq {atk[t]:+6.2f}  dDef {dfs[t]:+6.2f}")


def calib_curve(recs, tag):
    """Curva de calibracao do pick favorito do modelo."""
    buckets = defaultdict(list)
    for r in recs:
        k = max(range(3), key=lambda j: r["pm"][j])
        buckets[round(r["pm"][k] * 10)].append(int(k == r["y"]))
    print(f"\n--- calibracao do pick ({tag}) ---")
    for b in sorted(buckets):
        v = buckets[b]
        print(f"  conf ~{b * 10}%: n={len(v):3d}  acerto real {st.mean(v):.1%}")


r25 = report("2025 (temporada completa)", evaluate("2025"))
r26 = report("2026 (17 rodadas)", evaluate("2026"))

team_bias(r26, "2026")
calib_curve(r25 + r26, "2025+2026")

# times promovidos (sem historico -> Elo inicia em 1500)
PROMOVIDOS = {
    "2025": ["Ceará", "Mirassol", "Santos", "Sport Recife"],
    "2026": ["Athletico", "Chapecoense", "Coritiba", "Remo"],
}
print("\n--- times promovidos (Elo inicial 1500 = media da liga) ---")
for yr, teams, recs in (("2025", PROMOVIDOS["2025"], r25), ("2026", PROMOVIDOS["2026"], r26)):
    sub = [r for r in recs if r["home"] in teams or r["away"] in teams]
    if not sub:
        continue
    pts = 0.0
    exp_pts = 0.0
    n = 0
    for r in sub:
        for side, ph, pd in ((0, r["pm"][0], r["pm"][1]),):
            pass
        for t in teams:
            if r["home"] == t:
                won = r["y"] == 0
                drew = r["y"] == 1
                p_w, p_d = r["pm"][0], r["pm"][1]
            elif r["away"] == t:
                won = r["y"] == 2
                drew = r["y"] == 1
                p_w, p_d = r["pm"][2], r["pm"][1]
            else:
                continue
            pts += 3 * won + drew
            exp_pts += 3 * p_w + p_d
            n += 1
    print(
        f"  {yr}: {n} jogos-time | pontos reais {pts:.0f} | esperados pelo modelo "
        f"{exp_pts:.0f} ({'superestimados' if exp_pts > pts else 'subestimados'} "
        f"em {abs(exp_pts - pts):.0f} pts)"
    )
