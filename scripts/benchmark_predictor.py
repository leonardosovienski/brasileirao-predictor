"""benchmark_predictor — painel canônico único de avaliação preditiva do
sport model (GOV-P0, item 3 do Roadmap Técnico Consolidado v1.0-final).

Walk-forward puro (`BrasileiraoDixonColesEvaluator`, o mesmo motor de
`scripts/run_h4_sweep.py` — anti-leakage estrutural do core): treina só com o
passado, prevê o próximo jogo, nunca lê o próprio futuro. As observações são
ordenadas pelo KICKOFF REAL (`sofascore_matches.kickoff_at`), não pela
data-sem-hora de `matches` — a ordem da lista É o passado para a ABC
prequential, e ordenar por dia deixaria a sequência dentro de uma rodada ao
sabor do SQLite. Jogos simultâneos ficam fora do treino um do outro pela
guarda de bloco do evaluator (ver `src/evaluator.py`); `kickoff_coverage` e
`block_guard` no relatório dizem quanto disso aconteceu. Half-life vem da
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

`--retrain-every` expõe a cadência de reajuste (default 100 jogos). É a única
variável manipulada pelo RESEARCH-01A (CONTROL 100 vs TREATMENT 10); todo o
resto do painel fica idêntico entre os braços, como manda a Regra 6.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics as st
import sys
from collections.abc import Callable
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
from src.serving_evaluator import ServingStackEvaluator  # noqa: E402

DB = ROOT / "data" / "matches.db"
TRIALS = ROOT / "data" / "trials.json"
DEFAULT_HALF_LIFE = 120
MIN_HISTORY = 200
RETRAIN_EVERY = 100
MAX_GOALS = 8
OU_LINE = 2.5
MIN_TEAM_N = 10
# Bootstrap de bloco móvel: jogos vizinhos no tempo não são independentes.
BLOCK_LENGTH = 21
N_BOOT = 1000
BOOTSTRAP_SEED = 13
PROGRESS_EVERY = 200  # log de progresso do walk-forward (execução longa)
# Baselines de skill score realmente implementados. Os demais do Roadmap SS6
# (elo_baseline, current_v3, market_no_vig) exigem rodar outros previsores
# sobre a MESMA base; pedir um deles falha alto, nunca silencia como zero.
SUPPORTED_BASELINES = frozenset({"climatology"})
# Motores mensuráveis. `dixon_coles` é o histórico (Poisson + DC puro) e segue
# sendo o DEFAULT para não invalidar de repente as medições já feitas contra
# ele; `serving` é a pilha que realmente prevê (Elo + NB/DC + ensemble xG),
# reconstruída a cada reajuste em src/serving_evaluator.py.
ENGINES = ("dixon_coles", "serving")
DEFAULT_ENGINE = "dixon_coles"


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
            "SELECT m.date, m.home_team, m.away_team, m.home_score, m.away_score, s.kickoff_at, "
            "       m.tournament, m.neutral, s.home_xg, s.away_xg "
            "FROM matches m LEFT JOIN sofascore_matches s "
            "  ON s.date = m.date AND s.home_team = m.home_team AND s.away_team = m.away_team "
            "WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()
    obs = []
    for d, home, away, hs, asc, kickoff_at, tournament, neutral, home_xg, away_xg in rows:
        obs.append(
            {
                "home": home,
                "away": away,
                "kickoff": _kickoff(d, kickoff_at),
                "date": d,
                "has_real_kickoff": kickoff_at is not None,
                "tournament": tournament,
                "neutral": int(neutral or 0),
                # xG vive DENTRO de `result`, junto dos gols, pelo MESMO motivo
                # documentado em src/evaluator.py: a ABC do core remove só o
                # `target_key` das features antes do predict_step. Qualquer
                # campo de DESFECHO deixado no nível de cima chegaria à
                # previsão do próprio jogo — vazamento. Aninhado aqui, o xG
                # continua disponível no HISTÓRICO (que é passado estrito) para
                # o ajuste do ensemble, e invisível na hora de prever.
                "result": {
                    "home_goals": int(hs),
                    "away_goals": int(asc),
                    "home_xg": home_xg,
                    "away_xg": away_xg,
                },
            }
        )
    # Ordenar pelo RELÓGIO, não pela data-sem-hora: a ordem da lista é o que a
    # ABC prequential usa como "passado", então ordenar por `date` deixaria a
    # sequência dentro de uma mesma rodada ao sabor do SQLite.
    obs.sort(key=lambda o: (o["kickoff"], o["home"], o["away"]))
    if end:
        obs = [o for o in obs if o["date"] <= end]
    return obs


def _kickoff(date_str: str, kickoff_at: str | None) -> datetime:
    """Kickoff real do `sofascore_matches` quando existe; senão, meia-noite UTC
    da data.

    O fallback NÃO é cosmético: sem hora, a rodada inteira colapsa num único
    bloco simultâneo, e a guarda de bloco do evaluator passa a excluir do treino
    todos os jogos do mesmo dia. Isso custa um pouco de histórico, mas é a
    leitura HONESTA de um dado que não sabe a que horas o jogo começou —
    preencher com uma ordem inventada é que seria leakage. Quantos jogos caem
    nesse caso vai para `kickoff_coverage` no relatório."""
    if kickoff_at:
        return datetime.fromisoformat(str(kickoff_at).replace("Z", "+00:00")).astimezone(UTC)
    return datetime.fromisoformat(date_str).replace(tzinfo=UTC)


def _outcomes_1x2(goals_home: int, goals_away: int) -> int:
    """0=derrota do mandante, 1=empate, 2=vitoria do mandante — ordem ordinal
    coerente com [p_loss, p_draw, p_win] que o RPS do core espera."""
    if goals_home > goals_away:
        return 2
    if goals_home == goals_away:
        return 1
    return 0


def _make_evaluator(engine: str, half_life: float, cfg: dict[str, Any] | None):
    """Instancia o motor pedido. `dixon_coles` mede o Poisson+DC puro;
    `serving` mede a pilha que realmente prevê — ver
    src/serving_evaluator.py."""
    if engine == "serving":
        if not cfg:
            raise SystemExit("engine 'serving' exige config.yaml carregado (Elo, calibração, ensemble_xg)")
        return ServingStackEvaluator(cfg, max_goals=MAX_GOALS)
    if engine != "dixon_coles":
        raise NotImplementedError(f"engine {engine!r} desconhecido. Disponíveis: {list(ENGINES)}")
    return BrasileiraoDixonColesEvaluator(half_life_days=half_life, max_goals=MAX_GOALS)


def _run_walkforward(
    observations: list[dict[str, Any]],
    half_life: float,
    retrain_every: int,
    *,
    progress: Callable[[int, int], None] | None = None,
    engine: str = DEFAULT_ENGINE,
    cfg: dict[str, Any] | None = None,
):
    """Walk-forward completo. `progress(feitas, total)` é chamado a cada
    `PROGRESS_EVERY` previsões — uma execução com refit por rodada leva horas e
    ficar mudo o tempo todo é indistinguível de travamento."""
    ev = _make_evaluator(engine, half_life, cfg)
    if progress is not None:
        ev = _with_progress(ev, len(observations) - MIN_HISTORY, progress)
    results = ev.run(observations, min_history=MIN_HISTORY, retrain_every=retrain_every)
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
    return rows, ev


def _with_progress(ev, total: int, progress: Callable[[int, int], None]):
    """Instrumenta `predict_step` para reportar progresso, sem tocar na lógica
    do avaliador (que é o objeto sob medição — envolver é mais seguro que
    espalhar contador dentro dele)."""
    inner = ev.predict_step
    state = {"done": 0}

    def counting(features):
        out = inner(features)
        state["done"] += 1
        if state["done"] % PROGRESS_EVERY == 0:
            progress(state["done"], total)
        return out

    ev.predict_step = counting  # type: ignore[method-assign]
    return ev


def _climatology_probs(rows: list[dict[str, Any]]) -> list[list[float]]:
    n = len(rows)
    counts = [0, 0, 0]
    for r in rows:
        counts[r["actual_1x2"]] += 1
    freqs = [c / n for c in counts] if n else [1 / 3, 1 / 3, 1 / 3]
    return [freqs for _ in rows]


def _metric_record(
    name: str,
    value: float,
    *,
    baseline_value: float | None,
    n: int,
    is_primary: bool,
    delta_ci95: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Uma linha do formato de saída do Roadmap SS6.

    `delta_ci95` é o IC95 do delta de perda (modelo - baseline), na MESMA
    orientação do campo `delta`: negativo = modelo melhor. Vem de
    `_delta_ci95`, que trabalha sobre perdas pareadas jogo a jogo — sem ele a
    métrica primária viajaria sem incerteza, e o Roadmap SS6 exige o campo
    justamente no exemplo da primária."""
    delta = (value - baseline_value) if baseline_value is not None else None
    return {
        "metric": name,
        "value": round(value, 6),
        "baseline_value": round(baseline_value, 6) if baseline_value is not None else None,
        "delta": round(delta, 6) if delta is not None else None,
        "delta_ci95": [round(delta_ci95[0], 6), round(delta_ci95[1], 6)] if delta_ci95 else None,
        "n": n,
        "is_primary": is_primary,
    }


