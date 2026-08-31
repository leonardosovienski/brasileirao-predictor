"""Walk-forward: OU2.5 e dupla-chance (1X/X2) para os primeiros N jogos do
Brasileirao 2026. Mesma metodologia sem lookahead de scripts/predict_first18_2026.py
(Elo forward + Poisson/Dixon-Coles calibrado so com pre-temporada). Foco em
hit-rate bruto; odds de fechamento (se existirem) sao so anotadas para EV
numa 2a etapa, nao usadas para decidir a previsao.

Uso: python brasileirao_scripts/predict_first18_ou_dc.py [N_JOGOS]  (default 18)
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.getcwd())
from brasileirao_predictor import db, model, ratings
from brasileirao_predictor.ingest import ROOT, load_config
from brasileirao_predictor.predict import _canon

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

# odds de fechamento (so anotacao, nao entram na previsao)
om = {}
for row in conn.execute(
    "SELECT date, home_team, away_team, odds_over, odds_under, odds_dc_1x, odds_dc_x2 FROM sofascore_matches"
).fetchall():
    d, h, a, oo, ou, o1x, ox2 = row
    om[(d, _canon(h), _canon(a))] = (oo, ou, o1x, ox2)


def find_odds(d, h, a):
    key = (d, _canon(h), _canon(a))
    return om.get(key)


hits_ou = 0
hits_dc = 0
rows_out = []
for i in test_idx:
    d, h, a, hs, as_, t, neu = rows[i]
    diff = history[i][0]
    r = model.predict_match(diff, 0.0, params, 0.0, max_goals=MAXG)
    p_over = r["over"][2.5]
    ou_pred = "OVER" if p_over >= 0.5 else "UNDER"
    real_total = hs + as_
    ou_real = "OVER" if real_total > 2.5 else "UNDER"
    ou_ok = ou_pred == ou_real
    hits_ou += ou_ok

    p_1x = r["p_win"] + r["p_draw"]  # 1X: mandante nao perde
    p_x2 = r["p_draw"] + r["p_loss"]  # X2: visitante nao perde
    dc_pred = "1X" if p_1x >= p_x2 else "X2"
    dc_p = max(p_1x, p_x2)
    real_1x = hs >= as_
    real_x2 = as_ >= hs
    dc_ok = real_1x if dc_pred == "1X" else real_x2
    hits_dc += dc_ok

    odds = find_odds(d, h, a)
    rows_out.append((d, h, a, hs, as_, p_over, ou_pred, ou_real, ou_ok, dc_pred, dc_p, dc_ok, odds))

print(
    f"{'Data':10} {'Casa':20} {'Fora':20} {'Real':6} {'Tot':4} {'P(Ov)':6} {'PrevOU':6} {'OU-ok':6} "
    f"{'PrevDC':6} {'P(DC)':6} {'DC-ok':6} {'Odds(O/U/1X/X2)'}"
)
for d, h, a, hs, as_, p_over, ou_pred, ou_real, ou_ok, dc_pred, dc_p, dc_ok, odds in rows_out:
    total = hs + as_
    odds_s = f"{odds}" if odds else "-"
    print(
        f"{d:10} {h:20} {a:20} {hs}-{as_:<3} {total:<4} {p_over:.2f}   {ou_pred:6} {'V' if ou_ok else 'X':6} "
        f"{dc_pred:6} {dc_p:.2f}   {'V' if dc_ok else 'X':6} {odds_s}"
    )

n = len(rows_out)
print(f"\nOU2.5      hit-rate: {hits_ou}/{n} ({hits_ou / n:.1%})")
print(f"DC (1X/X2) hit-rate: {hits_dc}/{n} ({hits_dc / n:.1%})")
