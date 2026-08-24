"""Primitivas da Fase 0: ordenação do residual modelo × mercado.

Este módulo não emite picks e não decide capital. Ele mede odds agregadas do
SofaScore, cuja executabilidade é desconhecida, como diagnóstico histórico.
"""

from __future__ import annotations

import math
import random
import statistics as st
from collections import defaultdict
from datetime import UTC, datetime
from statistics import NormalDist
from typing import Any

from predictor_core.contracts import registry as registry_module
from predictor_core.measurement.metrics import brier, log_loss, rps
from predictor_core.measurement.stats import probabilistic_sharpe_ratio

from src.math_utils import shin_probabilities

SELECTIONS = ("away", "draw", "home")
DIVERGENCE_BINS = (
    ("lt_-5pp", -math.inf, -0.05),
    ("-5_0pp", -0.05, 0.0),
    ("0_5pp", 0.0, 0.05),
    ("5_10pp", 0.05, 0.10),
    ("ge_10pp", 0.10, math.inf),
)
ODDS_BINS = (("1_2", 1.0, 2.0), ("2_3", 2.0, 3.0), ("3_5", 3.0, 5.0), ("ge_5", 5.0, math.inf))
DECLARED_FAMILY_TRIALS = len(SELECTIONS) * len(DIVERGENCE_BINS) * len(ODDS_BINS)
TARGET_ROI = 0.05
POWER = 0.80
ALPHA = 0.05


def devig_1x2(odds: Any) -> list[float] | None:
    """Shin sem vig em ordem canônica [away, draw, home]."""
    if not odds or len(odds) != 3 or any(not isinstance(o, (int, float)) or o <= 1 for o in odds):
        return None
    probabilities, _z, _margin = shin_probabilities(odds)
    return [float(probabilities[2]), float(probabilities[1]), float(probabilities[0])]


def paired_records(rows: list[dict[str, Any]], start: str, end: str) -> list[dict[str, Any]]:
    records = []
    for row in rows:
        if not start <= row["date"] <= end:
            continue
        market = devig_1x2(row.get("market_odds_1x2"))
        elo_diff = row.get("effective_elo_diff")
        if market is None or not isinstance(elo_diff, (int, float)) or not math.isfinite(elo_diff):
            continue
        raw_home, raw_draw, raw_away = row["market_odds_1x2"]
        records.append(
            {
                "date": row["date"],
                "event_key": f'{row["date"]}|{row["home"]}|{row["away"]}',
                "model": [float(row["p_loss"]), float(row["p_draw"]), float(row["p_win"])],
                "market": market,
                "odds": [float(raw_away), float(raw_draw), float(raw_home)],
                "outcome": int(row["actual_1x2"]),
                "effective_elo_diff": float(elo_diff),
            }
        )
    return records


def divergence_bin(value: float) -> str:
    return next(name for name, low, high in DIVERGENCE_BINS if low <= value < high)


def odds_bin(value: float) -> str:
    return next(name for name, low, high in ODDS_BINS if low <= value < high)


def required_n_for_roi(returns: list[float], target_roi: float = TARGET_ROI) -> int | None:
    """Amostra aproximada para detectar ROI alvo, usando variância observada no dev."""
    if len(returns) < 2 or target_roi <= 0:
        return None
    sigma = st.stdev(returns)
    if sigma == 0:
        return None
    z_alpha = NormalDist().inv_cdf(1 - ALPHA / 2)
    z_power = NormalDist().inv_cdf(POWER)
    return math.ceil(((z_alpha + z_power) * sigma / target_roi) ** 2)


def _finite_or_none(value: float) -> float | None:
    return float(value) if math.isfinite(value) else None


def _metric_block(records: list[dict[str, Any]]) -> dict[str, Any]:
    model = [r["model"] for r in records]
    market = [r["market"] for r in records]
    outcomes = [r["outcome"] for r in records]
    return {
        "n": len(records),
        "model": {
            "rps": rps(model, outcomes),
            "brier_1x2": brier(model, outcomes),
            "log_loss": log_loss(model, outcomes),
        },
        "market": {
            "rps": rps(market, outcomes),
            "brier_1x2": brier(market, outcomes),
            "log_loss": log_loss(market, outcomes),
        },
    }


def selection_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded = []
    for record in records:
        for index, selection in enumerate(SELECTIONS):
            model_p = record["model"][index]
            market_p = record["market"][index]
            odd = record["odds"][index]
            won = record["outcome"] == index
            expanded.append(
                {
                    "date": record["date"],
                    "event_key": record["event_key"],
                    "selection": selection,
                    "model_p": model_p,
                    "market_p": market_p,
                    "divergence": model_p - market_p,
                    "divergence_bin": divergence_bin(model_p - market_p),
                    "odd": odd,
                    "odds_bin": odds_bin(odd),
                    "won": won,
                    "pnl": odd - 1.0 if won else -1.0,
                    "effective_elo_diff": record["effective_elo_diff"],
                }
            )
    return expanded


def _dsr(returns: list[float], historical_trial_sharpes: list[float | None]) -> dict[str, Any]:
    denominator = list(historical_trial_sharpes) + [None] * DECLARED_FAMILY_TRIALS
    result = registry_module.deflated_sharpe_ratio(returns, denominator)
    return {
        "dsr": _finite_or_none(float(result["dsr"])),
        "sr0": _finite_or_none(float(result["sr0"])),
        "n_trials": int(result["n_trials"]),
        "declared_family_trials": DECLARED_FAMILY_TRIALS,
        "effective_trials_policy": "CONSERVATIVE_NO_CORRELATION_DISCOUNT",
    }


