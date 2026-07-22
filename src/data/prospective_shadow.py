"""Canonical, fail-closed record contract for H3/H5 prospective shadow."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any

PICK_REQUIRED = ("pick_id", "trial_id", "model_version", "code_commit", "predicted_at", "kickoff_at", "market", "selection", "captured_odds", "odds_captured_at", "bookmaker", "source", "source_event_id", "canonical_match_id", "closing_definition_version", "data_quality_status", "provenance_hash")
RESULT_REQUIRED = ("pick_id", "result", "settled_at", "settlement_status", "closing_odds", "closing_captured_at", "closing_definition_version", "provenance_hash")


def utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith(("Z", "+00:00")):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def record_hash(record: dict[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "provenance_hash"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_pick(record: dict[str, Any]) -> str | None:
    missing = [key for key in PICK_REQUIRED if record.get(key) in (None, "")]
    if missing: return "missing_required_field"
    times = [utc_timestamp(record[key]) for key in ("predicted_at", "kickoff_at", "odds_captured_at")]
    if not all(times): return "timezone_or_timestamp_invalid"
    if not (times[0] < times[1] and times[2] < times[1]): return "pre_event_clock_violation"
    odd = record["captured_odds"]
    if not isinstance(odd, (int, float)) or not math.isfinite(odd) or odd <= 1: return "invalid_odds"
    if record.get("synthetic") or record.get("environment") == "TEST": return "non_production_record"
    if record["provenance_hash"] != record_hash(record): return "provenance_hash_mismatch"
    return None


def validate_settlement(pick: dict[str, Any], result: dict[str, Any]) -> str | None:
    missing = [key for key in RESULT_REQUIRED if result.get(key) in (None, "")]
    if missing: return "incomplete_settlement"
    settled, closed, kickoff = utc_timestamp(result["settled_at"]), utc_timestamp(result["closing_captured_at"]), utc_timestamp(pick["kickoff_at"])
    if not settled or not closed or not kickoff: return "timezone_or_timestamp_invalid"
    if closed >= kickoff: return "closing_post_kickoff"
    if settled < kickoff: return "settlement_clock_invalid"
    if not isinstance(result["closing_odds"], (int, float)) or not math.isfinite(result["closing_odds"]) or result["closing_odds"] <= 1: return "invalid_closing_odds"
    if result["provenance_hash"] != record_hash(result): return "provenance_hash_mismatch"
    return None
