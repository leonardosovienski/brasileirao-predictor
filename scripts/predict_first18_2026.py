"""Walk-forward: prever os primeiros N jogos do Brasileirao 2026 usando so o
passado estrito (Elo forward + Poisson/Dixon-Coles calibrado antes da 1a rodada),
depois comparar com o resultado real. Sem lookahead: os parametros de calibracao
usam so jogos anteriores a 2026-01-28.

Uso: python scripts/predict_first18_2026.py [N_JOGOS]  (default 18)
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.getcwd())
from src import db, model, ratings
from src.ingest import ROOT, load_config

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

ratings_final, history = ratings.compute_ratings(rows, cfg["elo"])

FIRST_SEASON_DATE = "2026-01-28"
test_idx = [i for i, r in enumerate(rows) if r[5].startswith("Brasileir") and r[0] >= FIRST_SEASON_DATE][:N_GAMES]

cy = cfg["model"].get("calibration_window_years")
ccut = (date.fromisoformat(FIRST_SEASON_DATE) - timedelta(days=int(cy * 365.25))).isoformat()
params = model.fit_goal_model([h for h, r in zip(history, rows) if ccut <= r[0] < FIRST_SEASON_DATE])
MAXG = cfg["model"]["max_goals"]
home_adv = float(cfg["elo"]["home_advantage"])


def outcome(hs, as_):
    if hs > as_:
        return "H"
    if hs < as_:
        return "A"
    return "D"


hits = 0
rows_out = []
for i in test_idx:
    d, h, a, hs, as_, t, neu = rows[i]
    diff = history[i][0]
    r = model.predict_match(diff, 0.0, params, 0.0, max_goals=MAXG)
    ph, pd, pa = r["p_win"], r["p_draw"], r["p_loss"]
    pred_label = "H" if ph >= pd and ph >= pa else ("A" if pa >= pd else "D")
    real_label = outcome(hs, as_)
    ok = pred_label == real_label
    hits += ok
    rows_out.append((d, h, a, hs, as_, ph, pd, pa, pred_label, real_label, ok))

print(f"{'Data':10} {'Casa':22} {'Fora':22} {'Real':6} {'Prev':6} {'P(C)':6} {'P(E)':6} {'P(F)':6} OK")
for d, h, a, hs, as_, ph, pd, pa, pred_label, real_label, ok in rows_out:
    print(f"{d:10} {h:22} {a:22} {hs}-{as_:<3} {pred_label:6} {ph:.2f}   {pd:.2f}   {pa:.2f}   {'V' if ok else 'X'}")

n = len(rows_out)
print(f"\nAcertos (1X2): {hits}/{n} ({hits / n:.1%})")
