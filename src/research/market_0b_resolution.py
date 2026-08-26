"""Pré-checagem estrutural da Fase 0B para OU2.5 e BTTS.

Não emite apostas. Mede somente se o modelo varia o bastante entre jogos para
que um teste posterior de ordenação contra o mercado seja identificável.
"""

from __future__ import annotations

import math
import random
import statistics as st
from collections import defaultdict
from statistics import NormalDist
from typing import Any

MIN_MARKET_COVERAGE = 0.80
THRESHOLD_VAR = {"ou25": 0.02, "btts": 0.02}
HISTOGRAM_WIDTH = 0.05
TARGET_ROI = 0.05
POWER = 0.80
ALPHA = 0.05
DIVERGENCE_BINS = (
    ("lt_-5pp", -math.inf, -0.05),
    ("-5_0pp", -0.05, 0.0),
    ("0_5pp", 0.0, 0.05),
    ("5_10pp", 0.05, 0.10),
    ("ge_10pp", 0.10, math.inf),
)


def valid_two_way_odds(value: Any) -> bool:
    return bool(
        value
        and len(value) == 2
        and all(isinstance(odd, (int, float)) and math.isfinite(odd) and odd > 1 for odd in value)
    )


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _histogram(values: list[float]) -> list[dict[str, Any]]:
    counts = [0] * int(1 / HISTOGRAM_WIDTH)
    for value in values:
        index = min(int(value / HISTOGRAM_WIDTH), len(counts) - 1)
        counts[max(index, 0)] += 1
    return [
        {"lower": i * HISTOGRAM_WIDTH, "upper": (i + 1) * HISTOGRAM_WIDTH, "n": count} for i, count in enumerate(counts)
    ]


def market_summary(
    rows: list[dict[str, Any]], probability_key: str, odds_key: str, *, threshold_var: float
) -> dict[str, Any]:
    probabilities = [
        float(row[probability_key])
        for row in rows
        if isinstance(row.get(probability_key), (int, float)) and math.isfinite(row[probability_key])
    ]
    odds_n = sum(valid_two_way_odds(row.get(odds_key)) for row in rows)
    p10 = _quantile(probabilities, 0.10) if probabilities else None
    p90 = _quantile(probabilities, 0.90) if probabilities else None
    sd = st.pstdev(probabilities) if len(probabilities) > 1 else 0.0 if probabilities else None
    spread = p90 - p10 if p10 is not None and p90 is not None else None
    resolution_pass = bool(sd is not None and sd >= threshold_var)
    coverage = odds_n / len(rows) if rows else 0.0
    return {
        "n_predictions": len(probabilities),
        "requested_n": len(rows),
        "probability_mean": st.mean(probabilities) if probabilities else None,
        "probability_sd": sd,
        "probability_variance": sd * sd if sd is not None else None,
        "probability_min": min(probabilities) if probabilities else None,
        "probability_max": max(probabilities) if probabilities else None,
        "probability_range": max(probabilities) - min(probabilities) if probabilities else None,
        "probability_p10": p10,
        "probability_p90": p90,
        "probability_p10_p90_spread": spread,
        "unique_probabilities_4dp": len({round(value, 4) for value in probabilities}),
        "histogram_width": HISTOGRAM_WIDTH,
        "histogram": _histogram(probabilities),
        "threshold_var": threshold_var,
        "odds_complete_n": odds_n,
        "odds_coverage": coverage,
        "odds_coverage_pass": coverage >= MIN_MARKET_COVERAGE,
        "resolution_pass": resolution_pass,
        "structural_verdict": "RESOLUTION_SUFFICIENT" if resolution_pass else "NO_GO_LOW_MODEL_RESOLUTION",
    }


