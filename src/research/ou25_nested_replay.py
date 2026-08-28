"""Nested temporal replay for an OU2.5 recommendation filter.

The module deliberately does not fit the football model.  Its input is the
point-in-time/prequential prediction ledger produced by the repository's
evaluator.  It only tunes the *decision filter*, and every outer decision is
selected on rows strictly older than the outer test block.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import NormalDist, mean
from typing import Any

import numpy as np

CONTAMINATED_SEASONS = frozenset({"2024", "2025", "2026"})


@dataclass(frozen=True)
class FilterParameters:
    min_conservative_ev: float
    max_conservative_ev: float
    min_odds: float
    max_odds: float
    side: str = "both"
    uncertainty_quantile: float = 0.90
    friction_rate: float = 0.015

    @property
    def id(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def devig_proportional(over_odd: float, under_odd: float) -> tuple[float, float]:
    inv = (1 / over_odd, 1 / under_odd)
    total = sum(inv)
    return inv[0] / total, inv[1] / total


def anchor_to_market_prequential(
    rows: Iterable[dict[str, Any]],
    *,
    minimum_history: int = 190,
    block_size: int = 38,
    weights: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Blend model and de-vigged market with a weight fitted on past blocks.

    ``weight=1`` is the sports model and ``weight=0`` is the market.  The
    selected weight for a block only sees labels strictly before that block.
    """
    ordered = sorted((dict(row) for row in rows), key=lambda row: (row["kickoff_at"], row["event_id"]))
    if any(not 0 <= weight <= 1 for weight in weights):
        raise ValueError("anchor weights must be between zero and one")
    output = [dict(row) for row in ordered]
    folds = []
    for start in range(minimum_history, len(ordered), block_size):
        history = ordered[:start]

        def loss(weight: float) -> float:
            errors = []
            for row in history:
                market, _ = devig_proportional(*map(float, row["offered_odds_ou25"]))
                probability = weight * float(row["p_over"]) + (1 - weight) * market
                errors.append((probability - int(row["actual_over"])) ** 2)
            return mean(errors)

        losses = {weight: loss(weight) for weight in weights}
        selected = min(weights, key=lambda weight: (losses[weight], weight))
        test = output[start : start + block_size]
        for row in test:
            market, _ = devig_proportional(*map(float, row["offered_odds_ou25"]))
            row["p_over_model_unanchored"] = float(row["p_over"])
            row["p_over"] = selected * float(row["p_over"]) + (1 - selected) * market
            row["market_anchor_model_weight"] = selected
        folds.append(
            {
                "train_n": len(history),
                "test_n": len(test),
                "test_min_kickoff": test[0]["kickoff_at"] if test else None,
                "selected_model_weight": selected,
                "past_brier_by_weight": {str(weight): losses[weight] for weight in weights},
            }
        )
    evaluated = output[minimum_history:]
    model_errors = []
    anchored_errors = []
    market_errors = []
    for row in evaluated:
        actual = int(row["actual_over"])
        market, _ = devig_proportional(*map(float, row["offered_odds_ou25"]))
        model = float(row.get("p_over_model_unanchored", row["p_over"]))
        model_errors.append((model - actual) ** 2)
        anchored_errors.append((float(row["p_over"]) - actual) ** 2)
        market_errors.append((market - actual) ** 2)
    report = {
        "schema_version": "ou25-market-anchor-prequential/2",
        "minimum_history": minimum_history,
        "block_size": block_size,
        "weights": list(weights),
        "folds": folds,
        "evaluated_n": len(evaluated),
        "model_brier": mean(model_errors) if model_errors else None,
        "anchored_brier": mean(anchored_errors) if anchored_errors else None,
        "market_brier": mean(market_errors) if market_errors else None,
        "capital_enabled": False,
    }
    return output, report


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    out: dict[str, float] = {}
    running = 0.0
    m = len(ordered)
    for rank, (key, value) in enumerate(ordered):
        running = max(running, min(1.0, (m - rank) * value))
        out[key] = running
    return out


def _wilson_lower(successes: int, n: int, confidence: float) -> float:
    if n <= 0:
        return 0.0
    z = NormalDist().inv_cdf(0.5 + confidence / 2)
    observed = successes / n
    denominator = 1 + z * z / n
    centre = observed + z * z / (2 * n)
    margin = z * math.sqrt(observed * (1 - observed) / n + z * z / (4 * n * n))
    return max(0.0, (centre - margin) / denominator)


