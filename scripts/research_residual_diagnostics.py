"""Diagnósticos residuais congelados: OU2.5 dev-only, T2-2026 e mercado 1X2."""

from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist
from typing import Any

from scipy.stats import binom

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import benchmark_predictor as bp  # noqa: E402
from src.ingest import load_config  # noqa: E402
from src.math_utils import shin_probabilities  # noqa: E402
from src.research.market_0b_resolution import full_market_protocol, valid_two_way_odds  # noqa: E402
from src.research.structural_edge import power_probabilities  # noqa: E402


def _losses(probs: list[float], actual: int) -> tuple[float, float, float]:
    onehot = [int(i == actual) for i in range(3)]
    brier = sum((p - y) ** 2 for p, y in zip(probs, onehot, strict=True))
    logloss = -math.log(max(probs[actual], 1e-15))
    rps = ((probs[0] - onehot[0]) ** 2 + (probs[0] + probs[1] - onehot[0] - onehot[1]) ** 2) / 2
    return rps, brier, logloss


def _market_probs(row: dict[str, Any]) -> list[float] | None:
    odds = row.get("market_odds_1x2")
    if not odds or len(odds) != 3 or any(not isinstance(o, (int, float)) or o <= 1 for o in odds):
        return None
    probs, _z, _margin = shin_probabilities(odds)
    return [float(probs[2]), float(probs[1]), float(probs[0])]


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    paired = [(row, _market_probs(row)) for row in rows]
    paired = [(row, market) for row, market in paired if market is not None]
    model_losses = [_losses([row["p_loss"], row["p_draw"], row["p_win"]], row["actual_1x2"]) for row, _ in paired]
    market_losses = [_losses(market, row["actual_1x2"]) for row, market in paired]
    names = ("rps", "brier_1x2", "log_loss")
    return {
        "n": len(paired),
        **{
            name: {
                "model": st.mean(value[i] for value in model_losses) if model_losses else None,
                "market": st.mean(value[i] for value in market_losses) if market_losses else None,
                "model_minus_market": st.mean(value[i] for value in model_losses)
                - st.mean(value[i] for value in market_losses)
                if model_losses
                else None,
            }
            for i, name in enumerate(names)
        },
    }


def _devig_records(rows: list[dict[str, Any]], method: str) -> list[dict[str, Any]]:
    records = []
    for row in rows:
        odds = row.get("market_odds_ou25")
        if not valid_two_way_odds(odds) or not isinstance(row.get("effective_elo_diff"), (int, float)):
            continue
        fair = shin_probabilities(list(odds))[0] if method == "shin" else power_probabilities(list(odds))[0]
        records.append(
            {
                "date": row["date"],
                "model_p": float(row["p_over"]),
                "market_p": float(fair[0]),
                "odds": [float(odds[0]), float(odds[1])],
                "actual": int(row["actual_over"]),
                "effective_elo_diff": float(row["effective_elo_diff"]),
            }
        )
    return records