def _bootstrap_mean_ci(values: list[float]) -> tuple[float, float] | None:
    """IC95 da média por bootstrap de BLOCO MÓVEL.

    Não é iid: as linhas chegam em ordem cronológica e o erro de jogos vizinhos
    é correlacionado (mesma rodada, mesmas equipes em forma, mesmo regime de
    gols). Reamostrar observação a observação estreita o intervalo e
    SUPERESTIMA significância — e este painel, sendo a régua de promoção de
    toda trial, tem que ser o mais conservador dos instrumentos, não o menos.
    Mesmo esquema já usado por `h10_fadiga_walkforward.py` e pelo RESEARCH-01A."""
    if not values:
        return None
    lo, hi, _samples = bootstrap_ci(
        values,
        lambda u: sum(u) / len(u),
        scheme="moving",
        block_length=BLOCK_LENGTH,
        n_boot=N_BOOT,
        seed=BOOTSTRAP_SEED,
    )
    if lo is None or hi is None:
        return None
    return lo, hi


def _skill_score_ci(losses_model: list[float], losses_baseline: list[float]) -> tuple[float, float] | None:
    """IC95 do ganho médio (baseline - modelo) por jogo — positivo = modelo bate
    o baseline."""
    if not losses_model or len(losses_model) != len(losses_baseline):
        return None
    return _bootstrap_mean_ci([b - m for m, b in zip(losses_model, losses_baseline)])