def evaluate_certainty_policies(
    rows: Iterable[dict[str, Any]],
    *,
    evaluation_start: int,
    confidences: tuple[float, ...] = (0.90, 0.95, 0.99),
    minimum_samples: tuple[int, ...] = (30, 50, 100),
    radii: tuple[float, ...] = (0.05, 0.10),
    minimum_net_evs: tuple[float, ...] = (0.0, 0.02, 0.05),
    friction_rate: float = 0.02,
    seed: int = 20260827,
) -> dict[str, Any]:
    """Evaluate abstention policies using past-only Wilson probability bounds."""
    ordered = sorted((dict(row) for row in rows), key=lambda row: (row["kickoff_at"], row["event_id"]))
    policies = []
    raw_p = {}
    for confidence in confidences:
        for min_n in minimum_samples:
            for radius in radii:
                for minimum_ev in minimum_net_evs:
                    picks = []
                    for index in range(evaluation_start, len(ordered)):
                        row = ordered[index]
                        history = ordered[:index]
                        choices = []
                        for side in ("over", "under"):
                            probability = float(row["p_over"] if side == "over" else 1 - row["p_over"])
                            calibration = []
                            for past in history:
                                past_probability = float(past["p_over"] if side == "over" else 1 - past["p_over"])
                                if abs(past_probability - probability) <= radius:
                                    outcome = int(past["actual_over"] if side == "over" else not past["actual_over"])
                                    calibration.append(outcome)
                            if len(calibration) < min_n:
                                continue
                            lower = _wilson_lower(sum(calibration), len(calibration), confidence)
                            odd = float(row["offered_odds_ou25"][0 if side == "over" else 1])
                            conservative_ev = lower * odd - 1 - friction_rate
                            if conservative_ev >= minimum_ev:
                                choices.append((conservative_ev, side, odd, probability, lower, len(calibration)))
                        if not choices:
                            continue
                        conservative_ev, side, odd, probability, lower, calibration_n = max(choices)
                        won = bool(row["actual_over"]) == (side == "over")
                        picks.append(
                            {
                                "event_id": row["event_id"],
                                "season": row["season"],
                                "side": side,
                                "odd": odd,
                                "profit": odd - 1 if won else -1.0,
                                "clv": None,
                                "outcome_probability": probability,
                                "probability_ci_lower": lower,
                                "conservative_ev": conservative_ev,
                                "calibration_n": calibration_n,
                            }
                        )
                    policy_id = f"c{confidence:.2f}_n{min_n}_r{radius:.2f}_ev{minimum_ev:.2f}"
                    metrics = _metrics(picks, seed=seed + len(policies), full_bootstrap=True)
                    raw_p[policy_id] = _normal_p_greater([pick["profit"] for pick in picks])
                    policies.append(
                        {
                            "policy_id": policy_id,
                            "confidence": confidence,
                            "minimum_calibration_n": min_n,
                            "probability_radius": radius,
                            "minimum_conservative_ev": minimum_ev,
                            "metrics": metrics,
                            "picks": picks,
                        }
                    )
    adjusted = holm_adjust(raw_p)
    for policy in policies:
        policy["p_raw_one_sided"] = raw_p[policy["policy_id"]]
        policy["p_holm"] = adjusted[policy["policy_id"]]
    return {
        "schema_version": "ou25-certainty-abstention/2",
        "evaluation_start": evaluation_start,
        "evaluated_games": len(ordered) - evaluation_start,
        "policy_count": len(policies),
        "multiplicity": "Holm across all certainty policies",
        "policies": policies,
        "capital_enabled": False,
        "maximum_indication_score": 40,
    }


