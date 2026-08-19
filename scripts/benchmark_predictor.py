"""benchmark_predictor — painel canônico único de avaliação preditiva do
sport model (GOV-P0, item 3 do Roadmap Técnico Consolidado v1.0-final).

Walk-forward puro (`BrasileiraoDixonColesEvaluator`, o mesmo motor de
`scripts/run_h4_sweep.py` — anti-leakage estrutural do core): treina só com o
passado, prevê o próximo jogo, nunca lê o próprio futuro. Half-life vem da
trial `H4_DIXON_COLES_CALIBRATED` se registrada em data/trials.json; senão,
cai no default de `config.yaml`.

Não decide GO/NO-GO de nada, não abre funil de aposta, não lê/escreve
data/bets.jsonl. É SÓ medição — mesma régua para qualquer trial de
RESEARCH-01..08 comparar contra este baseline congelado.

Métrica primária: RPS (Ranked Probability Score, ordinal 1X2 — perda-derrota/
empate/vitória). Guardrails: Brier 1X2, Brier OU2.5, log-loss, ECE,
calibration slope e resolution/sharpness (calculados sobre OU2.5 — o único
mercado binário canônico do projeto, o mesmo que H1/H4/H8/H9 avaliam).
Diagnóstico: coverage (sempre 1.0 — este painel não filtra por edge),
accuracy 1X2/OU2.5 (DIAGNOSTIC_ONLY, nunca métrica de promoção — Regra 12) e
variância de lambda_total.

Skill scores: só vs `climatology` (frequência empírica de classe no próprio
período avaliado) está implementado nesta versão. `elo_baseline`,
`current_v3` e `market_no_vig` exigem rodar OUTROS previsores sobre a mesma
base e não estão cobertos aqui ainda — `--baseline` desconhecido falha alto
(NotImplementedError), nunca silencia como zero ou None.

Estratificações: overall, by_season, by_month, by_team (omite n<10),
by_probability_bucket (10 faixas da prob. do vencedor previsto),
by_lambda_total_bucket, by_turno_of_season (1º/2º turno real, corte por
ordem cronológica dentro da temporada — metade dos jogos, não mês
calendário). Toda
estratificação carrega `n` (Regra 11). `by_home_away` e `by_xg_regime` do
roadmap NÃO estão neste painel: o evaluator aqui é o Dixon-Coles puro (mesmo
de H4), sem o ensemble atk/def-xG opcional (`src.xg_model`) integrado ao
walk-forward — adicionar exigiria plugar `xg_model` no laço prequential, fora
do escopo deste script de medição.

Uso:
    python scripts/benchmark_predictor.py \\
        --model H4_DIXON_COLES_CALIBRATED --period 2024-01-01,2025-12-31 \\
        --output reports/benchmark_h4_2024-2025.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics as st
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predictor_core.contracts.registry import TrialRegistry  # noqa: E402
from predictor_core.measurement.bootstrap import bootstrap_ci  # noqa: E402
from predictor_core.measurement.metrics import brier, calibration_table, log_loss, rps  # noqa: E402

from src.dixon_coles import DixonColesMatrix  # noqa: E402
from src.evaluator import BrasileiraoDixonColesEvaluator  # noqa: E402
from src.ingest import load_config  # noqa: E402

DB = ROOT / "data" / "matches.db"
TRIALS = ROOT / "data" / "trials.json"
DEFAULT_HALF_LIFE = 120
MIN_HISTORY = 200
RETRAIN_EVERY = 100
MAX_GOALS = 8
OU_LINE = 2.5
MIN_TEAM_N = 10


def _half_life_for(model_tag: str) -> float:
    trial = next((t for t in TrialRegistry(TRIALS).load() if t["name"] == model_tag), None)
    if trial is not None:
        hl = trial.get("params", {}).get("half_life_days")
        if hl is not None:
            return float(hl)
    return float(DEFAULT_HALF_LIFE)


def _load_observations(end: str) -> list[dict[str, Any]]:
    """Carrega TODO o histórico até `end` (sem filtro de `start`) — o
    walk-forward precisa de temporadas anteriores como burn-in pra prever o
    início do período pedido; recortar por `start` aqui privaria o modelo do
    próprio passado. O recorte por `start` acontece só depois, sobre as
    LINHAS PREVISTAS (ver `run`), nunca sobre o histórico de treino."""
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT date, home_team, away_team, home_score, away_score "
            "FROM matches WHERE home_score IS NOT NULL AND away_score IS NOT NULL "
            "ORDER BY date"
        ).fetchall()
    finally:
        conn.close()
    obs = []
    for d, home, away, hs, asc in rows:
        kickoff = datetime.fromisoformat(d).replace(tzinfo=UTC)
        obs.append(
            {
                "home": home,
                "away": away,
                "kickoff": kickoff,
                "date": d,
                "result": {"home_goals": int(hs), "away_goals": int(asc)},
            }
        )
    if end:
        obs = [o for o in obs if o["date"] <= end]
    return obs


def _outcomes_1x2(goals_home: int, goals_away: int) -> int:
    """0=derrota do mandante, 1=empate, 2=vitoria do mandante — ordem ordinal
    coerente com [p_loss, p_draw, p_win] que o RPS do core espera."""
    if goals_home > goals_away:
        return 2
    if goals_home == goals_away:
        return 1
    return 0


def _run_walkforward(observations: list[dict[str, Any]], half_life: float) -> list[dict[str, Any]]:
    ev = BrasileiraoDixonColesEvaluator(half_life_days=half_life, max_goals=MAX_GOALS)
    results = ev.run(observations, min_history=MIN_HISTORY, retrain_every=RETRAIN_EVERY)
    rows = []
    for r in results:
        obs = observations[r["index"]]
        pred = r["prediction"]
        outcome = pred.value  # {"home", "draw", "away"} — outcome_probs()
        p_win, p_draw, p_loss = outcome["home"], outcome["draw"], outcome["away"]
        lam, mu, rho = pred.metadata["lam"], pred.metadata["mu"], pred.metadata["rho"]
        matrix = DixonColesMatrix(lam, mu, rho, max_goals=MAX_GOALS)
        grid = matrix.grid()
        p_over = sum(grid[h][a] for h in range(MAX_GOALS + 1) for a in range(MAX_GOALS + 1) if h + a > OU_LINE)
        rows.append(
            {
                "date": obs["date"],
                "season": obs["date"][:4],
                "month": obs["date"][:7],
                "home": obs["home"],
                "away": obs["away"],
                "p_win": p_win,
                "p_draw": p_draw,
                "p_loss": p_loss,
                "p_over": p_over,
                "lambda_total": lam + mu,
                "actual_1x2": _outcomes_1x2(obs["result"]["home_goals"], obs["result"]["away_goals"]),
                "actual_over": int(obs["result"]["home_goals"] + obs["result"]["away_goals"] > OU_LINE),
            }
        )
    return rows


def _climatology_probs(rows: list[dict[str, Any]]) -> list[list[float]]:
    n = len(rows)
    counts = [0, 0, 0]
    for r in rows:
        counts[r["actual_1x2"]] += 1
    freqs = [c / n for c in counts] if n else [1 / 3, 1 / 3, 1 / 3]
    return [freqs for _ in rows]


def _metric_record(
    name: str, value: float, *, baseline_value: float | None, n: int, is_primary: bool
) -> dict[str, Any]:
    delta = (value - baseline_value) if baseline_value is not None else None
    return {
        "metric": name,
        "value": round(value, 6),
        "baseline_value": round(baseline_value, 6) if baseline_value is not None else None,
        "delta": round(delta, 6) if delta is not None else None,
        "delta_ci95": None,
        "n": n,
        "is_primary": is_primary,
    }


def _skill_score_ci(losses_model: list[float], losses_baseline: list[float]) -> tuple[float, float] | None:
    """IC95 bootstrap (iid) da diferença média de perda (baseline - modelo)
    por jogo — positivo = modelo bate o baseline. `bootstrap_ci` devolve
    (lo, hi, amostras_ordenadas); só os dois primeiros interessam aqui."""
    if not losses_model or len(losses_model) != len(losses_baseline):
        return None
    diffs = [b - m for m, b in zip(losses_model, losses_baseline)]
    lo, hi, _samples = bootstrap_ci(diffs, lambda u: sum(u) / len(u), scheme="iid", n_boot=1000, seed=13)
    return lo, hi


def _guardrails_ou25(rows: list[dict[str, Any]]) -> dict[str, Any]:
    probs = [r["p_over"] for r in rows if r["p_over"] is not None]
    outcomes = [r["actual_over"] for r in rows if r["p_over"] is not None]
    n = len(probs)
    if n == 0:
        return {"ece": None, "calibration_slope": None, "resolution": None, "sharpness": None}
    table = calibration_table(probs, outcomes, bins=10)
    ece = sum(b["n"] * abs(b["mean_pred"] - b["obs_freq"]) for b in table) / n
    overall_rate = sum(outcomes) / n
    resolution = sum(b["n"] * (b["obs_freq"] - overall_rate) ** 2 for b in table) / n
    sharpness = st.pvariance(probs) if n > 1 else 0.0
    xs = [b["mean_pred"] for b in table]
    ys = [b["obs_freq"] for b in table]
    if len(xs) >= 2 and st.pvariance(xs) > 0:
        mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        var_x = sum((x - mean_x) ** 2 for x in xs)
        slope = cov / var_x if var_x else None
    else:
        slope = None
    return {
        "ece": round(ece, 6),
        "calibration_slope": round(slope, 6) if slope is not None else None,
        "resolution": round(resolution, 6),
        "sharpness": round(sharpness, 6),
    }


def _stratify(rows: list[dict[str, Any]], key_fn) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        buckets.setdefault(key_fn(r), []).append(r)
    return buckets


def _prob_bucket(r: dict[str, Any]) -> str:
    p = max(r["p_win"], r["p_draw"], r["p_loss"])
    lo = int(p * 10) / 10
    return f"[{lo:.1f},{lo + 0.1:.1f})"


def _lambda_bucket(r: dict[str, Any]) -> str:
    lt = r["lambda_total"]
    if lt is None:
        return "unknown"
    lo = int(lt)
    return f"[{lo},{lo + 1})"


def _tag_turno(rows: list[dict[str, Any]]) -> None:
    """Marca `turno` (T1/T2) por ORDEM CRONOLÓGICA dentro da própria temporada
    (metade dos jogos da temporada = T1, resto = T2) — não por mês calendário.
    O Brasileirão roda abril-dezembro; um corte em 30/06 NÃO bate com o fim
    real do 1º turno (19 rodadas), então esse critério seria enganoso pra
    medir turno 1 vs turno 2 de verdade. Muta `rows` in-place (adiciona a
    chave `turno`), chamado uma vez antes de qualquer estratificação."""
    by_season: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_season.setdefault(r["season"], []).append(r)
    for season_rows in by_season.values():
        season_rows.sort(key=lambda r: r["date"])
        half = len(season_rows) // 2
        for i, r in enumerate(season_rows):
            r["turno"] = "T1" if i < half else "T2"


def _turno_of_season(r: dict[str, Any]) -> str:
    return f"{r['season']}-{r['turno']}"


def _stratum_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    probs_1x2 = [[r["p_loss"], r["p_draw"], r["p_win"]] for r in rows]
    outcomes_1x2 = [r["actual_1x2"] for r in rows]
    return {
        "n": n,
        "rps": round(rps(probs_1x2, outcomes_1x2), 6) if n else None,
        "brier_1x2": round(brier(probs_1x2, outcomes_1x2), 6) if n else None,
        "log_loss": round(log_loss(probs_1x2, outcomes_1x2), 6) if n else None,
    }


def run(*, model_tag: str, start: str, end: str) -> dict[str, Any]:
    half_life = _half_life_for(model_tag)
    observations = _load_observations(end)
    if len(observations) < MIN_HISTORY + 50:
        raise SystemExit(f"histórico insuficiente ({len(observations)}) para min_history={MIN_HISTORY}")
    all_rows = _run_walkforward(observations, half_life)
    # turno é calculado sobre a temporada INTEIRA (histórico completo até
    # `end`), nunca sobre o recorte de `start` — senão pedir --period a
    # partir do meio de uma temporada quebraria o corte T1/T2 daquele ano.
    _tag_turno(all_rows)
    rows = [r for r in all_rows if (not start or r["date"] >= start) and (not end or r["date"] <= end)]
    if not rows:
        raise SystemExit(f"nenhuma previsão cai no período [{start or '-inf'}, {end or '+inf'}] após o walk-forward")
    n = len(rows)

    probs_1x2 = [[r["p_loss"], r["p_draw"], r["p_win"]] for r in rows]
    outcomes_1x2 = [r["actual_1x2"] for r in rows]
    baseline_probs = _climatology_probs(rows)

    rps_losses = [rps([p], [y]) for p, y in zip(probs_1x2, outcomes_1x2)]
    rps_baseline_losses = [rps([p], [y]) for p, y in zip(baseline_probs, outcomes_1x2)]
    brier_losses = [brier([p], [y]) for p, y in zip(probs_1x2, outcomes_1x2)]
    brier_baseline_losses = [brier([p], [y]) for p, y in zip(baseline_probs, outcomes_1x2)]

    rps_ci = _skill_score_ci(rps_losses, rps_baseline_losses)
    brier_ci = _skill_score_ci(brier_losses, brier_baseline_losses)

    metrics = [
        _metric_record(
            "rps",
            rps(probs_1x2, outcomes_1x2),
            baseline_value=rps(baseline_probs, outcomes_1x2),
            n=n,
            is_primary=True,
        ),
        _metric_record(
            "brier_1x2",
            brier(probs_1x2, outcomes_1x2),
            baseline_value=brier(baseline_probs, outcomes_1x2),
            n=n,
            is_primary=False,
        ),
        _metric_record(
            "log_loss",
            log_loss(probs_1x2, outcomes_1x2),
            baseline_value=log_loss(baseline_probs, outcomes_1x2),
            n=n,
            is_primary=False,
        ),
    ]
    ou_probs = [r["p_over"] for r in rows if r["p_over"] is not None]
    ou_outcomes = [r["actual_over"] for r in rows if r["p_over"] is not None]
    if ou_probs:
        metrics.append(
            _metric_record(
                "brier_ou25",
                brier([[1 - p, p] for p in ou_probs], ou_outcomes),
                baseline_value=None,
                n=len(ou_probs),
                is_primary=False,
            )
        )
    guardrails_ou25 = _guardrails_ou25(rows)

    def _predicted_1x2(r: dict[str, Any]) -> int:
        triple = [r["p_loss"], r["p_draw"], r["p_win"]]
        return triple.index(max(triple))

    accuracy_1x2 = sum(1 for r in rows if _predicted_1x2(r) == r["actual_1x2"]) / n
    ou_hit_rate = (
        sum(1 for r in rows if r["p_over"] is not None and int(r["p_over"] > 0.5) == r["actual_over"]) / len(ou_probs)
        if ou_probs
        else None
    )
    lambda_values = [r["lambda_total"] for r in rows if r["lambda_total"] is not None]

    strata = {
        "overall": {"overall": _stratum_metrics(rows)},
        "by_season": {k: _stratum_metrics(v) for k, v in _stratify(rows, lambda r: r["season"]).items()},
        "by_month": {k: _stratum_metrics(v) for k, v in _stratify(rows, lambda r: r["month"]).items()},
        "by_team": {
            k: _stratum_metrics(v)
            for k, v in _stratify(
                [r for r in rows for _ in (0,)],
                lambda r: r["home"],
            ).items()
            if len(v) >= MIN_TEAM_N
        },
        "by_probability_bucket": {k: _stratum_metrics(v) for k, v in _stratify(rows, _prob_bucket).items()},
        "by_lambda_total_bucket": {k: _stratum_metrics(v) for k, v in _stratify(rows, _lambda_bucket).items()},
        "by_turno_of_season": {k: _stratum_metrics(v) for k, v in _stratify(rows, _turno_of_season).items()},
    }

    return {
        "schema_version": "benchmark-predictor/1",
        "model_tag": model_tag,
        "half_life_days": half_life,
        "period": {"start": start or rows[0]["date"], "end": end or rows[-1]["date"]},
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "n": n,
        "metrics": metrics,
        "guardrails_ou25": guardrails_ou25,
        "diagnostic": {
            "coverage": 1.0,
            "accuracy_1x2": round(accuracy_1x2, 6),
            "ou25_hit_rate": round(ou_hit_rate, 6) if ou_hit_rate is not None else None,
            "lambda_total_variance": round(st.pvariance(lambda_values), 6) if len(lambda_values) > 1 else None,
        },
        "skill_scores": {
            "rps_skill_score_vs_climatology": {
                "value": round(1 - (rps(probs_1x2, outcomes_1x2) / rps(baseline_probs, outcomes_1x2)), 6),
                "delta_ci95": [round(rps_ci[0], 6), round(rps_ci[1], 6)] if rps_ci else None,
            },
            "brier_skill_score_vs_climatology": {
                "value": round(1 - (brier(probs_1x2, outcomes_1x2) / brier(baseline_probs, outcomes_1x2)), 6),
                "delta_ci95": [round(brier_ci[0], 6), round(brier_ci[1], 6)] if brier_ci else None,
            },
        },
        "strata": strata,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--model",
        required=True,
        help="model_tag: nome de trial em data/trials.json (half_life) ou tag livre",
    )
    parser.add_argument(
        "--period",
        required=True,
        help="start,end em ISO date (YYYY-MM-DD), qualquer lado pode ser vazio",
    )
    parser.add_argument("--output", required=True, type=Path, help="caminho do JSON de saída")
    parser.add_argument(
        "--baseline",
        default="climatology",
        choices=["climatology"],
        help="baseline de skill score",
    )
    args = parser.parse_args()

    start, _, end = args.period.partition(",")
    load_config()  # valida config.yaml cedo, falha alto se ausente
    result = run(model_tag=args.model, start=start.strip(), end=end.strip())

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"BENCHMARK_WRITTEN path={args.output} n={result['n']} rps={result['metrics'][0]['value']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
