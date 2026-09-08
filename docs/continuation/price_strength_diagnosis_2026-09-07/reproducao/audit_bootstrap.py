"""Independent audit of saved bootstrap summaries; no fitting or forecasting.

Each replicate expands sampled ISO weeks into the full list of fixture indices
and recomputes means over those fixtures. No weekly score/profit aggregates or
functions from evaluate_correction are reused.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs/DIAGNOSTICO_XG/CORRECAO"
PRIMARY = "quality_raw_market_blend"
CONTROLS = (
    "xg_calibrated_primary",
    "xg_raw_diagnostic",
    "old_raw_frozen_2024",
    "market_proportional_devig",
)
MARKETS = ("1x2", "ou25", "btts")
METRICS = ("brier", "log_loss")
SEED = 20260908
REPLICATES = 2000
EXPECTED_WEEKS = 33
TOLERANCE = 1e-12


def load_bytes(name):
    content = (OUTPUT / name).read_bytes()
    return json.loads(content), {
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def number(value):
    if type(value) not in (int, float):
        raise TypeError("saved metrics must be numeric")
    if not math.isfinite(value):
        raise ValueError("saved metrics must be finite")
    return float(value)


def net_profit(row, arm):
    bet = row["bets"][arm]
    if bet is None:
        return 0.0
    if not isinstance(bet, dict):
        raise TypeError("saved bet must be an object or null")
    return number(bet["settlement"]["net_profit_units"])


def iso_week(row):
    kickoff = datetime.fromisoformat(row["kickoff"].replace("Z", "+00:00"))
    if kickoff.tzinfo is None or kickoff.utcoffset() is None:
        raise ValueError("saved kickoff has no timezone")
    year, week, _ = kickoff.astimezone(UTC).isocalendar()
    return year, week


def main():
    rows, rows_record = load_bytes("event_results.json")
    result, result_record = load_bytes("results.json")
    manifest, manifest_record = load_bytes("MANIFEST.json")
    if not isinstance(rows, list) or not rows:
        raise ValueError("event results must be a nonempty array")
    if len({row["event_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate fixture ID in the saved common panel")
    if any(row["common"] is not True for row in rows):
        raise ValueError("noncommon fixture in the bootstrap input")

    checks = []

    def exact(path, expected, actual):
        checks.append(
            {
                "path": path,
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )

    def close(path, expected, actual):
        expected, actual = number(expected), number(actual)
        error = abs(expected - actual)
        checks.append(
            {
                "path": path,
                "expected": expected,
                "actual": actual,
                "absolute_error": error,
                "passed": error <= TOLERANCE,
            }
        )

    exact(
        "input_hash/event_results.json",
        manifest["files"]["event_results.json"],
        rows_record["sha256"],
    )
    exact(
        "input_hash/results.json",
        manifest["files"]["results.json"],
        result_record["sha256"],
    )
    exact("coverage/new_common", result["coverage"]["new_common"], len(rows))
    saved = result["bootstrap_common"]
    exact("bootstrap/replicates", REPLICATES, saved["replicates"])
    exact("bootstrap/seed", SEED, saved["seed"])
    exact("bootstrap/control_names", sorted(CONTROLS), sorted(saved["comparisons"]))

    fixture_weeks = [iso_week(row) for row in rows]
    ordered_weeks = sorted(set(fixture_weeks))
    exact("actual/week_count", EXPECTED_WEEKS, len(ordered_weeks))
    exact("bootstrap/week_count", len(ordered_weeks), saved["weeks"])
    if len(ordered_weeks) != EXPECTED_WEEKS:
        raise ValueError("unexpected week universe for this fixed audit")
    week_members = {key: [] for key in ordered_weeks}
    for index, key in enumerate(fixture_weeks):
        week_members[key].append(index)

    columns = [
        (control, market, metric)
        for control in CONTROLS
        for market in MARKETS
        for metric in METRICS
    ]
    columns += [(control, "net_per_fixture", None) for control in CONTROLS]
    deltas = np.empty((len(rows), len(columns)), dtype=float)
    for column, (control, market, metric) in enumerate(columns):
        for index, row in enumerate(rows):
            if metric is None:
                deltas[index, column] = net_profit(row, PRIMARY) - net_profit(
                    row, control
                )
            else:
                deltas[index, column] = number(
                    row["scores"][PRIMARY][market][metric]
                ) - number(row["scores"][control][market][metric])

    # Sampling is paired: each expanded replicate serves every metric/control.
    choices = np.random.default_rng(SEED).integers(
        0, len(ordered_weeks), size=(REPLICATES, len(ordered_weeks))
    )
    replicate_means = np.empty((REPLICATES, len(columns)), dtype=float)
    denominator_counts = Counter()
    for replicate, chosen_weeks in enumerate(choices):
        indices = [
            index
            for choice in chosen_weeks
            for index in week_members[ordered_weeks[int(choice)]]
        ]
        denominator_counts[len(indices)] += 1
        # Direct fixture-level mean, deliberately without precomputed group sums.
        sample = deltas[indices, :]
        for column in range(len(columns)):
            replicate_means[replicate, column] = math.fsum(sample[:, column]) / len(
                indices
            )

    intervals = np.quantile(replicate_means, [0.025, 0.975], axis=0, method="linear")
    recomputed = {}
    for column, (control, market, metric) in enumerate(columns):
        reference = saved["comparisons"][control]
        if metric is None:
            reference = reference["net_per_fixture"]
            path = f"{control}/net_per_fixture"
        else:
            reference = reference["probabilistic"][market][metric]
            path = f"{control}/{market}/{metric}"
        mean = math.fsum(deltas[:, column]) / len(rows)
        ci = [float(intervals[0, column]), float(intervals[1, column])]
        close(f"{path}/delta_mean", reference["delta_mean"], mean)
        close(f"{path}/ci95_lower", reference["ci95_descriptive"][0], ci[0])
        close(f"{path}/ci95_upper", reference["ci95_descriptive"][1], ci[1])
        recomputed[path] = {"delta_mean": mean, "ci95_descriptive": ci}

    for name, expected in (
        ("event_results.json", rows_record),
        ("results.json", result_record),
        ("MANIFEST.json", manifest_record),
    ):
        exact(
            f"unchanged/{name}",
            expected["sha256"],
            hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest(),
        )
    failed = [check for check in checks if not check["passed"]]
    audit = {
        "schema_version": "price-strength-bootstrap-independent-audit/1",
        "status": "PASS" if not failed else "FAIL",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "method": "Expand sampled ISO weeks into fixture indices; math.fsum over each complete replicate; paired draws",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": {
            "event_results.json": rows_record,
            "results.json": result_record,
            "MANIFEST.json": manifest_record,
        },
        "no_model_import_fit_or_forecast": True,
        "saved_scores_and_settlements_used": True,
        "fixtures": len(rows),
        "weeks": len(ordered_weeks),
        "replicates": REPLICATES,
        "seed": SEED,
        "controls": list(CONTROLS),
        "statistics": len(columns),
        "no_bet_fixtures_retained": {
            arm: sum(row["bets"][arm] is None for row in rows)
            for arm in (PRIMARY, *CONTROLS)
        },
        "iso_week_membership_counts": {
            f"{year}-W{week:02}": len(week_members[(year, week)])
            for year, week in ordered_weeks
        },
        "replicate_fixture_count_distribution": dict(
            sorted(denominator_counts.items())
        ),
        "absolute_tolerance": TOLERANCE,
        "checks_count": len(checks),
        "failed_checks": len(failed),
        "max_absolute_numeric_error": max(
            check.get("absolute_error", 0) for check in checks
        ),
        "checks": checks,
        "recomputed_intervals": recomputed,
        "limitations": [
            "Audits saved bootstrap arithmetic, not the original score or settlement calculation.",
            "Intervals are descriptive; no correction for previous searches or post-diagnosis selection.",
            "No forecasts, model fitting, new outcomes or economic strategy runs were performed.",
        ],
    }
    with (OUTPUT / "bootstrap_audit.json").open("x", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(
        json.dumps(
            {
                key: audit[key]
                for key in (
                    "status",
                    "fixtures",
                    "weeks",
                    "replicates",
                    "statistics",
                    "checks_count",
                    "failed_checks",
                    "max_absolute_numeric_error",
                )
            }
        )
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
