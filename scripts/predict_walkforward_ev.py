"""EV (Shin de-vig) para OU2.5 e dupla-chance (1X/X2) nos primeiros N jogos do
Brasileirao 2026. Metodologia walk-forward sem lookahead (Elo forward +
Poisson/Dixon-Coles calibrado so com pre-temporada); plugamos as odds de
fechamento e aplicamos a regra de compra do backtest (min_edge=0.02,
max_edge=0.15).

OU2.5: mercado binario complementar (over/under) -> shin_probabilities([o_over,
o_under]) devolve p_market direto pros dois lados.

DC (1X/X2): nao existe odd complementar direta pra "nao-1X" no banco, entao
devigamos o 1x2 fechado (odds_home/draw/away) e somamos as celulas do mesmo
jeito que a probabilidade do modelo e' somada (p_home+p_draw, p_draw+p_away) —
compara maca com maca.

Regra de compra: so entra se min_edge <= EV <= max_edge (mesma janela do
backtest, cfg["backtest"]).

Uso: python scripts/predict_walkforward_ev.py [N_JOGOS]
     (default N_JOGOS=18; ex.: rodar com 40 na proxima marca combinada)
"""

import sys
from datetime import date, timedelta

from src import db, model, ratings
from src.ingest import ROOT, load_config
from src.math_utils import shin_probabilities
from src.predict import _canon

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

MIN_EDGE = cfg["backtest"]["min_edge"]
MAX_EDGE = cfg["backtest"]["max_edge"]

om = {}
for row in conn.execute(
    "SELECT date, home_team, away_team, odds_home, odds_draw, odds_away, odds_over, odds_under FROM sofascore_matches"
).fetchall():
    d, h, a, oh, od, oa, oo, ou = row
    om[(d, _canon(h), _canon(a))] = (oh, od, oa, oo, ou)


def find_odds(d, h, a):
    return om.get((d, _canon(h), _canon(a)))


def ev(model_p, market_p):
    return model_p / market_p - 1.0


ou_bets = []
dc_bets = []
for i in test_idx:
    d, h, a, hs, as_, t, neu = rows[i]
    diff = history[i][0]
    r = model.predict_match(diff, 0.0, params, 0.0, max_goals=MAXG)
    odds = find_odds(d, h, a)
    if not odds or any(o is None for o in odds):
        continue
    oh, od, oa, oo, ou_odd = odds

    # --- OU2.5 ---
    p_over_model = r["over"][2.5]
    p_under_model = 1.0 - p_over_model
    mkt_probs, _z_ou, _overround_ou = shin_probabilities([oo, ou_odd])
    p_over_mkt, p_under_mkt = float(mkt_probs[0]), float(mkt_probs[1])
    ev_over = ev(p_over_model, p_over_mkt)
    ev_under = ev(p_under_model, p_under_mkt)
    real_total = hs + as_
    real_over = real_total > 2.5

    for side, edge, model_p, mkt_p in (
        ("OVER", ev_over, p_over_model, p_over_mkt),
        ("UNDER", ev_under, p_under_model, p_under_mkt),
    ):
        if MIN_EDGE <= edge <= MAX_EDGE:
            odd = oo if side == "OVER" else ou_odd
            won = real_over if side == "OVER" else not real_over
            pnl = (odd - 1.0) if won else -1.0
            ou_bets.append((d, h, a, side, edge, model_p, mkt_p, odd, won, pnl))

    # --- DC 1X / X2 (via 1x2 devigado) ---
    mkt_1x2, _z2, _overround2 = shin_probabilities([oh, od, oa])
    p_h_mkt, p_d_mkt, p_a_mkt = (float(x) for x in mkt_1x2)
    p_1x_mkt = p_h_mkt + p_d_mkt
    p_x2_mkt = p_d_mkt + p_a_mkt
    p_1x_model = r["p_win"] + r["p_draw"]
    p_x2_model = r["p_draw"] + r["p_loss"]
    ev_1x = ev(p_1x_model, p_1x_mkt)
    ev_x2 = ev(p_x2_model, p_x2_mkt)
    real_1x = hs >= as_
    real_x2 = as_ >= hs

    dc_row = conn.execute(
        "SELECT odds_dc_1x, odds_dc_x2 FROM sofascore_matches WHERE date=? AND home_team=? AND away_team=?",
        (d, h, a),
    ).fetchone()
    odd_1x_real, odd_x2_real = dc_row or (None, None)

    for side, edge, model_p, mkt_p, odd in (
        ("1X", ev_1x, p_1x_model, p_1x_mkt, odd_1x_real),
        ("X2", ev_x2, p_x2_model, p_x2_mkt, odd_x2_real),
    ):
        if MIN_EDGE <= edge <= MAX_EDGE and odd:
            won = real_1x if side == "1X" else real_x2
            pnl = (odd - 1.0) if won else -1.0
            dc_bets.append((d, h, a, side, edge, model_p, mkt_p, odd, won, pnl))

print(f"=== OU2.5 — apostas dentro da janela EV [{MIN_EDGE * 100:.0f}%, {MAX_EDGE * 100:.0f}%] ===")
print(
    f"{'Data':10} {'Casa':18} {'Fora':18} {'Lado':6} {'EV':7} {'P(mod)':7} {'P(mkt)':7} {'Odd':6} {'Ganhou':7} {'P&L'}"
)
for d, h, a, side, edge, mp, kp, odd, won, pnl in ou_bets:
    print(
        f"{d:10} {h:18} {a:18} {side:6} {edge:+.1%}  {mp:.2f}   {kp:.2f}   "
        f"{odd:<6} {'sim' if won else 'nao':7} {pnl:+.2f}"
    )
n_ou = len(ou_bets)
wins_ou = sum(1 for b in ou_bets if b[8])
pnl_ou = sum(b[9] for b in ou_bets)
print(
    f"\nOU2.5: {n_ou} apostas geradas | {wins_ou} vitorias ({wins_ou / n_ou:.1%})"
    if n_ou
    else "\nOU2.5: nenhuma aposta na janela de EV"
)
if n_ou:
    print(f"P&L (stake=1u): {pnl_ou:+.2f}u | ROI: {pnl_ou / n_ou:+.1%}")

print("\n=== Dupla-chance (1X/X2) — apostas dentro da janela EV ===")
print(
    f"{'Data':10} {'Casa':18} {'Fora':18} {'Lado':6} {'EV':7} {'P(mod)':7} {'P(mkt)':7} {'Odd':6} {'Ganhou':7} {'P&L'}"
)
for d, h, a, side, edge, mp, kp, odd, won, pnl in dc_bets:
    print(
        f"{d:10} {h:18} {a:18} {side:6} {edge:+.1%}  {mp:.2f}   {kp:.2f}   "
        f"{odd:<6} {'sim' if won else 'nao':7} {pnl:+.2f}"
    )
n_dc = len(dc_bets)
wins_dc = sum(1 for b in dc_bets if b[8])
pnl_dc = sum(b[9] for b in dc_bets)
print(
    f"\nDC: {n_dc} apostas geradas | {wins_dc} vitorias ({wins_dc / n_dc:.1%})"
    if n_dc
    else "\nDC: nenhuma aposta na janela de EV"
)
if n_dc:
    print(f"P&L (stake=1u): {pnl_dc:+.2f}u | ROI: {pnl_dc / n_dc:+.1%}")
