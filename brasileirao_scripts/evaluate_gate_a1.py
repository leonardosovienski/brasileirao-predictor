"""Veredito mecânico do Gate A1; modo econômico nunca pode emitir PASS."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_METRICS = ROOT / "data" / "collector_metrics"


def load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def consecutive(days: list[date]) -> bool:
    return len(days) == 7 and all((right - left).days == 1 for left, right in zip(days, days[1:], strict=False))


def evaluate(metrics_root: Path) -> dict[str, Any]:
    files = sorted(path for path in metrics_root.glob("????-??-??.json"))[-7:]
    metrics = [load_json(path, {}) for path in files]
    days = [date.fromisoformat(path.stem) for path in files]
    audit = load_json(metrics_root / "manual_audit.json", {})
    tests = load_json(metrics_root / "test_attestation.json", {})
    rotation = load_json(metrics_root / "key_rotation_attestation.json", {})

    def minimum(field: str, default: float = 0.0) -> float:
        return min((float(item.get(field, default)) for item in metrics), default=default)

    def maximum(field: str, default: float = float("inf")) -> float:
        return max((float(item.get(field, default)) for item in metrics), default=default)

    criteria = {
        "oddspapi_key_rotated_and_attested": rotation.get("rotated") is True
        and bool(str(rotation.get("rotated_at", "")).strip())
        and bool(str(rotation.get("attested_by", "")).strip()),
        "sources_5_soft_plus_reference": bool(metrics)
        and all(item.get("reference_present") and int(item.get("soft_books_count", 0)) >= 5 for item in metrics),
        "seven_consecutive_days": consecutive(days),
        "no_gap_over_1h": bool(metrics)
        and all(item.get("max_gap_seconds") is not None and float(item["max_gap_seconds"]) <= 3600 for item in metrics),
        "event_coverage_ge_90pct": minimum("event_coverage") >= 0.90,
        "market_coverage_ge_95pct": minimum("market_coverage") >= 0.95,
        "continuity_ge_95pct": bool(metrics)
        and all(item.get("continuity") is not None and float(item["continuity"]) >= 0.95 for item in metrics),
        "identity_resolution_ge_99pct": minimum("identity_resolution_rate") >= 0.99,
        "conflict_rate_lt_0_1pct": maximum("conflict_rate") < 0.001,
        "manual_audit_50_and_tests_green": int(audit.get("events_audited", 0)) >= 50
        and audit.get("passed") is True
        and tests.get("contract_tests_green") is True,
    }
    economic = bool(metrics) and any(str(item.get("mode", "")).startswith("economic") for item in metrics)
    if not metrics:
        verdict = "NOT_STARTED"
    elif economic:
        verdict = "REHEARSAL_ONLY_BUDGETED"
    else:
        verdict = "PASS" if all(criteria.values()) else "FAIL_RESTART_CLOCK"
    return {
        "schema_version": "gate_a1_verdict/1",
        "verdict": verdict,
        "mode": "economic" if economic else "full",
        "days": [day.isoformat() for day in days],
        "criteria": criteria,
        "external_evidence": {
            "key_rotation_attestation_present": bool(rotation),
            "manual_audit_events": int(audit.get("events_audited", 0)),
            "contract_tests_attested_green": tests.get("contract_tests_green") is True,
        },
        "restart_clock_required": verdict == "FAIL_RESTART_CLOCK",
        "capital_enabled": False,
        "homologated": verdict == "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics-dir", type=Path, default=DEFAULT_METRICS)
    args = parser.parse_args()
    result = evaluate(args.metrics_dir)
    args.metrics_dir.mkdir(parents=True, exist_ok=True)
    (args.metrics_dir / "gate_a1_verdict.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] in {"PASS", "REHEARSAL_ONLY_BUDGETED", "NOT_STARTED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
