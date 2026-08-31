"""Quebra por time dos primeiros N jogos do Brasileirao 2026: gols esperados
pelo modelo (ataque/defesa) vs gols reais, e calibracao do resultado (Brier)
por time. Mesma metodologia walk-forward sem lookahead de
scripts/predict_first18_2026.py — serve pra ver ONDE o modelo erra (que times
ele super/subestima), nao so quanto erra no agregado.

Uso: python brasileirao_scripts/predict_first18_teams.py [N_JOGOS]  (default 18)
"""

import os
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.getcwd())
from brasileirao_predictor import db, model, ratings
from brasileirao_predictor.ingest import ROOT, load_config

N_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 18
cfg = load_config()
conn = db.connect(str(ROOT / cfg["database"]))

rows = conn.execute(
    "SELECT date, home_team, away_team, home_score, away_score, tournament, neutral "
    "FROM matches WHERE home_score IS NOT NULL ORDER BY date"
).fetchall()

window = cfg["elo"].get("window_years")
if window:
    cut = (date.fromisoformat(rows[-1][0]) - timedelta(days=int(window * 365.25))).isoformat()
    rows = [r for r in rows if r[0] >= cut]

_, history = ratings.compute_ratings(rows, cfg["elo"])

FIRST_SEASON_DATE = "2026-01-28"
test_idx = [i for i, r in enumerate(rows) if r[5].startswith("Brasileir") and r[0] >= FIRST_SEASON_DATE][:N_GAMES]

cy = cfg["model"].get("calibration_window_years")
ccut = (date.fromisoformat(FIRST_SEASON_DATE) - timedelta(days=int(cy * 365.25))).isoformat()
params = model.fit_goal_model([h for h, r in zip(history, rows) if ccut <= r[0] < FIRST_SEASON_DATE])
MAXG = cfg["model"]["max_goals"]


def outcome(hs, as_):
    if hs > as_:
        return "H"
    if hs < as_:
        return "A"
    return "D"


def brier(ph, pd, pa, real):
    yh, yd, ya = (1, 0, 0) if real == "H" else ((0, 1, 0) if real == "D" else (0, 0, 1))
    return (ph - yh) ** 2 + (pd - yd) ** 2 + (pa - ya) ** 2


team_stats = defaultdict(
    lambda: {
        "jogos": 0,
        "gf": 0,
        "ga": 0,
        "xgf": 0.0,
        "xga": 0.0,
        "acertos": 0,
        "brier_total": 0.0,
    }
)

for i in test_idx:
    d, h, a, hs, as_, t, neu = rows[i]
    diff = history[i][0]
    r = model.predict_match(diff, 0.0, params, 0.0, max_goals=MAXG)
    lam_h, lam_a = r["lambda_a"], r["lambda_b"]
    ph, pd, pa = r["p_win"], r["p_draw"], r["p_loss"]
    real = outcome(hs, as_)
    pred = "H" if ph >= pd and ph >= pa else ("A" if pa >= pd else "D")
    br = brier(ph, pd, pa, real)

    th = team_stats[h]
    th["jogos"] += 1
    th["gf"] += hs
    th["ga"] += as_
    th["xgf"] += lam_h
    th["xga"] += lam_a
    th["acertos"] += int(pred == real)
    th["brier_total"] += br

    ta = team_stats[a]
    ta["jogos"] += 1
    ta["gf"] += as_
    ta["ga"] += hs
    ta["xgf"] += lam_a
    ta["xga"] += lam_h
    ta["acertos"] += int(pred == real)
    ta["brier_total"] += br

rows_out = []
for team, s in team_stats.items():
    delta_ataque = s["gf"] - s["xgf"]  # + = time fez mais gols do que o modelo esperava
    delta_defesa = s["xga"] - s["ga"]  # + = time sofreu MENOS do que o modelo esperava (defesa melhor)
    brier_medio = s["brier_total"] / s["jogos"]
    rows_out.append(
        (
            team,
            s["jogos"],
            s["gf"],
            s["xgf"],
            delta_ataque,
            s["ga"],
            s["xga"],
            delta_defesa,
            s["acertos"],
            brier_medio,
        )
    )

rows_out.sort(key=lambda x: x[4] + x[7], reverse=True)  # mais "positivo" (superou o modelo) primeiro

print(f"{'Time':22} {'J':3} {'GF':4} {'xGF':6} {'ΔAtaque':8} {'GC':4} {'xGC':6} {'ΔDefesa':8} {'1X2 ok':7} {'Brier':6}")
for team, jogos, gf, xgf, dat, ga, xga, ddef, acertos, br in rows_out:
    print(
        f"{team:22} {jogos:<3} {gf:<4} {xgf:<6.2f} {dat:+.2f}    {ga:<4} {xga:<6.2f} {ddef:+.2f}    "
        f"{acertos}/{jogos:<4} {br:.2f}"
    )

n_games = len(test_idx)
brier_uniform = brier(1 / 3, 1 / 3, 1 / 3, "H")  # brier de "sempre 1/3,1/3,1/3" como piso de referencia
brier_global = sum(s["brier_total"] for s in team_stats.values()) / (2 * n_games)
print(f"\nBrier medio global (1X2, quanto menor melhor; piso uniforme={brier_uniform:.3f}): {brier_global:.3f}")
print("ΔAtaque > 0 = time fez mais gols que o modelo previa (modelo subestimou o ataque)")
print("ΔDefesa > 0 = time sofreu menos gols que o modelo previa (modelo subestimou a defesa)")
