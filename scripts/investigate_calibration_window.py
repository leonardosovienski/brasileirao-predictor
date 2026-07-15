"""Investigacao de causa raiz (2a hipotese, apos form_half_life_years ter sido
REFUTADA — ver scripts/investigate_half_life.py): sera que
calibration_window_years=4 (config.yaml, model.calibration_window_years) esta
calibrando o Poisson (a,b,alpha,rho) numa janela longa demais, diluindo o
padrao de gols da temporada mais recente e causando o vies persistente visto
em N=18 e N=40 (Palmeiras/Gremio/Botafogo superestimados pra baixo,
Internacional pra cima, Cruzeiro mal calibrado em defesa)?

Varre calibration_window_years num grid, recalibrando o Poisson do zero pra
cada valor (Elo forward fica FIXO na config atual — half_life ja foi testado
e descartado isoladamente). Metricas: Brier medio (1X2), hit-rate 1X2/OU2.5,
vies acumulado nos 5 times flagged, e EV/ROI real de OU2.5 com Shin de-vig
sobre odds de fechamento (mesma regra de compra do backtest, 2%-15%) — e' a
metrica que decide se um ganho de hit-rate vira lucro de verdade.

Read-only: NAO toca em config.yaml.

Uso: python scripts/investigate_calibration_window.py [N_JOGOS]  (default 40)
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.getcwd())
from src import db, model, ratings
from src.ingest import ROOT, load_config
from src.math_utils import shin_probabilities
from src.predict import _canon

N_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 40

cfg = load_config()
conn = db.connect(str(ROOT / cfg["database"]))

rows_all = conn.execute(
    "SELECT date, home_team, away_team, home_score, away_score, tournament, neutral "
    "FROM matches WHERE home_score IS NOT NULL ORDER BY date").fetchall()

window = cfg["elo"].get("window_years")
if window:
    cut = (date.fromisoformat(rows_all[-1][0]) - timedelta(days=int(window * 365.25))).isoformat()
    rows_all = [r for r in rows_all if r[0] >= cut]

# Elo forward FIXO na config atual — so a janela de calibracao do Poisson varia
_, history = ratings.compute_ratings(rows_all, cfg["elo"])

FIRST_SEASON_DATE = "2026-01-28"
MAXG = cfg["model"]["max_goals"]

test_idx = [i for i, r in enumerate(rows_all)
            if r[5].startswith("Brasileir") and r[0] >= FIRST_SEASON_DATE][:N_GAMES]

FLAGGED_TEAMS = {"Palmeiras", "Grêmio", "Botafogo", "Internacional", "Cruzeiro"}
MIN_EDGE, MAX_EDGE = cfg["backtest"]["min_edge"], cfg["backtest"]["max_edge"]

odds_ou = {}
for row in conn.execute(
        "SELECT date, home_team, away_team, odds_over, odds_under FROM sofascore_matches").fetchall():
    d, h, a, oo, ou = row
    odds_ou[(d, _canon(h), _canon(a))] = (oo, ou)


def outcome(hs, as_):
    if hs > as_:
        return "H"
    if hs < as_:
        return "A"
    return "D"


def brier(ph, pd, pa, real):
    yh, yd, ya = (1, 0, 0) if real == "H" else ((0, 1, 0) if real == "D" else (0, 0, 1))
    return (ph - yh) ** 2 + (pd - yd) ** 2 + (pa - ya) ** 2


def run(cy):
    if cy is None:
        ccut = rows_all[0][0]  # tudo dentro da window_years do Elo
    else:
        ccut = (date.fromisoformat(FIRST_SEASON_DATE) - timedelta(days=int(cy * 365.25))).isoformat()

    train_hist = [h for h, r in zip(history, rows_all) if ccut <= r[0] < FIRST_SEASON_DATE]
    n_train = len(train_hist)
    params = model.fit_goal_model(train_hist)

    hits_1x2 = hits_ou = 0
    brier_total = 0.0
    flagged_bias = 0.0
    team_xgf, team_gf, team_xga, team_ga = {}, {}, {}, {}
    ev_bets = 0
    ev_wins = 0
    ev_pnl = 0.0

    for i in test_idx:
        d, h, a, hs, as_, t, neu = rows_all[i]
        diff = history[i][0]
        r = model.predict_match(diff, 0.0, params, 0.0, max_goals=MAXG)
        lam_h, lam_a = r["lambda_a"], r["lambda_b"]
        ph, pd, pa = r["p_win"], r["p_draw"], r["p_loss"]
        real = outcome(hs, as_)
        pred = "H" if ph >= pd and ph >= pa else ("A" if pa >= pd else "D")
        hits_1x2 += int(pred == real)
        brier_total += brier(ph, pd, pa, real)
        p_over = r["over"][2.5]
        p_under = 1.0 - p_over
        ou_pred = "OVER" if p_over >= 0.5 else "UNDER"
        real_over = (hs + as_) > 2.5
        ou_real = "OVER" if real_over else "UNDER"
        hits_ou += int(ou_pred == ou_real)

        odds = odds_ou.get((d, _canon(h), _canon(a)))
        if odds and all(o is not None for o in odds):
            oo, ou_odd = odds
            mkt, _z, _o = shin_probabilities([oo, ou_odd])
            p_over_mkt, p_under_mkt = float(mkt[0]), float(mkt[1])
            for side, edge, mp, odd, won in (
                    ("OVER", p_over / p_over_mkt - 1.0, p_over, oo, real_over),
                    ("UNDER", p_under / p_under_mkt - 1.0, p_under, ou_odd, not real_over)):
                if MIN_EDGE <= edge <= MAX_EDGE:
                    ev_bets += 1
                    ev_wins += int(won)
                    ev_pnl += (odd - 1.0) if won else -1.0

        for team, gf, xgf, ga, xga in ((h, hs, lam_h, as_, lam_a), (a, as_, lam_a, hs, lam_h)):
            team_gf[team] = team_gf.get(team, 0) + gf
            team_xgf[team] = team_xgf.get(team, 0.0) + xgf
            team_ga[team] = team_ga.get(team, 0) + ga
            team_xga[team] = team_xga.get(team, 0.0) + xga

    for team in FLAGGED_TEAMS:
        if team in team_gf:
            d_ataque = team_gf[team] - team_xgf[team]
            d_defesa = team_xga[team] - team_ga[team]
            flagged_bias += abs(d_ataque) + abs(d_defesa)

    n = len(test_idx)
    return {
        "cy": cy, "n_train": n_train, "n": n,
        "hit_1x2": hits_1x2 / n, "hit_ou25": hits_ou / n,
        "brier": brier_total / n, "flagged_bias": flagged_bias,
        "ev_bets": ev_bets, "ev_wins": ev_wins, "ev_pnl": ev_pnl,
    }


GRID = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, None]

print(f"Investigando calibration_window_years em N={N_GAMES} jogos (config atual: "
      f"{cfg['model'].get('calibration_window_years')})\n")
print(f"{'cy':6} {'n_train':8} {'hit_1X2':8} {'hit_OU2.5':10} {'Brier':7} {'vies_flg':9} "
      f"{'ev_bets':8} {'ev_win%':8} {'ev_ROI':8}")
results = []
for cy in GRID:
    res = run(cy)
    results.append(res)
    cy_s = "None" if cy is None else f"{cy:.2f}"
    marker = "  <- config atual" if cy == cfg["model"].get("calibration_window_years") else ""
    roi_s = f"{res['ev_pnl']/res['ev_bets']:+.1%}" if res["ev_bets"] else "n/a"
    win_s = f"{res['ev_wins']/res['ev_bets']:.1%}" if res["ev_bets"] else "n/a"
    print(f"{cy_s:6} {res['n_train']:<8} {res['hit_1x2']:.1%}    {res['hit_ou25']:.1%}      "
          f"{res['brier']:.3f}   {res['flagged_bias']:<9.2f}{res['ev_bets']:<8} {win_s:8} {roi_s}{marker}")

best_brier = min(results, key=lambda r: r["brier"])
best_bias = min(results, key=lambda r: r["flagged_bias"])
with_bets = [r for r in results if r["ev_bets"] > 0]
if with_bets:
    best_roi = max(with_bets, key=lambda r: r["ev_pnl"] / r["ev_bets"])
    print(f"\nMelhor ROI de EV (OU2.5): cy={best_roi['cy']} "
          f"(ROI={best_roi['ev_pnl']/best_roi['ev_bets']:+.1%}, n={best_roi['ev_bets']})")
print(f"Menor Brier (melhor calibracao 1X2): cy={best_brier['cy']} (Brier={best_brier['brier']:.3f})")
print(f"Menor vies nos times flagged: cy={best_bias['cy']} (vies={best_bias['flagged_bias']:.2f})")
