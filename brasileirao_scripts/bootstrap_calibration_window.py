"""Bootstrap do IC95% do ROI de OU2.5 para um valor especifico de
calibration_window_years — segue diretamente da investigacao em
scripts/investigate_calibration_window.py, que achou cy<=0.5 revertendo o
ROI de -33.8% (config atual, cy=4.0) para +22-26% em N=40, mas com poucas
apostas (11-21). Este script decide se esse sinal e' estatisticamente real
ou ruido, com a MESMA metodologia usada no veredito H1/H4: bootstrap por
CLUSTER de jogo (brasileirao_predictor.bootstrap.ci_mean_cluster — nao aposta i.i.d., porque
OVER e UNDER do mesmo jogo compartilham o choque do resultado), 1000
iteracoes, seed 13 (cfg["backtest"] — mesmos valores do backtest oficial).

IC que cruza zero = ainda sem evidencia de edge, mesmo que a media pareca
boa — decisao defensavel, nao convicção (mesmo criterio do H1 original).

Read-only: NAO toca em config.yaml.

Uso: python brasileirao_scripts/bootstrap_calibration_window.py [CY] [N_JOGOS]
     (default CY=0.5, N_JOGOS=40)
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.getcwd())
import numpy as np

from brasileirao_predictor import db, model, ratings
from brasileirao_predictor.bootstrap import ci_mean_cluster
from brasileirao_predictor.ingest import ROOT, load_config
from brasileirao_predictor.math_utils import shin_probabilities
from brasileirao_predictor.predict import _canon

CY = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
N_GAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 40

cfg = load_config()
conn = db.connect(str(ROOT / cfg["database"]))

rows_all = conn.execute(
    "SELECT date, home_team, away_team, home_score, away_score, tournament, neutral "
    "FROM matches WHERE home_score IS NOT NULL ORDER BY date"
).fetchall()

window = cfg["elo"].get("window_years")
if window:
    cut = (date.fromisoformat(rows_all[-1][0]) - timedelta(days=int(window * 365.25))).isoformat()
    rows_all = [r for r in rows_all if r[0] >= cut]

_, history = ratings.compute_ratings(rows_all, cfg["elo"])

FIRST_SEASON_DATE = "2026-01-28"
MAXG = cfg["model"]["max_goals"]
MIN_EDGE, MAX_EDGE = cfg["backtest"]["min_edge"], cfg["backtest"]["max_edge"]
ITERATIONS = cfg["backtest"].get("bootstrap_iterations", 1000)
SEED = cfg["backtest"].get("bootstrap_seed", 13)

test_idx = [i for i, r in enumerate(rows_all) if r[5].startswith("Brasileir") and r[0] >= FIRST_SEASON_DATE][:N_GAMES]

ccut = (date.fromisoformat(FIRST_SEASON_DATE) - timedelta(days=int(CY * 365.25))).isoformat()
train_hist = [h for h, r in zip(history, rows_all) if ccut <= r[0] < FIRST_SEASON_DATE]
params = model.fit_goal_model(train_hist)

odds_ou = {}
for row in conn.execute("SELECT date, home_team, away_team, odds_over, odds_under FROM sofascore_matches").fetchall():
    d, h, a, oo, ou = row
    odds_ou[(d, _canon(h), _canon(a))] = (oo, ou)

pairs = []  # (pnl, game_key) para o cluster bootstrap
detail = []
for i in test_idx:
    d, h, a, hs, as_, t, neu = rows_all[i]
    diff = history[i][0]
    r = model.predict_match(diff, 0.0, params, 0.0, max_goals=MAXG)
    odds = odds_ou.get((d, _canon(h), _canon(a)))
    if not odds or any(o is None for o in odds):
        continue
    oo, ou_odd = odds
    p_over = r["over"][2.5]
    p_under = 1.0 - p_over
    mkt, _z, _o = shin_probabilities([oo, ou_odd])
    p_over_mkt, p_under_mkt = float(mkt[0]), float(mkt[1])
    real_over = (hs + as_) > 2.5

    for side, edge, mp, odd, won in (
        ("OVER", p_over / p_over_mkt - 1.0, p_over, oo, real_over),
        ("UNDER", p_under / p_under_mkt - 1.0, p_under, ou_odd, not real_over),
    ):
        if MIN_EDGE <= edge <= MAX_EDGE:
            pnl = (odd - 1.0) if won else -1.0
            pairs.append((pnl, (d, h, a)))
            detail.append((d, h, a, side, edge, odd, won, pnl))

n = len(pairs)
n_games = len({c for _v, c in pairs})
print(f"calibration_window_years={CY}, N_JOGOS={N_GAMES}, treino={len(train_hist)} jogos\n")
print(f"{'Data':10} {'Casa':18} {'Fora':18} {'Lado':6} {'EV':7} {'Odd':6} {'Ganhou':7} {'P&L'}")
for d, h, a, side, edge, odd, won, pnl in detail:
    print(f"{d:10} {h:18} {a:18} {side:6} {edge:+.1%}  {odd:<6} {'sim' if won else 'nao':7} {pnl:+.2f}")

if n < 2:
    sys.exit(f"\nApostas insuficientes (n={n}) para bootstrap — abaixo do minimo de 2.")

rng = np.random.default_rng(SEED)
mean, lo, hi = ci_mean_cluster(pairs, ITERATIONS, rng)
sig = "SIGNIFICATIVO (IC nao cruza zero)" if (lo > 0 or hi < 0) else "NAO significativo (IC cruza zero)"

print(f"\nApostas: {n} ({n_games} jogos distintos) | iteracoes={ITERATIONS} | seed={SEED}")
print(f"ROI medio: {mean:+.1%}")
print(f"IC 95% (cluster bootstrap por jogo): [{lo:+.1%}, {hi:+.1%}]")
print(f"Veredito: {sig}")
