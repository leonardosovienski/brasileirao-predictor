"""Descriptive forecast-quality audit of a previously executed frozen replay.

No database/network/cohort access, fitting, policy search or wagering. All
comparisons use the same completed, valid-price panel within market and turn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

import numpy as np

WORK = Path(__file__).resolve().parent
BASE = WORK.parent.parent
MARKETS = ("1x2", "ou25", "btts")
MODELS = ("raw", "calibrated", "market_devig", "climatology_train")
METRICS = ("brier", "log_loss")
TURNS = ("test_exploratory", "paper_betting")
SEED = 20260909
REPLICATES = 2000
LOG_EPSILON = 1e-15
HISTORICAL_SHA256 = "14153f7cbb348e9eef22a8e1c438757b1ef482951e2576d4a8381d7928e8e142"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path, value):
    if path.exists():
        raise FileExistsError(f"Preserve prior diagnostic artifact: {path}")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def utc(value):
    if not isinstance(value, str):
        raise TypeError("Known timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Explicit timezone required")
    return parsed.astimezone(UTC)


def outcomes(result):
    home, away = result["home_goals"], result["away_goals"]
    if any(type(score) is not int or score < 0 for score in (home, away)):
        raise ValueError("Nonnegative integer fulltime scores required")
    return {
        "1x2": 0 if home > away else 1 if home == away else 2,
        "ou25": 0 if home + away >= 3 else 1,
        "btts": 0 if home > 0 and away > 0 else 1,
    }


def probability_vector(forecast, market):
    if market == "1x2":
        raw = forecast.get("p_1x2")
        if not isinstance(raw, (list, tuple)) or len(raw) != 3:
            return None
        vector = list(raw)
    else:
        positive = forecast.get("p_over25" if market == "ou25" else "p_btts")
        if type(positive) not in (int, float):
            return None
        vector = [positive, 1 - positive]
    if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in vector):
        return None
    if not math.isclose(math.fsum(vector), 1, rel_tol=0, abs_tol=1e-9):
        return None
    return vector


def valid_quotes(quotes, market, selection_plan):
    if not isinstance(quotes, (list, tuple)) or len(quotes) != (3 if market == "1x2" else 2):
        return False
    lower, upper = selection_plan["odds_bounds_inclusive"][market]
    if any(type(o) not in (int, float) or not math.isfinite(o) or not lower <= o <= upper for o in quotes):
        return False
    booksum = math.fsum(1 / o for o in quotes)
    lo, hi = selection_plan["overround_inclusive"]
    return lo - 1e-12 <= booksum <= hi + 1e-12


def market_probabilities(quotes):
    total = math.fsum(1 / o for o in quotes)
    return [1 / o / total for o in quotes]


def estimate_climatology(history):
    """Use only 2021--2024; the 2025 calibration data are not a baseline input."""
    ids = set()
    counts = {market: [0] * (3 if market == "1x2" else 2) for market in MARKETS}
    used = []
    for row in history:
        kickoff = utc(row["kickoff"])
        if not 2021 <= kickoff.year <= 2025:
            raise ValueError("Historical file must not contain 2026 or other periods")
        if row["event_id"] in ids:
            raise ValueError("Duplicate historical identity")
        ids.add(row["event_id"])
        if kickoff.year == 2025:
            continue
        if str(row["date"])[:4] != str(kickoff.year):
            raise ValueError("Historical date/year disagreement")
        targets = outcomes(row["result"])
        for market, winner in targets.items():
            counts[market][winner] += 1
        used.append(row)
    if not used:
        raise ValueError("No eligible climatology training observations")
    probabilities = {market: [count / len(used) for count in values] for market, values in counts.items()}
    if any(prob <= 0 for vector in probabilities.values() for prob in vector):
        raise ValueError("Empirical baseline has a zero class; no undeclared smoothing")
    return {
        "n": len(used), "years": [2021, 2022, 2023, 2024], "smoothing": "none",
        "counts": counts, "probabilities": probabilities,
        "last_training_kickoff": max(utc(row["kickoff"]) for row in used).isoformat(),
        "event_ids_sha256": digest([row["event_id"] for row in used]),
    }


def score_forecast(probabilities, winner):
    """Brier is sum over 3 classes for 1X2, single positive class for binary."""
    if len(probabilities) not in (2, 3) or type(winner) is not int or not 0 <= winner < len(probabilities):
        raise ValueError("Invalid scoring dimensions or outcome")
    if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities):
        raise ValueError("Invalid scoring probabilities")
    if not math.isclose(math.fsum(probabilities), 1, rel_tol=0, abs_tol=1e-9):
        raise ValueError("Scoring vector must sum to one")
    if len(probabilities) == 3:
        brier = math.fsum((p - (i == winner)) ** 2 for i, p in enumerate(probabilities))
    else:
        brier = (probabilities[0] - (winner == 0)) ** 2
    return {"brier": brier, "log_loss": -math.log(max(LOG_EPSILON, probabilities[winner]))}


def index_unique(rows, key):
    indexed = {str(row[key]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate artifact identity")
    return indexed


def prepare_losses(events, replay, forecasts, climatology, original_plan, candidate_hash):
    raw = index_unique(replay["diagnostic_raw"], "id")
    calibrated = index_unique(replay["primary_calibrated"], "id")
    predictions = index_unique(forecasts, "event_id")
    canonical = index_unique(events, "event_id")
    if not set(raw) == set(calibrated) == set(predictions) == set(canonical):
        raise ValueError("Forecast, replay and canonical IDs disagree")
    losses = []
    coverage = {turn: {"official_fixtures": 0, "completed": 0, "completion_states": Counter(),
                       "markets": {m: Counter() for m in MARKETS}} for turn in TURNS}
    for row in events:
        identity = str(row["event_id"])
        role = row["role"]
        expected_role = TURNS[0] if 1 <= row["round"] <= 19 else TURNS[1]
        if type(row["round"]) is not int or not 1 <= row["round"] <= 38 or role != expected_role:
            raise ValueError("Role disagrees with official round")
        if row["season"] != 2026 or utc(row["kickoff"]).year != 2026:
            raise ValueError("Unexpected replay season")
        stats = coverage[role]
        stats["official_fixtures"] += 1
        stats["completion_states"][row["completion_state"]] += 1
        for arm in (raw[identity], calibrated[identity]):
            if arm["candidate_frozen2025_hash"] != candidate_hash:
                raise ValueError("Different frozen candidate")
            for source_key, arm_key in (("round", "round"), ("role", "role"), ("odds", "odds"),
                                        ("kickoff", "kickoff_at"), ("completion_state", "completion_state")):
                if row[source_key] != arm[arm_key]:
                    raise ValueError("Replay metadata or quotes differ")
            expected = row["result"] or {}
            if (arm["home_goals"], arm["away_goals"]) != (expected.get("home_goals"), expected.get("away_goals")):
                raise ValueError("Replay outcomes differ from canonical input")
        for key in ("p_1x2", "p_over25", "p_btts"):
            if raw[identity][key] != predictions[identity][key]:
                raise ValueError("Raw arm differs from saved forecasts")
        if row["completion_state"] != "COMPLETED":
            for market in MARKETS:
                stats["markets"][market]["excluded_not_completed"] += 1
            continue
        targets = outcomes(row["result"])
        stats["completed"] += 1
        for market in MARKETS:
            quotes = row["odds"][market]
            if not valid_quotes(quotes, market, original_plan["selection"]):
                stats["markets"][market]["excluded_quote_gates"] += 1
                continue
            p_raw = probability_vector(raw[identity], market)
            p_cal = probability_vector(calibrated[identity], market)
            if p_raw is None or p_cal is None:
                stats["markets"][market]["excluded_missing_forecast"] += 1
                continue
            stats["markets"][market]["common_panel"] += 1
            vectors = {"raw": p_raw, "calibrated": p_cal, "market_devig": market_probabilities(quotes),
                       "climatology_train": climatology["probabilities"][market]}
            losses.append({
                "event_id": row["event_id"], "round": row["round"], "role": role, "market": market,
                "losses": {name: score_forecast(vector, targets[market]) for name, vector in vectors.items()},
            })
    return losses, coverage


def cluster_bootstrap(rows, seed, replicates=REPLICATES):
    """Paired cluster percentile intervals for event-weighted means.

    Sample G observed official rounds with replacement; each selected cluster
    carries every event and all model/metric values. Never sample a future or
    unobserved round as if its missing results were zero.
    """
    if not rows:
        return {"status": "NO_COMMON_PANEL", "n": 0, "rounds": [], "models": {}, "paired_differences": {}}
    rounds = sorted({row["round"] for row in rows})
    values = np.array([[[row["losses"][model][metric] for metric in METRICS] for model in MODELS] for row in rows])
    sums = np.array([values[[row["round"] == group for row in rows]].sum(axis=0) for group in rounds])
    counts = np.array([sum(row["round"] == group for row in rows) for group in rounds])
    mean = values.mean(axis=0)
    bootstrap = None
    if len(rounds) >= 2:
        rng = np.random.default_rng(seed)
        drawn = rng.integers(0, len(rounds), size=(replicates, len(rounds)))
        bootstrap = sums[drawn].sum(axis=1) / counts[drawn].sum(axis=1)[:, None, None]

    def interval(samples):
        return np.quantile(samples, [.025, .975]).tolist() if samples is not None else None

    models = {
        model: {metric: {"mean": float(mean[m, k]), "ci95": interval(bootstrap[:, m, k] if bootstrap is not None else None)}
                for k, metric in enumerate(METRICS)}
        for m, model in enumerate(MODELS)
    }
    differences = {}
    for left, right in combinations(range(len(MODELS)), 2):
        name = f"{MODELS[left]}_minus_{MODELS[right]}"
        differences[name] = {
            metric: {"mean": float(mean[left, k] - mean[right, k]),
                     "ci95": interval(bootstrap[:, left, k] - bootstrap[:, right, k] if bootstrap is not None else None)}
            for k, metric in enumerate(METRICS)
        }
    return {
        "status": "DESCRIPTIVE_ONLY", "n": len(rows), "rounds": rounds,
        "cluster_count": len(rounds), "events_by_round": dict(zip(map(str, rounds), counts.tolist())),
        "few_clusters_warning": len(rounds) < 10,
        "seed": seed, "replicates": replicates if bootstrap is not None else 0,
        "models": models, "paired_differences": differences,
    }


def render_report(result):
    lines = ["# Qualidade preditiva do replay congelado", "",
             "Diagnóstico adicional dos mesmos resultados já derivados. Nenhum modelo, peso ou regra foi ajustado.", "",
             "Menor Brier e menor log-loss indicam previsões melhores. Os quatro previsores são comparados nos mesmos jogos em cada mercado e turno.", "",
             "A climatologia usa somente os 1.520 jogos de 2021–2024. O Brier de 1X2 soma as três classes; o dos mercados binários usa a classe positiva. Não se devem comparar os números brutos de Brier entre 1X2 e os mercados binários.", ""]
    labels = {"test_exploratory": "Primeiro turno", "paper_betting": "Segundo turno disponível"}
    for role in TURNS:
        lines += [f"## {labels[role]}", "",
                  f"Jogos concluídos: {result['coverage'][role]['completed']} de {result['coverage'][role]['official_fixtures']} oficiais.", "",
                  "| Mercado | Jogos / rodadas | Previsor | Brier | Log-loss |", "|---|---:|---|---:|---:|"]
        for market in MARKETS:
            panel = result["panels"][role][market]
            for model in MODELS:
                metrics = panel.get("models", {}).get(model)
                if metrics:
                    lines.append(f"| {market} | {panel['n']} / {panel['cluster_count']} | {model} | {metrics['brier']['mean']:.6f} | {metrics['log_loss']['mean']:.6f} |")
        lines += ["", "Diferença contra o mercado sem margem: valor positivo significa erro maior. IC95 por reamostragem pareada de rodadas.", "",
                  "| Mercado | Previsor − mercado | Δ Brier [IC95] | Δ log-loss [IC95] |", "|---|---|---:|---:|"]
        for market in MARKETS:
            panel = result["panels"][role][market]
            for model in ("raw", "calibrated"):
                pair = panel.get("paired_differences", {}).get(f"{model}_minus_market_devig")
                if pair:
                    formatted = []
                    for metric in METRICS:
                        entry = pair[metric]
                        ci = entry["ci95"]
                        formatted.append(f"{entry['mean']:+.6f} [{ci[0]:+.6f}, {ci[1]:+.6f}]" if ci else f"{entry['mean']:+.6f} [indisponível]")
                    lines.append(f"| {market} | {model} | {formatted[0]} | {formatted[1]} |")
        lines.append("")
    lines += ["## Interpretação e limites", "",
              "Os intervalos usam 2.000 reamostragens de rodadas oficiais completas observadas, seed 20260909 com deslocamento fixo por painel. Preservam os mesmos eventos entre previsores e ponderam a média pelo número de jogos. Não há ajuste por múltiplas comparações nem incerteza do treino/calibração dentro desses intervalos.", "",
              "O segundo turno tem poucas rodadas disponíveis; seus intervalos são especialmente instáveis. Jogos futuros e placares ausentes não foram tratados como perdas zero. As rodadas podem permanecer correlacionadas entre si e nem sempre representam a mesma semana devido a adiamentos.", "",
              "O modelo e o Elo ficaram congelados no fim de 2024. Esta execução mede esse candidato fixo, e não reproduz a atualização contínua do serving. As odds são retrospectivas, sem prova de disponibilidade pré-jogo; o mercado sem margem também não é probabilidade verdadeira. Qualidade probabilística não comprova valor econômico ou execução.", "",
              "O histórico já tinha sido explorado, e este diagnóstico é posterior aos resultados econômicos. Todos os mercados e comparadores pré-definidos estão publicados, inclusive os que pioraram. Nenhum resultado permite reivindicar teste cego, promoção de estratégia ou lucro futuro.", ""]
    return "\n".join(lines)


def execute(source_dir, history_path, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {name: source_dir / name for name in ("canonical_input_2026.json", "candidate.json", "forecasts_2026.json", "replay_inputs.json")}
    paths["original_plan"] = source_dir / "reproducao/plan.json"
    paths["historical_2021_2025"] = history_path
    source_hashes = {name: sha(path) for name, path in paths.items()}
    plan = {
        "purpose": "POST_RESULT_DESCRIPTIVE_QUALITY_DIAGNOSTIC_NO_TUNING",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "markets": MARKETS, "models": MODELS, "metrics": METRICS,
        "climatology": "Empirical class frequencies on 2021-2024 only; no smoothing",
        "panel": "Within each official turn and market, completed common panel with original quote gates and all four forecasts",
        "brier": "1X2 sum over three classes; binary squared error for positive class",
        "log_loss": {"base": "e", "zero_probability_epsilon": LOG_EPSILON},
        "bootstrap": {"unit": "official round", "paired": True, "replicates": REPLICATES, "seed": SEED,
                      "seed_offsets": "100*turn_index + market_index", "interval": "percentile 2.5/97.5",
                      "min_clusters_for_interval": 2, "few_cluster_warning_below": 10},
        "all_pairwise_differences": True, "multiplicity_adjustment": False,
        "stop": "One fixed diagnostic, publish every panel; no refit, threshold change, selection or promotion",
        "source_sha256": source_hashes,
        "script_sha256": sha(Path(__file__)),
    }
    save_new(output_dir / "diagnostics_quality_plan.json", plan)
    if source_hashes["historical_2021_2025"] != HISTORICAL_SHA256:
        raise ValueError("Previously verified historical source changed")
    original_plan, candidate = read(paths["original_plan"]), read(paths["candidate.json"])
    if candidate["plan_sha256"] != source_hashes["original_plan"]:
        raise ValueError("Candidate/original plan hash disagreement")
    content = {key: value for key, value in candidate.items() if key != "candidate_sha256"}
    if digest(content) != candidate["candidate_sha256"]:
        raise ValueError("Candidate content changed")
    climate = estimate_climatology(read(history_path))
    if climate["n"] != 1520:
        raise ValueError("Expected exactly 1520 climatology observations")
    events, replay, forecasts = read(paths["canonical_input_2026.json"]), read(paths["replay_inputs.json"]), read(paths["forecasts_2026.json"])
    losses, coverage = prepare_losses(events, replay, forecasts, climate, original_plan, candidate["candidate_sha256"])
    if len(events) != 380 or any(coverage[role]["official_fixtures"] != 190 for role in TURNS):
        raise ValueError("Official turn denominator changed")
    panels = {}
    for turn_index, role in enumerate(TURNS):
        panels[role] = {}
        for market_index, market in enumerate(MARKETS):
            rows = [row for row in losses if row["role"] == role and row["market"] == market]
            panels[role][market] = cluster_bootstrap(rows, SEED + 100 * turn_index + market_index)
    result = {
        "status": "COMPLETE_DESCRIPTIVE_ONLY", "plan_sha256": sha(output_dir / "diagnostics_quality_plan.json"),
        "candidate_sha256": candidate["candidate_sha256"], "source_sha256": source_hashes,
        "climatology": climate, "coverage": coverage, "panels": panels,
        "new_model_fit": False, "new_strategy": False, "profit_test": False,
        "protected_cohort_ledgers_read": False,
    }
    for name, path in paths.items():
        if sha(path) != source_hashes[name]:
            raise ValueError("Source changed during diagnostics")
    save_new(output_dir / "diagnostics_quality_results.json", result)
    save_new(output_dir / "diagnostics_quality_event_losses.json", losses)
    report = output_dir / "DIAGNOSTICO_QUALIDADE.md"
    if report.exists():
        raise FileExistsError(report)
    report.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "panels": {
        role: {market: {"n": panel["n"], "rounds": panel.get("cluster_count"), "models": panel["models"]}
               for market, panel in by_market.items()} for role, by_market in panels.items()}}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=BASE / "outputs/BACKTEST_NOVO_2026")
    parser.add_argument("--history", type=Path, default=BASE / "work/selection_reanalysis/historical_input.json")
    parser.add_argument("--outdir", type=Path, default=WORK)
    options = parser.parse_args()
    execute(options.source, options.history, options.outdir)