def _delta_ci95(losses_model: list[float], losses_baseline: list[float]) -> tuple[float, float] | None:
    """IC95 do delta médio (modelo - baseline) — negativo = modelo melhor.

    Mesma quantidade do `_skill_score_ci`, com o SINAL do campo `delta` do
    formato de saída. Duas orientações no mesmo relatório convidam a erro de
    leitura, então cada uma tem nome próprio e um só lugar de uso."""
    ci = _skill_score_ci(losses_model, losses_baseline)
    return (-ci[1], -ci[0]) if ci else None


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
    # Regressão PONDERADA por `n` do bin. Sem peso, um bin com 3 jogos tem a
    # mesma alavancagem de um com 400: o slope (guardrail com alvo 0.9-1.1)
    # passa a refletir ruído de cauda e pode tanto vetar trial boa quanto
    # mascarar degradação real no miolo da distribuição.
    bins = [b for b in table if b["n"] > 0]
    xs = [b["mean_pred"] for b in bins]
    ys = [b["obs_freq"] for b in bins]
    ws = [b["n"] for b in bins]
    slope = None
    if len(bins) >= 2:
        w_total = sum(ws)
        mean_x = sum(w * x for w, x in zip(ws, xs)) / w_total
        mean_y = sum(w * y for w, y in zip(ws, ys)) / w_total
        var_x = sum(w * (x - mean_x) ** 2 for w, x in zip(ws, xs))
        if var_x > 0:
            cov = sum(w * (x - mean_x) * (y - mean_y) for w, x, y in zip(ws, xs, ys))
            slope = cov / var_x
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