def _normal_p_greater(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0
    sd = float(np.std(values, ddof=1))
    if sd == 0:
        return 0.0 if mean(values) > 0 else 1.0
    z = mean(values) / (sd / math.sqrt(len(values)))
    return 1.0 - NormalDist().cdf(z)


def _moving_block_lcb(values: list[float], *, seed: int, iterations: int = 1000) -> float | None:
    if len(values) < 2:
        return None
    rng = np.random.default_rng(seed)
    n = len(values)
    block = min(max(2, round(math.sqrt(n))), n)
    starts = np.arange(n - block + 1)
    samples = np.empty(iterations)
    for j in range(iterations):
        draw: list[float] = []
        while len(draw) < n:
            start = int(rng.choice(starts))
            draw.extend(values[start : start + block])
        samples[j] = np.mean(draw[:n])
    return float(np.quantile(samples, 0.025))


def _uncertainty(history: list[dict[str, Any]], side: str, quantile: float) -> float:
    bins: dict[int, list[tuple[float, int]]] = {}
    for row in history:
        p = float(row["p_over"] if side == "over" else 1 - row["p_over"])
        y = int(row["actual_over"] if side == "over" else not row["actual_over"])
        bins.setdefault(min(9, int(p * 10)), []).append((p, y))
    # Upper quantile of historical calibration gaps.  This is a probability
    # haircut, not the Bernoulli outcome error of one game (which would be far
    # too pessimistic and conflate aleatoric variance with calibration risk).
    gaps = [
        abs(mean(p for p, _ in values) - mean(y for _, y in values)) for values in bins.values() if len(values) >= 10
    ]
    return float(np.quantile(gaps, quantile)) if gaps else 1.0


def score_row(
    row: dict[str, Any],
    params: FilterParameters,
    history: list[dict[str, Any]],
    *,
    uncertainty_by_side: dict[str, float] | None = None,
) -> dict[str, Any] | None:
    over_odd, under_odd = row["offered_odds_ou25"]
    close_over, close_under = row.get("closing_odds_ou25") or (None, None)
    close_probabilities = (
        devig_proportional(float(close_over), float(close_under)) if close_over and close_under else (None, None)
    )
    if not over_odd or not under_odd:
        return None
    market_over, market_under = devig_proportional(float(over_odd), float(under_odd))
    choices = []
    for side, probability, odd, market_probability, close_probability in (
        ("over", float(row["p_over"]), float(over_odd), market_over, close_probabilities[0]),
        ("under", 1 - float(row["p_over"]), float(under_odd), market_under, close_probabilities[1]),
    ):
        if params.side != "both" and params.side != side:
            continue
        uncertainty = (
            uncertainty_by_side[side]
            if uncertainty_by_side is not None
            else _uncertainty(history, side, params.uncertainty_quantile)
        )
        conservative_ev = max(0.0, probability - uncertainty) * odd - 1 - params.friction_rate
        if not (params.min_conservative_ev <= conservative_ev <= params.max_conservative_ev):
            continue
        if not (params.min_odds <= odd <= params.max_odds):
            continue
        choices.append((conservative_ev, side, probability, odd, market_probability, close_probability, uncertainty))
    if not choices:
        return None
    conservative_ev, side, probability, odd, market_probability, close_probability, uncertainty = max(choices)
    won = bool(row["actual_over"]) == (side == "over")
    clv = odd * float(close_probability) - 1 if close_probability is not None else None
    data_factor = min(1.0, len(history) / 1000)
    indication_score = min(40, max(1, round(40 * min(1.0, conservative_ev / 0.05) * data_factor)))
    return {
        "event_id": row["event_id"],
        "kickoff_at": row["kickoff_at"],
        "season": row["season"],
        "side": side,
        "odd": odd,
        "outcome_probability": probability,
        "market_probability_devig": market_probability,
        "gross_ev": probability * odd - 1,
        "conservative_ev": conservative_ev,
        "indication_strength_0_100": indication_score,
        "strength_cap_reason": "NO_PROSPECTIVE_A1_EVIDENCE",
        "uncertainty_haircut": uncertainty,
        "profit": odd - 1 if won else -1.0,
        "clv": clv,
        "won": won,
        "contaminated": str(row["season"]) in CONTAMINATED_SEASONS,
    }


def _mean_lcb(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return mean(values) - 1.96 * float(np.std(values, ddof=1)) / math.sqrt(len(values))


def _metrics(picks: list[dict[str, Any]], *, seed: int, full_bootstrap: bool = True) -> dict[str, Any]:
    profits = [float(p["profit"]) for p in picks]
    clvs = [float(p["clv"]) for p in picks if p.get("clv") is not None]
    season_roi = {s: mean([p["profit"] for p in picks if p["season"] == s]) for s in {p["season"] for p in picks}}
    side_roi = {s: mean([p["profit"] for p in picks if p["side"] == s]) for s in {p["side"] for p in picks}}
    odd_bands = {"low": [], "mid": [], "high": []}
    for p in picks:
        odd_bands["low" if p["odd"] < 1.8 else "mid" if p["odd"] <= 2.2 else "high"].append(p["profit"])
    odd_roi = {k: mean(v) for k, v in odd_bands.items() if v}
    return {
        "n": len(picks),
        "roi": mean(profits) if profits else None,
        "roi_ci95_lower": _moving_block_lcb(profits, seed=seed) if full_bootstrap else _mean_lcb(profits),
        "clv": mean(clvs) if clvs else None,
        "clv_ci95_lower": (
            (_moving_block_lcb(clvs, seed=seed + 1) if full_bootstrap else _mean_lcb(clvs)) if clvs else None
        ),
        "season_roi": season_roi,
        "side_roi": side_roi,
        "odd_band_roi": odd_roi,
        "worst_season_roi": min(season_roi.values()) if season_roi else None,
        "worst_side_roi": min(side_roi.values()) if side_roi else None,
        "worst_odd_band_roi": min(odd_roi.values()) if odd_roi else None,
    }


def _rank_key(metrics: dict[str, Any]) -> tuple[float, ...]:
    def ranked(value: float | None) -> float:
        return float(value) if value is not None and math.isfinite(value) else float("-inf")

    return (
        ranked(metrics["roi_ci95_lower"]),
        ranked(metrics["clv_ci95_lower"]),
        ranked(metrics["worst_season_roi"]),
        ranked(metrics["worst_side_roi"]),
        ranked(metrics["worst_odd_band_roi"]),
        math.log1p(metrics["n"]),
    )


def _split_blocks(rows: list[dict[str, Any]], block_size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + block_size] for i in range(0, len(rows), block_size)]


def nested_walk_forward(
    rows: Iterable[dict[str, Any]],
    combinations: Iterable[FilterParameters],
    *,
    minimum_train: int = 380,
    block_size: int = 95,
    seed: int = 20260827,
) -> dict[str, Any]:
    ordered = sorted((dict(r) for r in rows), key=lambda r: (r["kickoff_at"], r["event_id"]))
    configs = list(combinations)
    if not configs:
        raise ValueError("at least one filter combination is required")
    outer: list[dict[str, Any]] = []
    all_picks: list[dict[str, Any]] = []
    tested: list[dict[str, Any]] = []
    for fold_no, start in enumerate(range(minimum_train, len(ordered), block_size), 1):
        history = ordered[:start]
        test = ordered[start : start + block_size]
        if not test:
            break
        config_metrics: dict[str, dict[str, Any]] = {}
        raw_p: dict[str, float] = {}
        for config_no, config in enumerate(configs):
            # Inner expanding replay: first half is burn-in, later blocks are
            # scored with uncertainty estimated only from their own prefix.
            inner_picks: list[dict[str, Any]] = []
            inner_start = max(40, min(block_size, len(history) // 2))
            for pos in range(inner_start, len(history), block_size):
                prefix = history[:pos]
                uncertainty_by_side = {
                    side: _uncertainty(prefix, side, config.uncertainty_quantile) for side in ("over", "under")
                }
                for row in history[pos : pos + block_size]:
                    pick = score_row(row, config, prefix, uncertainty_by_side=uncertainty_by_side)
                    if pick:
                        inner_picks.append(pick)
            metrics = _metrics(inner_picks, seed=seed + fold_no * 10000 + config_no * 2, full_bootstrap=False)
            config_metrics[config.id] = metrics
            raw_p[config.id] = _normal_p_greater([p["profit"] for p in inner_picks])
        adjusted = holm_adjust(raw_p)
        for config in configs:
            tested.append(
                {
                    "outer_fold": fold_no,
                    "train_end_exclusive": test[0]["kickoff_at"],
                    "config_id": config.id,
                    "parameters": asdict(config),
                    "metrics": config_metrics[config.id],
                    "p_raw_one_sided": raw_p[config.id],
                    "p_holm": adjusted[config.id],
                }
            )
        selected = max(configs, key=lambda c: _rank_key(config_metrics[c.id]))
        outer_uncertainty = {
            side: _uncertainty(history, side, selected.uncertainty_quantile) for side in ("over", "under")
        }
        fold_picks = [
            p for row in test if (p := score_row(row, selected, history, uncertainty_by_side=outer_uncertainty))
        ]
        for pick in fold_picks:
            pick["outer_fold"] = fold_no
            pick["config_id"] = selected.id
        all_picks.extend(fold_picks)
        outer.append(
            {
                "fold": fold_no,
                "train_n": len(history),
                "test_n": len(test),
                "train_max_kickoff": history[-1]["kickoff_at"],
                "test_min_kickoff": test[0]["kickoff_at"],
                "selected_config_id": selected.id,
                "selection_p_holm": adjusted[selected.id],
                "test_metrics": _metrics(fold_picks, seed=seed + fold_no),
            }
        )
    final_metrics = _metrics(all_picks, seed=seed)
    evaluated_rows = ordered[minimum_train:]
    always_picks = []
    market_brier = []
    model_brier = []
    for row in evaluated_rows:
        oo, ou = row["offered_odds_ou25"]
        if not oo or not ou:
            continue
        market_over, _ = devig_proportional(float(oo), float(ou))
        model_brier.append((float(row["p_over"]) - int(row["actual_over"])) ** 2)
        market_brier.append((market_over - int(row["actual_over"])) ** 2)
        sides = [
            (float(row["p_over"]) * float(oo) - 1, "over", float(oo)),
            ((1 - float(row["p_over"])) * float(ou) - 1, "under", float(ou)),
        ]
        _ev, side, odd = max(sides)
        won = bool(row["actual_over"]) == (side == "over")
        always_picks.append(
            {"profit": odd - 1 if won else -1.0, "season": row["season"], "side": side, "odd": odd, "clv": None}
        )
    return {
        "schema_version": "ou25-nested-replay/2",
        "generated_at": datetime.now().astimezone().isoformat(),
        "contaminated_seasons": sorted(CONTAMINATED_SEASONS),
        "capital_enabled": False,
        "strength_cap_without_prospective_a1": 40,
        "selection_priority": [
            "roi_ci95_lower",
            "clv_ci95_lower",
            "worst_season_roi",
            "worst_side_roi",
            "worst_odd_band_roi",
            "sample_size",
        ],
        "multiplicity": "Holm family-wise correction within each outer fold",
        "outer_folds": outer,
        "tested_combinations": tested,
        "picks": all_picks,
        "metrics": final_metrics,
        "baselines": {
            "always_bet_best_model_ev": _metrics(always_picks, seed=seed + 91),
            "never_bet": {"n": 0, "profit": 0.0, "roi": 0.0},
            "market_devig": {
                "n": len(market_brier),
                "brier": mean(market_brier) if market_brier else None,
                "model_brier_same_rows": mean(model_brier) if model_brier else None,
                "note": "probability benchmark; a de-vigged fair price is not an executable bet",
            },
        },
    }


def freeze_candidate(result: dict[str, Any], destination: Path, *, source_hash: str) -> dict[str, Any]:
    fold_ids = [f["selected_config_id"] for f in result["outer_folds"]]
    candidate_id = fold_ids[-1] if fold_ids else None
    candidate_trial = next((t for t in reversed(result["tested_combinations"]) if t["config_id"] == candidate_id), None)
    metrics = result.get("metrics") or {}
    eligible = bool(
        metrics.get("n", 0) >= 200
        and metrics.get("roi_ci95_lower") is not None
        and metrics["roi_ci95_lower"] > 0
        and metrics.get("clv_ci95_lower") is not None
        and metrics["clv_ci95_lower"] > 0
    )
    frozen = {
        "schema_version": "ou25-frozen-candidate/2",
        "candidate_id": candidate_id if eligible else None,
        "parameters": candidate_trial["parameters"] if candidate_trial and eligible else None,
        "frozen_from_observed_data": True,
        "observed_contaminated_seasons": sorted(CONTAMINATED_SEASONS),
        "validation_status": "FUTURE_PROSPECTIVE_A1_REQUIRED",
        "capital_enabled": False,
        "maximum_indication_score": 40,
        "current_action": "SHADOW_CANDIDATE" if eligible else "NO_BET",
        "eligible_at_freeze": eligible,
        "source_sha256": source_hash,
    }
    destination.write_text(json.dumps(frozen, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return frozen


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
