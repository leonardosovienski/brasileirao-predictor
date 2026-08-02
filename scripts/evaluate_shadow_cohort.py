"""Strict evaluator for the frozen H3/H5 prospective shadow cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from src.data.prospective_shadow import PICK_REQUIRED, validate_pick, validate_settlement

ROOT = Path(__file__).resolve().parents[1]


def _dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith(("Z", "+00:00")):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value)) and float(value) > 1.0


def _hash(rows: list[dict[str, Any]]) -> str:
    payload = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for row in rows
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def evaluate(picks_path: Path, results_path: Path, min_sample: int = 100) -> dict[str, Any]:
    picks = (
        [json.loads(line) for line in picks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if picks_path.exists()
        else []
    )
    results = (
        [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if results_path.exists()
        else []
    )
    by_key = {(r.get("pick_id"), r.get("source_event_id"), r.get("selection")): r for r in results}
    seen: set[Any] = set()
    counts = {
        "emitted": len(picks),
        "eligible": 0,
        "rejected": 0,
        "matured": 0,
        "legacy_incomplete": 0,
    }
    eligible: list[dict[str, Any]] = []
    reasons: dict[str, int] = {}

    def reject(reason: str, legacy: bool = False) -> None:
        counts["rejected"] += 1
        counts["legacy_incomplete" if legacy else "rejected"] += 0
        reasons[reason] = reasons.get(reason, 0) + 1

    for pick in picks:
        key = (pick.get("pick_id"), pick.get("source_event_id"), pick.get("selection"))
        missing = [field for field in PICK_REQUIRED if pick.get(field) in (None, "")]
        legacy = not pick.get("predicted_at") or not pick.get("kickoff_at") or not pick.get("odds_captured_at")
        if pick.get("pick_id") is not None:
            if key in seen:
                reject("duplicate_pick")
                continue
            seen.add(key)
        if missing:
            reject("legacy_incomplete" if legacy else "missing_required_field")
            counts["legacy_incomplete"] += int(legacy)
            continue
        invalid = validate_pick(pick)
        if invalid:
            reject(invalid)
            continue
        predicted, kickoff, captured = (_dt(pick[f]) for f in ("predicted_at", "kickoff_at", "odds_captured_at"))
        if not predicted or not kickoff or not captured:
            reject("timezone_or_timestamp_invalid")
            continue
        if not (predicted < kickoff and captured < kickoff):
            reject("pre_event_clock_violation")
            continue
        if not _valid_number(pick["captured_odds"]):
            reject("invalid_odds")
            continue
        result = by_key.get(key)
        if result:
            invalid = validate_settlement(pick, result)
            if invalid:
                reject(invalid)
                continue
            settled = _dt(result["settled_at"])
            if not settled or settled < kickoff:
                reject("settlement_clock_invalid")
                continue
            merged = {**pick, **result}
            counts["matured"] += 1
        else:
            merged = pick
        counts["eligible"] += 1
        eligible.append(merged)
    verdict = "INCONCLUSIVE"
    return {
        "schema_version": "shadow-cohort-evaluation/v1",
        "cohort": "H3/H5",
        "counts": counts,
        "classification": {
            "LEGACY_INCOMPLETE": counts["legacy_incomplete"],
            "PROSPECTIVE_ELIGIBLE": counts["eligible"],
            "MATURED_ELIGIBLE": counts["matured"],
            "PROSPECTIVE_REJECTED": max(0, counts["rejected"] - counts["legacy_incomplete"]),
        },
        "rejections": reasons,
        "dataset_hash": _hash(eligible),
        "min_sample": min_sample,
        "metrics": {
            "closing_coverage": sum(bool(r.get("closing_odds")) for r in eligible) / len(eligible) if eligible else 0.0
        },
        "verdict": verdict,
        "capital_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--picks", type=Path, default=ROOT / "data/sombra_picks.jsonl")
    parser.add_argument("--results", type=Path, default=ROOT / "data/sombra_results.jsonl")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.picks, args.results)
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.with_suffix(args.output.suffix + ".tmp").write_text(encoded, encoding="utf-8")
        args.output.with_suffix(args.output.suffix + ".tmp").replace(args.output)
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
