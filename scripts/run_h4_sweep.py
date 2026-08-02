"""run_h4_sweep — varredura H4: half-life do decaimento temporal do Dixon-Coles.

Orquestra o ciclo completo de governança:
  1. varre half_life ∈ {30, 60, 90, 120, 180, 360} dias;
  2. para cada janela, roda o walk-forward (BrasileiraoDixonColesEvaluator,
     herdeiro do PrequentialEvaluator do core — anti-leakage estrutural);
  3. liquida cada janela pelo RPS médio (métrica ordinal canônica do 1X2 —
     `predictor_core.measurement.metrics.rps`; NOTA: rps vive em `metrics`,
     não em `ordinal` — ordinal.py é a camada Plackett-Luce);
  4. para o VENCEDOR (menor RPS): emite o atestado de controle positivo com
     metric="rps" (attest_pipeline_power) e registra a trial no cofre
     data/trials.json com metric="rps" — satisfazendo a punição global
     (MetricMismatchError se a métrica atestada divergisse da registrada).

Uso:  python scripts/run_h4_sweep.py [--quick]
      --quick: grade reduzida e retrain esparso (smoke test da esteira).
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry, attestation_path_for  # noqa: E402
from predictor_core.measurement.bootstrap import bootstrap_ci  # noqa: E402
from predictor_core.measurement.metrics import rps  # noqa: E402
from predictor_core.testing.harness import attest_pipeline_power  # noqa: E402
from predictor_core.testing.synth import probabilistic_predictor  # noqa: E402

from src.evaluator import BrasileiraoDixonColesEvaluator  # noqa: E402

DB = ROOT / "data" / "matches.db"
TRIALS = ROOT / "data" / "trials.json"
HALF_LIFE_GRID: list[int] = [30, 60, 90, 120, 180, 360]
TRIAL_NAME = "H4_DIXON_COLES_CALIBRATED"
MIN_HISTORY = 200  # ~1 temporada de burn-in antes da 1ª previsão
RETRAIN_EVERY = 100  # reajusta o MLE a cada ~10 rodadas (custo ~30s/fit)
MAX_GOALS = 8

log = logging.getLogger("h4_sweep")


# ---------- dados ----------


def load_observations(cutoff: str) -> list[dict[str, Any]]:
    """Jogos ENCERRADOS até `cutoff`, ordenados, no formato do evaluator
    (gols dentro de `result` — o target blindado pelo core)."""
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
    obs: list[dict[str, Any]] = []
    for d, home, away, hs, asc in rows:
        kickoff = datetime.fromisoformat(d).replace(tzinfo=UTC)
        obs.append(
            {
                "home": home,
                "away": away,
                "kickoff": kickoff,
                "result": {"home_goals": int(hs), "away_goals": int(asc)},
            }
        )
    return obs


def outcome_index(result: dict[str, int]) -> int:
    """1X2 ordinal: 0=casa, 1=empate, 2=fora (a ordem que o RPS pune por distância)."""
    h, a = result["home_goals"], result["away_goals"]
    return 0 if h > a else (1 if h == a else 2)


# ---------- varredura ----------


def sweep_one(
    half_life: int, observations: list[dict[str, Any]], *, min_history: int, retrain_every: int
) -> dict[str, Any]:
    """Walk-forward de uma janela: retorna RPS médio + série por-jogo."""
    t0 = time.perf_counter()
    ev = BrasileiraoDixonColesEvaluator(half_life_days=float(half_life), max_goals=MAX_GOALS)
    log.info(
        "half_life=%3dd | xi=%.5f | walk-forward sobre %d jogos (min_history=%d, retrain_every=%d)...",
        half_life,
        ev.xi,
        len(observations),
        min_history,
        retrain_every,
    )
    results = ev.run(observations, min_history=min_history, retrain_every=retrain_every)
    probs = [
        [
            r["prediction"].value["home"],
            r["prediction"].value["draw"],
            r["prediction"].value["away"],
        ]
        for r in results
    ]
    outcomes = [outcome_index(r["actual"]) for r in results]
    mean_rps = rps(probs, outcomes)
    elapsed = time.perf_counter() - t0
    log.info(
        "half_life=%3dd | RPS=%.5f | %d previsões | rho=%.4f gamma=%.3f | %.1fs",
        half_life,
        mean_rps,
        len(results),
        ev.fitted_parameters["rho"],
        ev.fitted_parameters["home_advantage"],
        elapsed,
    )
    return {
        "half_life": half_life,
        "rps": mean_rps,
        "n_predictions": len(results),
        "probs": probs,
        "outcomes": outcomes,
        "elapsed_s": elapsed,
        "final_rho": ev.fitted_parameters["rho"],
    }


# ---------- controle positivo (harness, metric="rps") ----------


def _rps_pipeline(series: tuple[list[list[float]], list[int]]) -> dict[str, str]:
    """Pipeline de veredito por RPS: COMPROVADA se o IC bootstrap 95% do ganho
    de RPS sobre o baseline uniforme excluir zero por baixo (o previsor informa
    MAIS que o chute uniforme); senão REFUTADA."""
    probs, outcomes = series
    uniform = [1 / 3, 1 / 3, 1 / 3]
    gains = [rps([uniform], [y]) - rps([p], [y]) for p, y in zip(probs, outcomes)]
    lo, _, _ = bootstrap_ci(gains, lambda u: sum(u) / len(u), scheme="iid", n_boot=500, seed=13)
    return {"verdict": "COMPROVADA" if (lo is not None and lo > 0) else "REFUTADA"}


def attest_rps_power() -> dict[str, Any]:
    """Controle positivo com a MESMA régua da varredura (RPS ordinal):
    o gerador de edge produz previsões informativas (synth do core), o de
    ruído produz chutes não-informativos — o pipeline tem de separar os dois."""

    def edge():
        return probabilistic_predictor(300, skill_level=0.6, seed=13, n_classes=3)

    def noise():
        return probabilistic_predictor(300, skill_level=0.0, seed=17, n_classes=3)

    return attest_pipeline_power(
        _rps_pipeline,
        edge,
        noise,
        attestation_path=attestation_path_for(TRIALS),
        note="H4: controle positivo da régua RPS (edge sintético k=3 detectado, ruído uniforme rejeitado)",
        metric="rps",
    )


# ---------- main ----------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="grade reduzida + retrain esparso (smoke da esteira)")
    parser.add_argument("--cutoff", default=date.today().isoformat(), help="data máxima dos jogos (default: hoje)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    grid = [90, 360] if args.quick else HALF_LIFE_GRID
    retrain = 250 if args.quick else RETRAIN_EVERY

    observations = load_observations(args.cutoff)
    log.info("base: %d jogos encerrados até %s | grade: %s", len(observations), args.cutoff, grid)
    if len(observations) < MIN_HISTORY + 50:
        log.error("histórico insuficiente (%d) para min_history=%d", len(observations), MIN_HISTORY)
        return 1

    t0 = time.perf_counter()
    sweep = [sweep_one(hl, observations, min_history=MIN_HISTORY, retrain_every=retrain) for hl in grid]
    total = time.perf_counter() - t0

    sweep.sort(key=lambda s: s["rps"])
    log.info("---- resultado da varredura (%.1f min) ----", total / 60)
    for s in sweep:
        log.info(
            "  half_life=%3dd  RPS=%.5f  (n=%d, %.0fs)",
            s["half_life"],
            s["rps"],
            s["n_predictions"],
            s["elapsed_s"],
        )
    winner = sweep[0]
    log.info("VENCEDOR: half_life=%dd (RPS=%.5f)", winner["half_life"], winner["rps"])

    # Governança: atestado (metric="rps") ANTES do registro — a punição global
    # barraria a trial se a métrica atestada não fosse a registrada.
    log.info("emitindo atestado de controle positivo (metric='rps')...")
    record = attest_rps_power()
    log.info("atestado OK (passed_at=%s)", record["passed_at"])

    registry = TrialRegistry(TRIALS)
    registry.register(
        TRIAL_NAME,
        params={
            "model": "dixon_coles_wnll",
            "half_life_days": winner["half_life"],
            "min_history": MIN_HISTORY,
            "retrain_every": retrain,
            "max_goals": MAX_GOALS,
            "grid": grid,
            "cutoff": args.cutoff,
        },
        sharpe=None,
        notes=(
            f"H4: varredura de half-life por walk-forward. "
            f"RPS={winner['rps']:.5f} (n={winner['n_predictions']}), "
            f"rho_final={winner['final_rho']:.4f}. "
            f"Grade completa: " + "; ".join(f"{s['half_life']}d={s['rps']:.5f}" for s in sweep)
        ),
        metric="rps",
    )
    log.info(
        "trial '%s' registrada em %s (N=%d tentativas no cofre)",
        TRIAL_NAME,
        TRIALS,
        len(registry.load()),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
