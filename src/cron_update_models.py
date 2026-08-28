"""Batch: recalcula Elo e parâmetros do modelo e grava no cache (Parte 2).

Roda após cada ingestão (ou periodicamente). Tira o cálculo pesado do caminho
da CLI: o `predict` passa a só ler `current_elo` e `model_parameters`.
Grava um config_hash e um n_matches para a CLI detectar quando o cache ficou velho.
"""

import hashlib
import json
import sys
from datetime import UTC, date, datetime, timedelta

from . import db, model, ratings
from .ingest import ROOT, load_config

MODEL_ALGORITHM_VERSION = "nbdc-normalized-elo-horizon-v2"


def config_hash(cfg) -> str:
    relevant = {
        "model_algorithm_version": MODEL_ALGORITHM_VERSION,
        "elo": cfg["elo"],
        "calibration_window_years": cfg["model"]["calibration_window_years"],
        "goal_half_life_days": cfg["model"]["goal_half_life_days"],
    }
    # so entra no hash quando ligado: manter o hash historico intacto com a
    # flag desligada evita invalidar o cache de quem nao usa o ensemble.
    if (cfg.get("ensemble_xg") or {}).get("enabled"):
        relevant["ensemble_xg"] = cfg["ensemble_xg"]
    blob = json.dumps(relevant, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def cache_is_current(cfg, conn, params_row) -> bool:
    """True only when cached parameters match config and completed data."""
    if not params_row or len(params_row) < 7:
        return False
    n_now = conn.execute("SELECT COUNT(*) FROM matches WHERE home_score IS NOT NULL").fetchone()[0]
    return params_row[5] == config_hash(cfg) and params_row[4] == n_now


def _windowed(cfg, conn):
    rows = db.completed_matches_with_kickoff(conn)
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
    elo, history = ratings.compute_ratings(rows, cfg["elo"], asof=date.today())
    cal_cut = (
        date.fromisoformat(rows[-1][0]) - timedelta(days=int(cfg["model"]["calibration_window_years"] * 365.25))
    ).isoformat()
    hist_cal_rows = [(h, r) for h, r in zip(history, rows) if r[0] >= cal_cut]
    hist_cal = [h for h, _r in hist_cal_rows]
    fit_rows = [r for _h, r in hist_cal_rows]
    asof = date.fromisoformat(rows[-1][0][:10])
    weights = model.exponential_recency_weights([r[0] for r in fit_rows], asof, cfg["model"]["goal_half_life_days"])
    params = model.fit_goal_model(hist_cal, sample_weights=weights)
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
        "SELECT date, home_team, away_team, home_xg, away_xg FROM sofascore_matches WHERE home_score IS NOT NULL"
    ):
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
    elo, fitted_params, n = out
    a, b, alpha, rho = fitted_params[:4]
    n_total = conn.execute("SELECT COUNT(*) FROM matches WHERE home_score IS NOT NULL").fetchone()[0]
    now = datetime.now(UTC).isoformat(timespec="seconds")
    db.save_elo(conn, list(elo.items()))
    db.save_params(conn, a, b, alpha, rho, n_total, config_hash(cfg), now)
    print(
        f"cache atualizado: {len(elo)} times | "
        f"a={a:.3f} b={b:.3f} alpha={alpha:.4f} rho={rho:.4f} | {n} jogos na janela"
    )
    if (cfg.get("ensemble_xg") or {}).get("enabled"):
        xgp = compute_xg(cfg, conn)
        if xgp:
            db.save_xg_params(conn, xgp, n_total, config_hash(cfg), now)
            print(
                f"ensemble_xg atualizado: {len(xgp['atk'])} times | "
                f"mu={xgp['mu']:.3f} ha={xgp['ha']:.3f} "
                f"alpha={xgp['alpha']:.4f} rho={xgp['rho']:.4f} | "
                f"{xgp['n_matches']} jogos" + ("" if xgp["ok"] else " | AVISO: otimizacao nao convergiu")
            )


if __name__ == "__main__":
    run()