def _cell(rows: list[dict[str, Any]], historical_trial_sharpes: list[float | None]) -> dict[str, Any]:
    pnl = [r["pnl"] for r in rows]
    model_brier = st.mean((r["model_p"] - float(r["won"])) ** 2 for r in rows)
    market_brier = st.mean((r["market_p"] - float(r["won"])) ** 2 for r in rows)
    return {
        "n": len(rows),
        "coverage": None,
        "mean_divergence": st.mean(r["divergence"] for r in rows),
        "mean_model_p": st.mean(r["model_p"] for r in rows),
        "mean_market_p": st.mean(r["market_p"] for r in rows),
        "actual_rate": st.mean(float(r["won"]) for r in rows),
        "mean_odds": st.mean(r["odd"] for r in rows),
        "roi_diagnostic": st.mean(pnl),
        "model_brier_binary": model_brier,
        "market_brier_binary": market_brier,
        "brier_delta_model_minus_market": model_brier - market_brier,
        "psr": _finite_or_none(probabilistic_sharpe_ratio(pnl, 0.0)),
        "dsr": _dsr(pnl, historical_trial_sharpes),
        "required_n_for_5pct_roi_80pct_power": required_n_for_roi(pnl),
    }


def cells(records: list[dict[str, Any]], historical_trial_sharpes: list[float | None]) -> list[dict[str, Any]]:
    expanded = selection_rows(records)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in expanded:
        groups[(row["selection"], row["divergence_bin"], row["odds_bin"])].append(row)
    output = []
    for key, rows in sorted(groups.items()):
        result = _cell(rows, historical_trial_sharpes)
        result.update(zip(("selection", "divergence_bin", "odds_bin"), key))
        result["coverage"] = len(rows) / len(records) if records else 0.0
        output.append(result)
    return output


def draw_ordering(records: list[dict[str, Any]]) -> dict[str, Any]:
    draw_rows = [r for r in selection_rows(records) if r["selection"] == "draw"]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in draw_rows:
        groups[row["divergence_bin"]].append(row)
    ordered = []
    for name, _low, _high in DIVERGENCE_BINS:
        rows = groups.get(name, [])
        if rows:
            ordered.append(
                {
                    "divergence_bin": name,
                    "n": len(rows),
                    "mean_divergence": st.mean(r["divergence"] for r in rows),
                    "actual_draw_rate": st.mean(float(r["won"]) for r in rows),
                    "roi_diagnostic": st.mean(r["pnl"] for r in rows),
                }
            )
    roi = [row["roi_diagnostic"] for row in ordered]
    monotonic = len(roi) >= 3 and all(right >= left for left, right in zip(roi, roi[1:]))
    return {"bins": ordered, "monotonic_roi": monotonic}


def _permutation_stratum(row: dict[str, Any]) -> tuple[str, int]:
    month = row["date"][:7]
    abs_diff = abs(row["effective_elo_diff"])
    elo_band = 0 if abs_diff < 50 else 1 if abs_diff < 100 else 2 if abs_diff < 200 else 3
    return month, elo_band


def permute_outcomes(records: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    """Permuta resultados em mês × faixa de |ΔElo|, preservando preços e previsões."""
    rng = random.Random(seed)
    by_stratum: dict[tuple[str, int], list[int]] = defaultdict(list)
    for index, row in enumerate(records):
        by_stratum[_permutation_stratum(row)].append(index)
    outcomes = [r["outcome"] for r in records]
    permuted = list(outcomes)
    for indexes in by_stratum.values():
        values = [outcomes[index] for index in indexes]
        rng.shuffle(values)
        for index, value in zip(indexes, values):
            permuted[index] = value
    return [dict(row, outcome=outcome) for row, outcome in zip(records, permuted)]


def permutation_sanity(records: list[dict[str, Any]], permutations: int, seed: int) -> dict[str, Any]:
    observed = draw_ordering(records)["monotonic_roi"]
    null_monotonic = 0
    for offset in range(permutations):
        null_monotonic += int(draw_ordering(permute_outcomes(records, seed + offset))["monotonic_roi"])
    return {
        "strata": "calendar_month_x_abs_effective_elo_diff_band",
        "permutations": permutations,
        "seed": seed,
        "observed_monotonic": observed,
        "null_monotonic_count": null_monotonic,
        "null_monotonic_rate": null_monotonic / permutations,
    }


def draw_power_requirements(records: list[dict[str, Any]]) -> dict[str, int | None]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in selection_rows(records):
        if row["selection"] == "draw":
            grouped[row["divergence_bin"]].append(row["pnl"])
    return {name: required_n_for_roi(grouped.get(name, [])) for name, _low, _high in DIVERGENCE_BINS}


def evaluate(
    records: list[dict[str, Any]],
    *,
    requested_n: int,
    historical_trial_sharpes: list[float | None],
    permutations: int,
    seed: int,
    power_reference: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    draw = draw_ordering(records)
    power_requirements = draw_power_requirements(power_reference if power_reference is not None else records)
    minimums_met = all(
        power_requirements.get(row["divergence_bin"]) is not None
        and row["n"] >= int(power_requirements[row["divergence_bin"]] or 0)
        for row in draw["bins"]
    )
    return {
        "n": len(records),
        "requested_n": requested_n,
        "coverage": len(records) / requested_n if requested_n else 0.0,
        "paired_probabilistic": _metric_block(records),
        "draw_ordering": draw,
        "all_declared_cells": cells(records, historical_trial_sharpes),
        "permutation_sanity": permutation_sanity(records, permutations, seed),
        "draw_power_requirements_from_development": power_requirements,
        "power_minimums_met": minimums_met,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