def run(
    *,
    model_tag: str,
    start: str,
    end: str,
    retrain_every: int = RETRAIN_EVERY,
    baseline: str = "climatology",
    engine: str = DEFAULT_ENGINE,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if baseline not in SUPPORTED_BASELINES:
        raise NotImplementedError(
            f"baseline {baseline!r} não implementado neste painel. Disponíveis: "
            f"{sorted(SUPPORTED_BASELINES)}. `elo_baseline`, `current_v3` e `market_no_vig` "
            "exigem rodar OUTROS previsores sobre a MESMA base e ainda não estão plugados — "
            "falhar alto aqui é melhor que devolver skill score contra um baseline fantasma."
        )
    half_life = _half_life_for(model_tag)
    observations = _load_observations(end)
    if len(observations) < MIN_HISTORY + 50:
        raise SystemExit(f"histórico insuficiente ({len(observations)}) para min_history={MIN_HISTORY}")

    def _progress(done: int, total: int) -> None:
        print(f"  walk-forward: {done}/{total} previsões", file=sys.stderr, flush=True)

    all_rows, ev = _run_walkforward(observations, half_life, retrain_every, progress=_progress, engine=engine, cfg=cfg)
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

    ll_losses = [log_loss([p], [y]) for p, y in zip(probs_1x2, outcomes_1x2)]
    ll_baseline_losses = [log_loss([p], [y]) for p, y in zip(baseline_probs, outcomes_1x2)]

    rps_ci = _skill_score_ci(rps_losses, rps_baseline_losses)
    brier_ci = _skill_score_ci(brier_losses, brier_baseline_losses)

    metrics = [
        _metric_record(
            "rps",
            rps(probs_1x2, outcomes_1x2),
            baseline_value=rps(baseline_probs, outcomes_1x2),
            n=n,
            is_primary=True,
            delta_ci95=_delta_ci95(rps_losses, rps_baseline_losses),
        ),
        _metric_record(
            "brier_1x2",
            brier(probs_1x2, outcomes_1x2),
            baseline_value=brier(baseline_probs, outcomes_1x2),
            n=n,
            is_primary=False,
            delta_ci95=_delta_ci95(brier_losses, brier_baseline_losses),
        ),
        _metric_record(
            "log_loss",
            log_loss(probs_1x2, outcomes_1x2),
            baseline_value=log_loss(baseline_probs, outcomes_1x2),
            n=n,
            is_primary=False,
            delta_ci95=_delta_ci95(ll_losses, ll_baseline_losses),
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
        "retrain_every": retrain_every,
        "engine": engine,
        "serves_production_model": engine == "serving",
        "baseline": baseline,
        "bootstrap": {"scheme": "moving", "block_length": BLOCK_LENGTH, "n_boot": N_BOOT, "seed": BOOTSTRAP_SEED},
        "kickoff_coverage": {
            "n_observations": len(observations),
            "n_real_kickoff": sum(1 for o in observations if o["has_real_kickoff"]),
            "n_date_only_fallback": sum(1 for o in observations if not o["has_real_kickoff"]),
        },
        "block_guard": {
            "blocked_observations": ev.blocked_observations,
            "deferred_refits": ev.deferred_refits,
            # Só o motor `serving` ajusta xG; degradação silenciosa faria o
            # painel medir o baseline puro achando que mede o ensemble.
            "xg_fit_failures": getattr(ev, "xg_fit_failures", None),
        },
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
        "--engine",
        default=DEFAULT_ENGINE,
        choices=list(ENGINES),
        help=(
            f"motor avaliado (default {DEFAULT_ENGINE}). 'dixon_coles' = Poisson+DC puro (histórico); "
            "'serving' = a pilha que realmente prevê (Elo + NB/DC + ensemble xG)"
        ),
    )
    parser.add_argument(
        "--retrain-every",
        type=int,
        default=RETRAIN_EVERY,
        help=(
            f"cadência de reajuste em nº de jogos (default {RETRAIN_EVERY}). "
            "Variável manipulada pelo RESEARCH-01A: CONTROL usa o default, "
            "TREATMENT usa ~1 bloco de rodada (10)"
        ),
    )
    parser.add_argument(
        "--baseline",
        default="climatology",
        help=f"baseline de skill score (implementados: {sorted(SUPPORTED_BASELINES)})",
    )
    args = parser.parse_args()

    start, _, end = args.period.partition(",")
    cfg = load_config()  # valida config.yaml cedo, falha alto se ausente
    if args.retrain_every < 1:
        parser.error("--retrain-every >= 1")
    result = run(
        model_tag=args.model,
        start=start.strip(),
        end=end.strip(),
        retrain_every=args.retrain_every,
        baseline=args.baseline,
        engine=args.engine,
        cfg=cfg,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(
        f"BENCHMARK_WRITTEN path={args.output} engine={result['engine']} "
        f"n={result['n']} rps={result['metrics'][0]['value']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