def scalar_summary(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    """Describe a finite scalar emitted by the walk-forward serving stack."""
    values = [
        float(row[key])
        for row in rows
        if isinstance(row.get(key), (int, float)) and math.isfinite(row[key])
    ]
    sd = st.pstdev(values) if len(values) > 1 else 0.0 if values else None
    p10 = _quantile(values, 0.10) if values else None
    p90 = _quantile(values, 0.90) if values else None
    return {
        "n": len(values),
        "mean": st.mean(values) if values else None,
        "sd": sd,
        "variance": sd * sd if sd is not None else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "range": max(values) - min(values) if values else None,
        "p10": p10,
        "p90": p90,
        "p10_p90_spread": p90 - p10 if p10 is not None and p90 is not None else None,
    }


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ou25 = market_summary(rows, "p_over", "market_odds_ou25", threshold_var=THRESHOLD_VAR["ou25"])
    btts = market_summary(rows, "p_btts", "market_odds_btts", threshold_var=THRESHOLD_VAR["btts"])
    candidates = [name for name, result in (("ou25", ou25), ("btts", btts)) if result["resolution_pass"]]
    covered = [
        name
        for name, result in (("ou25", ou25), ("btts", btts))
        if result["resolution_pass"] and result["odds_coverage_pass"]
    ]
    return {
        "thresholds": {
            "threshold_var": THRESHOLD_VAR,
            "min_market_coverage": MIN_MARKET_COVERAGE,
            "policy": "ANY_MARKET_SD_BELOW_THRESHOLD_IS_GLOBAL_STRUCTURAL_NO_GO",
        },
        "markets": {"ou25": ou25, "btts": btts},
        "lambda_total": scalar_summary(rows, "lambda_total"),
        "resolution_candidates": candidates,
        "full_protocol_candidates": covered,
        "verdict": (
            "NO_GO_STRUCTURAL"
            if len(candidates) < 2
            else "PROCEED_TO_FULL_0B"
            if len(covered) == 2
            else "INSUFFICIENT_ODDS_COVERAGE"
        ),
    }


def _devig(odds: Any) -> list[float] | None:
    if not valid_two_way_odds(odds):
        return None
    implied = [1.0 / float(odd) for odd in odds]
    total = sum(implied)
    return [value / total for value in implied]


def paired_records(
    rows: list[dict[str, Any]], probability_key: str, odds_key: str, actual_key: str
) -> list[dict[str, Any]]:
    records = []
    for row in rows:
        market = _devig(row.get(odds_key))
        probability = row.get(probability_key)
        elo = row.get("effective_elo_diff")
        if market is None or not isinstance(probability, (int, float)) or not isinstance(elo, (int, float)):
            continue
        records.append(
            {
                "date": row["date"],
                "model_p": float(probability),
                "market_p": market[0],
                "odds": [float(value) for value in row[odds_key]],
                "actual": int(row[actual_key]),
                "effective_elo_diff": float(elo),
            }
        )
    return records


def _bin(value: float) -> str:
    return next(name for name, low, high in DIVERGENCE_BINS if low <= value < high)


def required_n(returns: list[float]) -> int | None:
    if len(returns) < 2 or st.stdev(returns) == 0:
        return None
    z = NormalDist().inv_cdf(1 - ALPHA / 2) + NormalDist().inv_cdf(POWER)
    return math.ceil((z * st.stdev(returns) / TARGET_ROI) ** 2)


def ordering(records: list[dict[str, Any]], power_reference: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[_bin(record["model_p"] - record["market_p"])].append(record)
    reference_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in power_reference or records:
        reference_groups[_bin(record["model_p"] - record["market_p"])].append(record)
    bins = []
    for name, _low, _high in DIVERGENCE_BINS:
        sample = groups.get(name, [])
        if not sample:
            continue
        pnl = [row["odds"][0] - 1 if row["actual"] else -1 for row in sample]
        ref_pnl = [row["odds"][0] - 1 if row["actual"] else -1 for row in reference_groups.get(name, [])]
        need = required_n(ref_pnl)
        bins.append(
            {
                "divergence_bin": name,
                "n": len(sample),
                "mean_divergence": st.mean(row["model_p"] - row["market_p"] for row in sample),
                "roi_diagnostic": st.mean(pnl),
                "required_n_for_5pct_roi_80pct_power": need,
                "power_met": need is not None and len(sample) >= need,
            }
        )
    roi = [item["roi_diagnostic"] for item in bins]
    return {
        "bins": bins,
        "monotonic_roi": len(roi) >= 3 and all(b >= a for a, b in zip(roi, roi[1:])),
        "power_minimums_met": bool(bins) and all(item["power_met"] for item in bins),
    }


def _stratum(record: dict[str, Any]) -> tuple[str, int]:
    absolute = abs(record["effective_elo_diff"])
    band = 0 if absolute < 50 else 1 if absolute < 100 else 2 if absolute < 200 else 3
    return record["date"][:7], band


def _permuted(records: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    indexes: dict[tuple[str, int], list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        indexes[_stratum(record)].append(index)
    actual = [record["actual"] for record in records]
    changed = list(actual)
    for group in indexes.values():
        values = [actual[index] for index in group]
        rng.shuffle(values)
        for index, value in zip(group, values):
            changed[index] = value
    return [dict(record, actual=value) for record, value in zip(records, changed)]


def _selection(records: list[dict[str, Any]], index: int) -> list[dict[str, Any]]:
    if index == 0:
        return records
    return [
        dict(
            record,
            model_p=1.0 - record["model_p"],
            market_p=1.0 - record["market_p"],
            odds=[record["odds"][1], record["odds"][0]],
            actual=1 - record["actual"],
        )
        for record in records
    ]


def full_market_protocol(
    records: list[dict[str, Any]], *, power_reference: list[dict[str, Any]], permutations: int, seed: int
) -> dict[str, Any]:
    selections = {}
    passed = False
    for index, name in enumerate(("side_a", "side_b")):
        selected = _selection(records, index)
        reference = _selection(power_reference, index)
        observed = ordering(selected, reference)
        null_count = sum(
            ordering(_permuted(selected, seed + index * permutations + i))["monotonic_roi"] for i in range(permutations)
        )
        selection_pass = (
            observed["monotonic_roi"] and observed["power_minimums_met"] and null_count / permutations < 0.05
        )
        passed = passed or selection_pass
        selections[name] = {
            "ordering": observed,
            "permutation": {
                "n": permutations,
                "seed": seed + index * permutations,
                "null_monotonic_count": null_count,
                "null_monotonic_rate": null_count / permutations,
            },
            "verdict": "SIGNAL" if selection_pass else "NO_GO",
        }
    return {
        "n": len(records),
        "declared_cells": 10,
        "selections": selections,
        "verdict": "SIGNAL_FOR_PROSPECTIVE_REPLICATION" if passed else "NO_GO_CURRENT_RESIDUAL",
    }
