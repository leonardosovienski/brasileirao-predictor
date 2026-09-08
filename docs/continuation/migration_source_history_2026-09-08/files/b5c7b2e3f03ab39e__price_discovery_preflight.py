"""Read-only, synthetic cadence preflight; never loads a scientific cohort."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from brasileirao_scripts.collect_odds_a1 import due_label

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "odds_snapshot_v1.json"
POLICY = ROOT / "contracts" / "a1-ou25-phase0-policy.json"
KICKOFF = datetime(2026, 1, 3, tzinfo=UTC)  # Fictional event, no source data.
TICK_MINUTES = 15


def simulate_schedule(mode: str, phase_minutes: int) -> list[dict[str, Any]]:
    """Exercise the actual due-label function with successful ideal captures."""
    if mode not in {"economic", "full"} or phase_minutes not in range(TICK_MINUTES):
        raise ValueError("expected economic/full and an integer phase from 0 to 14")
    now = KICKOFF - timedelta(minutes=1440 + TICK_MINUTES - phase_minutes)
    completed: set[str] = set()
    captures: list[dict[str, Any]] = []
    while now < KICKOFF:
        label = due_label(KICKOFF, now, completed, mode=mode)
        if label is not None:
            captures.append(
                {
                    "label": label,
                    "minutes_before_kickoff": int((KICKOFF - now).total_seconds() / 60),
                }
            )
            completed.add(label)
        now += timedelta(minutes=TICK_MINUTES)
    return captures


def build_report() -> dict[str, Any]:
    """Read only two versioned contracts; all schedule rows are synthetic."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    properties = schema["properties"]
    phases = []
    for phase in range(TICK_MINUTES):
        economic = simulate_schedule("economic", phase)
        full = simulate_schedule("full", phase)
        phases.append(
            {
                "phase_minutes": phase,
                "economic": economic,
                "economic_missing_labels": [
                    f"T-{window}m"
                    for window in policy["capture_windows_minutes"]
                    if f"T-{window}m" not in {row["label"] for row in economic}
                ],
                "full": full,
                "full_max_captures_per_utc_hour": max(
                    sum(other["label"] == row["label"] for other in full) for row in full
                ),
            }
        )
    execution_fields = [
        "source_price_updated_at",
        "request_sent_at",
        "response_received_at",
        "request_latency_ms",
        "available_stake",
        "accepted_odds",
    ]
    return {
        "schema_version": "price-discovery-preflight/1",
        "status": "SYNTHETIC_PREFLIGHT_ONLY",
        "inputs": ["schemas/odds_snapshot_v1.json", "contracts/a1-ou25-phase0-policy.json"],
        "real_cohort_read": False,
        "network_calls": 0,
        "database_access": False,
        "capital_enabled": False,
        "observed_provider_coverage": None,
        "declared_support": {
            "bookmakers": properties["bookmaker"]["enum"],
            "markets": properties["market"]["enum"],
            "time_fields": [name for name, spec in properties.items() if spec.get("format") == "date-time"],
            "additional_properties_allowed": schema["additionalProperties"],
            "execution_fields_absent": [name for name in execution_fields if name not in properties],
            "forbidden_labels": policy["labels_forbidden"],
            "threshold_frozen": policy["threshold_frozen"],
        },
        "simulation": {
            "kickoff_utc": KICKOFF.isoformat(),
            "tick_minutes": TICK_MINUTES,
            "phase_definition": "integer minute after kickoff minus 1455 minutes",
            "assumptions": [
                "fictional event; no real fixture identifiers or odds",
                "ideal successful captures; no latency, quota failures, reschedules or downtime",
                "first tick precedes T-24h; stop strictly before kickoff",
                "15 deterministic phases are scenarios, never an economic sample",
            ],
            "phases_missing_t10": [row["phase_minutes"] for row in phases if "T-10m" in row["economic_missing_labels"]],
            "phases": phases,
        },
        "limits": [
            "configured books and markets do not establish observed coverage",
            "job ticks do not establish quote capture cadence",
            "captured_at is a collector clock; source freshness and receipt ordering remain unverified",
            "schema fields do not prove executability or price leadership",
            "future quotes and closing prices require a separately frozen prospective protocol",
            "repeated books, selections and timestamps for one event are dependent observations",
        ],
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
