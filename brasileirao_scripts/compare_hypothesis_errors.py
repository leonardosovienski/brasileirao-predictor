"""Compare a treatment with a control by error signature on paired games."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

LABELS = ("away", "draw", "home")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _moving_ci(
    values: list[float],
    seed: int = 42,
    n_boot: int = 10_000,
    block: int = 21,
    alpha: float = 0.05,
) -> list[float] | None:
    if not values:
        return None
    delta = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    starts = np.arange(max(1, len(delta) - block + 1))
    means = np.empty(n_boot)
    blocks_needed = int(np.ceil(len(delta) / block))
    for i in range(n_boot):
        chosen = rng.choice(starts, size=blocks_needed, replace=True)
        sample = np.concatenate([delta[start : start + block] for start in chosen])[: len(delta)]
        means[i] = np.mean(sample)
    return [float(v) for v in np.quantile(means, [alpha / 2, 1 - alpha / 2])]


def _load(path: Path) -> dict[str, dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["event_id"]): row for row in rows}


def _chronological_keys(control: dict[str, dict[str, Any]], treatment: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(control.keys() & treatment.keys(), key=lambda key: (control[key]["date"], key))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--treatment", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--family-looks", type=int, default=1)
    args = parser.parse_args()
    if args.family_looks < 1:
        parser.error("--family-looks must be >= 1")

    control = _load(args.control)
    treatment = _load(args.treatment)
    # Moving blocks require a time axis. Event IDs are identifiers and sorting
    # by them would silently destroy temporal dependence.
    keys = _chronological_keys(control, treatment)
    if not keys:
        raise RuntimeError("no paired events")

    confusion_control: Counter[str] = Counter()
    confusion_treatment: Counter[str] = Counter()
    flips: Counter[str] = Counter()
    by_actual: dict[str, list[dict[str, Any]]] = {label: [] for label in LABELS}
    by_control_error: dict[str, list[dict[str, Any]]] = {
        "correct": [],
        "wrong_to_away": [],
        "wrong_to_draw": [],
        "wrong_to_home": [],
    }
    paired: list[dict[str, Any]] = []

    for key in keys:
        c = control[key]
        t = treatment[key]
        if (c["date"], c["home"], c["away"], c["outcome"]) != (t["date"], t["home"], t["away"], t["outcome"]):
            raise RuntimeError(f"pair mismatch for {key}")
        actual = int(c["outcome"])
        pred_c = int(np.argmax(c["probabilities"]))
        pred_t = int(np.argmax(t["probabilities"]))
        row = {
            "event_id": key,
            "actual": LABELS[actual],
            "pred_control": LABELS[pred_c],
            "pred_treatment": LABELS[pred_t],
            "rps_delta": float(t["rps"] - c["rps"]),
            "brier_delta": float(t["brier"] - c["brier"]),
            "log_loss_delta": float(t["log_loss"] - c["log_loss"]),
        }
        paired.append(row)
        by_actual[LABELS[actual]].append(row)
        bucket = "correct" if pred_c == actual else f"wrong_to_{LABELS[pred_c]}"
        by_control_error[bucket].append(row)
        confusion_control[f"{LABELS[actual]}->{LABELS[pred_c]}"] += 1
        confusion_treatment[f"{LABELS[actual]}->{LABELS[pred_t]}"] += 1
        if pred_c != pred_t:
            flips[f"{LABELS[pred_c]}->{LABELS[pred_t]}"] += 1

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        values = {metric: [float(row[f"{metric}_delta"]) for row in rows] for metric in ("rps", "brier", "log_loss")}
        return {
            "n": len(rows),
            "mean_delta_treatment_minus_control": {
                metric: _mean(metric_values) for metric, metric_values in values.items()
            },
            "moving_block_ci95": {metric: _moving_ci(metric_values) for metric, metric_values in values.items()},
        }

    result = {
        "schema_version": "hypothesis-error-comparison/1",
        "hypothesis": args.name,
        "control": {"path": str(args.control), "sha256": _sha256(args.control)},
        "treatment": {"path": str(args.treatment), "sha256": _sha256(args.treatment)},
        "pairing": {
            "paired_n": len(keys),
            "control_only": len(control.keys() - treatment.keys()),
            "treatment_only": len(treatment.keys() - control.keys()),
        },
        "overall": summarize(paired),
        "argmax_flips": {"n": sum(flips.values()), "directions": dict(sorted(flips.items()))},
        "confusion_control": dict(sorted(confusion_control.items())),
        "confusion_treatment": dict(sorted(confusion_treatment.items())),
        "by_actual": {name: summarize(rows) for name, rows in by_actual.items()},
        "by_control_error": {name: summarize(rows) for name, rows in by_control_error.items()},
    }
    if args.family_looks > 1:
        family_alpha = 0.05 / args.family_looks
        result["multiplicity_sensitivity"] = {
            "method": "Bonferroni by repercentiling the moving-block bootstrap distribution",
            "family_looks": args.family_looks,
            "two_sided_confidence_level": 1 - family_alpha,
            "quantiles": [family_alpha / 2, 1 - family_alpha / 2],
            "overall_delta_ci": {
                metric: _moving_ci(
                    [float(row[f"{metric}_delta"]) for row in paired],
                    alpha=family_alpha,
                )
                for metric in ("rps", "brier", "log_loss")
            },
        }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
