"""Batch: recalcula Elo e parâmetros do modelo e grava no cache (Parte 2).

Roda após cada ingestão (ou periodicamente). Tira o cálculo pesado do caminho
da CLI: o `predict` passa a só ler `current_elo` e `model_parameters`.
Grava um config_hash e um n_matches para a CLI detectar quando o cache ficou velho.
"""
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone

from . import db, model, ratings
from .ingest import ROOT, load_config


def config_hash(cfg) -> str:
    relevant = {"elo": cfg["elo"],
                "calibration_window_years": cfg["model"]["calibration_window_years"]}
    # so entra no hash quando ligado: manter o hash historico intacto com a
    # flag desligada evita invalidar o cache de quem nao usa o ensemble.
    if (cfg.get("ensemble_xg") or {}).get("enabled"):
        relevant["ensemble_xg"] = cfg["ensemble_xg"]
    blob = json.dumps(relevant, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def _windowed(cfg, conn):
    rows = conn.execute(
        "SELECT date, home_team, away_team, home_score, away_score, tournament, neutral "
        "FROM matches WHERE home_score IS NOT NULL ORDER BY date").fetchall()
    if not rows:
        return None
    window = cfg["elo"].get("window_years")
    if window:
        cut = (date.fromisoformat(rows[-1][0]) - timedelta(days=int(window * 365.25))).isoformat()
        rows = [r for r in rows if r[0] >= cut]
    return rows


def compute(cfg, conn):
    rows = _windowed(cfg, conn)
    if not rows:
        return None
    elo, history = ratings.compute_ratings(rows, cfg["elo"])
    cal_cut = (date.fromisoformat(rows[-1][0])
               - timedelta(days=int(cfg["model"]["calibration_window_years"] * 365.25))).isoformat()
    hist_cal = [h for h, r in zip(history, rows) if r[0] >= cal_cut]
    params = model.fit_goal_model(hist_cal)
    return elo, params, len(rows)


def compute_xg(cfg, conn):
    """Ajusta o modelo atk/def-xG (src/xg_model.py) com todos os jogos
    disputados da janela — walk-forward por construção (o cron só vê o
    passado). Devolve o dict de parâmetros ou None."""
    rows = _windowed(cfg, conn)
    if not rows:
        return None
    xg_map = {}
    for d, h, a, hx, ax in conn.execute(
            "SELECT date, home_team, away_team, home_xg, away_xg "
            "FROM sofascore_matches WHERE home_score IS NOT NULL"):
        xg_map[(d[:10], h, a)] = (hx, ax)
    from . import xg_model
    matches = [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
    return xg_model.fit(matches, xg_map, rows[-1][0], cfg.get("ensemble_xg"))


def run():
    cfg = load_config()
    conn = db.connect(str(ROOT / cfg["database"]))
    out = compute(cfg, conn)
    if not out:
        sys.exit("banco vazio — rode `python -m src.ingest` primeiro")
    elo, (a, b, alpha, rho), n = out
    n_total = conn.execute(
        "SELECT COUNT(*) FROM matches WHERE home_score IS NOT NULL").fetchone()[0]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db.save_elo(conn, list(elo.items()))
    db.save_params(conn, a, b, alpha, rho, n_total, config_hash(cfg), now)
    print(f"cache atualizado: {len(elo)} times | "
          f"a={a:.3f} b={b:.3f} alpha={alpha:.4f} rho={rho:.4f} | {n} jogos na janela")
    if (cfg.get("ensemble_xg") or {}).get("enabled"):
        xgp = compute_xg(cfg, conn)
        if xgp:
            db.save_xg_params(conn, xgp, n_total, config_hash(cfg), now)
            print(f"ensemble_xg atualizado: {len(xgp['atk'])} times | "
                  f"mu={xgp['mu']:.3f} ha={xgp['ha']:.3f} "
                  f"alpha={xgp['alpha']:.4f} rho={xgp['rho']:.4f} | "
                  f"{xgp['n_matches']} jogos"
                  + ("" if xgp["ok"] else " | AVISO: otimizacao nao convergiu"))


if __name__ == "__main__":
    run()
