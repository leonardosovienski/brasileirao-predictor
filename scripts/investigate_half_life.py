"""Investigacao de causa raiz: sera que form_half_life_years=4.0 (config.yaml)
esta pesando demais o historico 2024/25 e causando o vies persistente visto em
N=18 e N=40 (Palmeiras/Gremio/Botafogo superestimados pra baixo, Internacional
pra cima, Cruzeiro mal calibrado em defesa)?

Varre form_half_life_years num grid e recomputa TUDO — Elo forward, params do
Poisson (calibrados so com pre-temporada), previsao dos jogos de teste — pra
cada valor. Mede: Brier medio (1X2), hit-rate 1X2/OU2.5, e o vies acumulado
nos 5 times que carregaram o erro nas duas marcas anteriores (metrica local
que mais interessa, ja que ela e' quem motivou a investigacao).

Read-only: NAO toca em config.yaml. So reporta o grid pra decisao humana.

Uso: python scripts/investigate_half_life.py [N_JOGOS]  (default 40)
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.getcwd())
from src import db, model, ratings
from src.ingest import ROOT, load_config

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

FIRST_SEASON_DATE = "2026-01-28"
cy = cfg["model"].get("calibration_window_years")
ccut = (date.fromisoformat(FIRST_SEASON_DATE) - timedelta(days=int(cy * 365.25))).isoformat()
MAXG = cfg["model"]["max_goals"]

# times que carregaram o vies em N=18 E N=40 (do relatorio) — foco da investigacao
FLAGGED_TEAMS = {"Palmeiras", "Grêmio", "Botafogo", "Internacional", "Cruzeiro"}


def outcome(hs, as_):
    if hs > as_:
        return "H"
    if hs < as_:
        return "A"
    return "D"


def brier(ph, pd, pa, real):
    yh, yd, ya = (1, 0, 0) if real == "H" else ((0, 1, 0) if real == "D" else (0, 0, 1))
    return (ph - yh) ** 2 + (pd - yd) ** 2 + (pa - ya) ** 2


def run(half_life):
    elo_cfg = dict(cfg["elo"])
    elo_cfg["form_half_life_years"] = half_life  # None = sem decaimento (baseline extremo)
    _, history = ratings.compute_ratings(rows_all, elo_cfg)

    test_idx = [i for i, r in enumerate(rows_all)
                if r[5].startswith("Brasileir") and r[0] >= FIRST_SEASON_DATE][:N_GAMES]

    params = model.fit_goal_model(
        [h for h, r in zip(history, rows_all) if ccut <= r[0] < FIRST_SEASON_DATE])

    hits_1x2 = hits_ou = 0
    brier_total = 0.0
    flagged_bias = 0.0   # soma de |ΔAtaque|+|ΔDefesa| dos 5 times flagged
    team_xgf = {}
    team_gf = {}
    team_xga = {}
    team_ga = {}

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
        ou_pred = "OVER" if p_over >= 0.5 else "UNDER"
        ou_real = "OVER" if (hs + as_) > 2.5 else "UNDER"
        hits_ou += int(ou_pred == ou_real)

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
        "half_life": half_life,
        "n": n,
        "hit_1x2": hits_1x2 / n,
        "hit_ou25": hits_ou / n,
        "brier": brier_total / n,
        "flagged_bias": flagged_bias,
    }


GRID = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, None]

print(f"Investigando form_half_life_years em N={N_GAMES} jogos (config atual: "
      f"{cfg['elo'].get('form_half_life_years')})\n")
print(f"{'half_life':10} {'hit_1X2':9} {'hit_OU2.5':10} {'Brier':8} {'vies_flagged':13}")
results = []
for hl in GRID:
    res = run(hl)
    results.append(res)
    hl_s = "None" if hl is None else f"{hl:.1f}"
    marker = "  <- config atual" if hl == cfg["elo"].get("form_half_life_years") else ""
    print(f"{hl_s:10} {res['hit_1x2']:.1%}     {res['hit_ou25']:.1%}      "
          f"{res['brier']:.3f}    {res['flagged_bias']:.2f}{marker}")

best_brier = min(results, key=lambda r: r["brier"])
best_bias = min(results, key=lambda r: r["flagged_bias"])
print(f"\nMenor Brier (melhor calibracao 1X2): half_life={best_brier['half_life']} "
      f"(Brier={best_brier['brier']:.3f})")
print(f"Menor vies nos times flagged: half_life={best_bias['half_life']} "
      f"(vies={best_bias['flagged_bias']:.2f})")