def _ou25_dev(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_method = {}
    for offset, method in enumerate(("shin", "power")):
        records = _devig_records(rows, method)
        result = full_market_protocol(
            records, power_reference=records, permutations=1000, seed=20260825 + offset * 3000
        )
        for side in result["selections"].values():
            bins = side["ordering"]["bins"]
            side["top_minus_bottom_roi"] = (
                bins[-1]["roi_diagnostic"] - bins[0]["roi_diagnostic"] if len(bins) >= 2 else None
            )
        by_method[method] = result
    z = NormalDist().inv_cdf(0.975) + NormalDist().inv_cdf(0.80)
    typical_sd = st.stdev([1.9 - 1 if i % 2 else -1 for i in range(380)])
    mde = z * typical_sd / math.sqrt(380)
    primary = by_method["shin"]
    sensitivity = by_method["power"]
    side_go = {}
    for side_name in ("side_a", "side_b"):
        a = primary["selections"][side_name]
        b = sensitivity["selections"][side_name]
        strongest = max((item["roi_diagnostic"] for item in a["ordering"]["bins"]), default=-math.inf)
        side_go[side_name] = bool(
            a["ordering"]["monotonic_roi"]
            and b["ordering"]["monotonic_roi"]
            and (a["top_minus_bottom_roi"] or 0) >= 0.15
            and a["permutation"]["null_monotonic_rate"] < 0.05
            and strongest >= mde
        )
    return {
        "scope": "DEVELOPMENT_2021_2023_ONLY",
        "validation_2024_loaded": False,
        "mde_roi_approx_n380_at_odds_1_90": mde,
        "methods": by_method,
        "side_triage_go": side_go,
        "verdict": "CONSIDER_REGISTERING_2024_VALIDATION" if any(side_go.values()) else "ARCHIVE_OU25_CURRENT_RESIDUAL",
    }


def _accuracy(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    return st.mean(
        int(max(range(3), key=lambda i: [row["p_loss"], row["p_draw"], row["p_win"]][i]) == row["actual_1x2"])
        for row in rows
    )


def _t2_diagnostic(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    bp._tag_turno(rows)
    t2 = [row for row in rows if row["season"] == "2026" and row["turno"] == "T2"]
    history = {
        year: {"n": len(sample), "accuracy": _accuracy(sample)}
        for year in ("2022", "2023", "2024", "2025")
        if (sample := [row for row in rows if row["season"] == year and row["turno"] == "T2"])
    }
    actual_accuracy = _accuracy(t2)
    interval = [int(binom.ppf(0.025, len(t2), 0.5)), int(binom.ppf(0.975, len(t2), 0.5))]
    successes = round((actual_accuracy or 0) * len(t2))
    lambda_diag = {}
    for side, predicted_key, actual_key in (
        ("home", "lambda_home", "home_score"),
        ("away", "lambda_away", "away_score"),
    ):
        differences = [row[predicted_key] - row[actual_key] for row in t2]
        delta = st.mean(differences)
        half_width = 1.96 * st.stdev(differences) / math.sqrt(len(differences))
        lambda_diag[side] = {
            "predicted_mean": st.mean(row[predicted_key] for row in t2),
            "actual_mean": st.mean(row[actual_key] for row in t2),
            "predicted_minus_actual": delta,
            "paired_normal_ci95": [delta - half_width, delta + half_width],
        }
    centered = all(item["paired_normal_ci95"][0] <= 0 <= item["paired_normal_ci95"][1] for item in lambda_diag.values())
    return {
        "n": len(t2),
        "accuracy": actual_accuracy,
        "correct": successes,
        "binomial_predictive_interval_correct_count_95pct_p_0_50": interval,
        "accuracy_outside_interval": not interval[0] <= successes <= interval[1],
        "lambda_marginal": lambda_diag,
        "historical_t2": history,
        "verdict": "RESULT_NOISE_NOT_PARAMETER_DRIFT" if centered else "PARAMETER_DRIFT_SIGNAL",
    }


def _team_errors(rows: list[dict[str, Any]]) -> dict[str, Any]:
    season = [row for row in rows if row["season"] == "2026"]
    baseline_error = 1 - (_accuracy(season) or 0)
    result = {
        "baseline_model_error_rate": baseline_error,
        "venue_field_available": False,
        "venue_enrichment_task": "Add PIT stadium/venue source; city is not a stadium and must not be inferred.",
        "teams": {},
    }
    for team in ("Internacional", "Bahia"):
        involved = [row for row in season if team in (row["home"], row["away"])]
        decorated = []
        for row in involved:
            predicted = max(range(3), key=lambda i: [row["p_loss"], row["p_draw"], row["p_win"]][i])
            if predicted != row["actual_1x2"]:
                decorated.append(
                    {
                        key: row[key]
                        for key in ("date", "home", "away", "home_score", "away_score", "city", "neutral", "event_id")
                    }
                )
        home = [row for row in involved if row["home"] == team]
        away = [row for row in involved if row["away"] == team]
        home_error = 1 - (_accuracy(home) or 0)
        away_error = 1 - (_accuracy(away) or 0)
        result["teams"][team] = {
            "n": len(involved),
            "errors_n": len(decorated),
            "home": {"n": len(home), "error_rate": home_error},
            "away": {"n": len(away), "error_rate": away_error},
            "errors": decorated,
            "verdict": "HOME_EFFECT_CANDIDATE"
            if home_error > baseline_error and away_error <= baseline_error
            else "STRENGTH_MISESTIMATION_CANDIDATE"
            if home_error > baseline_error and away_error > baseline_error
            else "NO_CLEAR_EXCESS",
        }
    return result


def _market_benchmark(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sample = [row for row in rows if "2021" <= row["season"] <= "2024"]
    bp._tag_turno(sample)
    by_season = {
        year: _metrics([row for row in sample if row["season"] == year]) for year in ("2021", "2022", "2023", "2024")
    }
    by_turn = {
        key: _metrics(group) for key, group in _group(sample, lambda row: f"{row['season']}-{row['turno']}").items()
    }
    by_confidence = {
        key: _metrics(group)
        for key, group in _group(
            sample, lambda row: _confidence_bin(max(row["p_win"], row["p_draw"], row["p_loss"]))
        ).items()
    }
    home_pred = [row for row in sample if row["p_win"] > max(row["p_draw"], row["p_loss"])]
    resolution = {}
    for key, group in _group(home_pred, lambda row: _market_home_bin((_market_probs(row) or [0, 0, 0])[2])).items():
        resolution[key] = {
            **_metrics(group),
            "actual_home_rate": st.mean(row["actual_1x2"] == 2 for row in group),
            "actual_draw_rate": st.mean(row["actual_1x2"] == 1 for row in group),
            "market_mean_home": st.mean((_market_probs(row) or [0, 0, 0])[2] for row in group),
            "market_mean_draw": st.mean((_market_probs(row) or [0, 0, 0])[1] for row in group),
        }
    return {
        "overall": _metrics(sample),
        "by_season": by_season,
        "by_turn": by_turn,
        "by_model_confidence": by_confidence,
        "model_predicted_home_subset": {"overall": _metrics(home_pred), "market_resolution_bins": resolution},
        "theoretical_rps_prize_model_minus_market": _metrics(sample)["rps"]["model_minus_market"],
        "theoretical_rps_prize_home_subset": _metrics(home_pred)["rps"]["model_minus_market"],
    }


def _group(rows: list[dict[str, Any]], key) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[key(row)].append(row)
    return dict(sorted(groups.items()))


def _confidence_bin(value: float) -> str:
    return "lt_40" if value < 0.4 else "40_50" if value < 0.5 else "50_60" if value < 0.6 else "ge_60"


def _market_home_bin(value: float) -> str:
    return "lt_35" if value < 0.35 else "35_45" if value < 0.45 else "45_55" if value < 0.55 else "ge_55"


def run() -> dict[str, Any]:
    observations = bp._load_observations("2026-12-31")
    rows, _ = bp._run_walkforward(observations, 120.0, bp.RETRAIN_EVERY, engine="serving", cfg=load_config())
    dev = [row for row in rows if "2021-01-01" <= row["date"] <= "2023-12-31"]
    return {
        "schema_version": "residual-diagnostics/1",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "research_mode": "RETROSPECTIVE_DIAGNOSTIC_ONLY",
        "capital_gate": "CAPITAL_GATE: LOCKED",
        "ou25_dev_only": _ou25_dev(dev),
        "t2_2026": _t2_diagnostic(rows),
        "inter_bahia_2026": _team_errors(rows),
        "market_benchmark_2021_2024": _market_benchmark(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OU25={result['ou25_dev_only']['verdict']} T2={result['t2_2026']['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
