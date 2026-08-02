"""h4_verdict_bootstrap — veredito final da H4: Dixon-Coles vs Elo puro (H₀).

Bootstrap PAREADO do RPS jogo-a-jogo:
  1. roda os DOIS avaliadores (BrasileiraoDixonColesEvaluator half_life=360d e
     EloBaselineEvaluator) sobre a MESMA lista de observações, mesmo
     min_history — o PrequentialEvaluator do core garante fatiamento idêntico;
     o alinhamento é verificado jogo-a-jogo (index + confronto) antes de
     qualquer subtração;
  2. ΔRPS_i = RPS_dixon_i − RPS_elo_i (negativo = DC erra menos);
  3. bootstrap vetorizado (numpy, 10.000 reamostras, seed=42) da média de Δ;
  4. IC 95% (percentis 2.5/97.5):
       teto < 0  → H4 COMPROVADA (redução de erro significativa);
       cruza 0   → H4 REFUTADA (diferença indistinguível de sorte);
  5. registra o veredito na trial H4_DIXON_COLES_CALIBRATED (mesmos params —
     a governança N+1 só permite atualizar notes/campos com params idênticos),
     com metric="rps" (punição global) e o IC documentado.

NOTA: `rps` vive em `predictor_core.measurement.metrics` (ordinal.py do core é
a camada Plackett-Luce, não a métrica).

Uso:  python scripts/h4_verdict_bootstrap.py [--cutoff 2026-07-11]
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry  # noqa: E402
from predictor_core.measurement.metrics import rps  # noqa: E402

from src.elo_baseline import EloBaselineEvaluator  # noqa: E402
from src.evaluator import BrasileiraoDixonColesEvaluator  # noqa: E402

DB = ROOT / "data" / "matches.db"
TRIALS = ROOT / "data" / "trials.json"
TRIAL_NAME = "H4_DIXON_COLES_CALIBRATED"
HALF_LIFE_WINNER = 360  # vencedor da varredura (run_h4_sweep, RPS=0.21132)
MIN_HISTORY = 200  # idêntico à varredura — mesmo conjunto de teste
RETRAIN_EVERY = 100
MAX_GOALS = 8
N_BOOT = 10_000
SEED = 42

log = logging.getLogger("h4_verdict")


def load_observations(cutoff: str) -> list[dict[str, Any]]:
    """Mesmo loader da varredura: jogos encerrados até cutoff, ordenados."""
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT date, home_team, away_team, home_score, away_score "
            "FROM matches WHERE home_score IS NOT NULL AND away_score IS NOT NULL "
            "AND date <= ? ORDER BY date",
            (cutoff,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "home": h,
            "away": a,
            "kickoff": datetime.fromisoformat(d).replace(tzinfo=UTC),
            "result": {"home_goals": int(hs), "away_goals": int(ag)},
        }
        for d, h, a, hs, ag in rows
    ]


def outcome_index(result: dict[str, int]) -> int:
    h, a = result["home_goals"], result["away_goals"]
    return 0 if h > a else (1 if h == a else 2)


def per_game_rps(results: list[dict[str, Any]]) -> list[float]:
    """RPS de CADA jogo (o vetor pareável), na ordem do walk-forward."""
    out: list[float] = []
    for r in results:
        v = r["prediction"].value
        out.append(rps([[v["home"], v["draw"], v["away"]]], [outcome_index(r["actual"])]))
    return out


def assert_aligned(dc: list[dict[str, Any]], elo: list[dict[str, Any]]) -> None:
    """Pareamento estrutural: mesmo tamanho, mesmo index, MESMO confronto por
    posição. Qualquer divergência aborta antes de subtrair um único RPS."""
    if len(dc) != len(elo):
        raise AssertionError(f"séries de tamanhos diferentes: {len(dc)} vs {len(elo)}")
    for a, b in zip(dc, elo):
        if a["index"] != b["index"]:
            raise AssertionError(f"index divergente: {a['index']} vs {b['index']}")
        ma, mb = a["prediction"].metadata, b["prediction"].metadata
        if (ma["home"], ma["away"]) != (mb["home"], mb["away"]):
            raise AssertionError(
                f"confronto divergente no index {a['index']}: {ma['home']}x{ma['away']} vs {mb['home']}x{mb['away']}"
            )


def paired_bootstrap_ci(delta: np.ndarray, *, n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    """IC 95% da MÉDIA de Δ por bootstrap vetorizado (sem loop Python):
    matriz (n_boot × n) de índices reamostrados, média no eixo 1, percentis."""
    np.random.seed(seed)
    n = delta.shape[0]
    idx = np.random.choice(n, size=(n_boot, n), replace=True)
    means = delta[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", default=date.today().isoformat())
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    observations = load_observations(args.cutoff)
    log.info("base: %d jogos encerrados até %s", len(observations), args.cutoff)

    # --- braço H4: Dixon-Coles vencedor -------------------------------------
    t0 = time.perf_counter()
    log.info("braço H4: Dixon-Coles half_life=%dd (walk-forward)...", HALF_LIFE_WINNER)
    dc_ev = BrasileiraoDixonColesEvaluator(half_life_days=float(HALF_LIFE_WINNER), max_goals=MAX_GOALS)
    dc_results = dc_ev.run(observations, min_history=MIN_HISTORY, retrain_every=RETRAIN_EVERY)
    log.info("braço H4: %d previsões em %.0fs", len(dc_results), time.perf_counter() - t0)

    # --- braço H0: Elo puro ---------------------------------------------------
    t0 = time.perf_counter()
    log.info("braço H0: Elo puro (walk-forward, retrain a cada jogo)...")
    elo_ev = EloBaselineEvaluator()
    elo_results = elo_ev.run(observations, min_history=MIN_HISTORY, retrain_every=1)
    log.info("braço H0: %d previsões em %.0fs", len(elo_results), time.perf_counter() - t0)

    # --- pareamento + delta ---------------------------------------------------
    assert_aligned(dc_results, elo_results)
    rps_dc = np.array(per_game_rps(dc_results))
    rps_elo = np.array(per_game_rps(elo_results))
    delta = rps_dc - rps_elo
    log.info(
        "pareado: n=%d | RPS médio DC=%.5f | Elo=%.5f | ΔRPS médio=%.5f",
        delta.shape[0],
        rps_dc.mean(),
        rps_elo.mean(),
        delta.mean(),
    )

    # --- bootstrap ------------------------------------------------------------
    lo, hi = paired_bootstrap_ci(delta)
    log.info("bootstrap %d reamostras (seed=%d): IC95%% de ΔRPS = [%.5f, %.5f]", N_BOOT, SEED, lo, hi)

    if hi < 0:
        status, verdict_txt = "comprovada", "H4 COMPROVADA"
        detail = "IC 95% estritamente negativo — o DC reduz o erro ordinal com significância"
    else:
        status, verdict_txt = "refutada", "H4 REFUTADA"
        detail = (
            "IC 95% cruza zero — a redução de erro sobre o Elo puro é indistinguível de sorte"
            if lo < 0
            else "IC 95% estritamente positivo — o DC erra MAIS que o Elo puro"
        )
    log.info("VEREDITO: %s (%s)", verdict_txt, detail)

    # --- registro (params idênticos aos da varredura → update permitido) -----
    registry = TrialRegistry(TRIALS)
    existing = next((t for t in registry.load() if t["name"] == TRIAL_NAME), None)
    if existing is None:
        log.error("trial %s não encontrada — rode run_h4_sweep.py antes", TRIAL_NAME)
        return 1
    registry.register(
        TRIAL_NAME,
        params=existing["params"],  # idênticos: N+1 permite atualizar
        sharpe=existing.get("sharpe"),
        notes=(
            existing.get("notes", "") + f" | VEREDITO ({date.today().isoformat()}): {verdict_txt} vs Elo puro — "
            f"ΔRPS médio={delta.mean():.5f}, IC95%=[{lo:.5f}, {hi:.5f}], "
            f"bootstrap n={N_BOOT} seed={SEED}, pareado n={delta.shape[0]}. {detail}"
        ),
        metric="rps",
        status=status,
        rps_dixon=float(rps_dc.mean()),
        rps_elo_baseline=float(rps_elo.mean()),
        delta_rps_ci95=[lo, hi],
    )
    log.info("trial '%s' atualizada com status='%s' em %s", TRIAL_NAME, status, TRIALS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
