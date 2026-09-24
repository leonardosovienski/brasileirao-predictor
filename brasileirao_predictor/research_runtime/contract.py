"""Brasileirão research contract: request/result schemas owned by the domain (Stage A).

No envelope, transport, signing or CAIN concepts live here. Requests arrive as local
files (requester trust LOCAL_FILE_ONLY). Every identifier that leaves the domain is
qualified with the ``brasileirao:`` prefix (C18).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from typing import Any

DOMAIN_PREFIX = "brasileirao"
REQUEST_SCHEMA = "brasileirao-research-request/1"
RESULT_SCHEMA = "brasileirao-research-result/1"
OUTCOME_SCHEMA = "brasileirao-research-outcome/1"
REQUESTER_TRUST = "LOCAL_FILE_ONLY"

REQUEST_TYPES = {"WALKFORWARD_FORECAST_EVALUATION"}
REFERENCE_KINDS = ("dataset", "model", "features", "baseline", "cost_model")
OPTIONAL_REFERENCE_KINDS = ("odds",)
PRIORITIES = ("LOW", "NORMAL", "HIGH")
TARGETS = ("1X2", "OU25")
COMPETITIONS = ("Brasileirão Série A",)
MAX_EVENTS = 400
LEAD_MINUTES = (15, 10080)

# Closed enum of terminal research results (C24.1 result_states).
RESULT_STATES = (
    "WATCH_NO_CAPITAL",
    "NO_EDGE",
    "INCONCLUSIVE",
    "REFUTED",
    "CLOSED_INSUFFICIENT_SAMPLE",
    "INCONCLUSIVE_DATA_QUALITY",
    "FORECAST_ONLY",
    "FAILED_OPERATIONAL",
)
# Outcomes of one submission; only RESULT/DUPLICATE carry a stored result.
OUTCOME_STATUSES = (
    "RESULT",
    "DUPLICATE",
    "REJECTED",
    "CONFLICT",
    "NOT_READY",
    "OPS_FAILED_RETRYABLE",
    "TEMPORAL_INTEGRITY_VIOLATION",
    "RECONCILIATION_REQUIRED",
)
EXIT_CODES = {
    "RESULT": 0,
    "DUPLICATE": 0,
    "REJECTED": 2,
    "CONFLICT": 2,
    "NOT_READY": 3,
    "OPS_FAILED_RETRYABLE": 3,
    "TEMPORAL_INTEGRITY_VIOLATION": 4,
    "RECONCILIATION_REQUIRED": 5,
}
OPERATIONAL_STATES = ("SUCCEEDED", "FAILED", "TIMEOUT", "SKIPPED_ALREADY_SUCCEEDED")
SCIENTIFIC_STATES = ("SUPPORTED", "REFUTED", "INCONCLUSIVE", "INSUFFICIENT_SAMPLE", "NOT_EVALUATED")
ECONOMIC_STATES = ("WATCH", "NO_EDGE", "NOT_EVALUATED")

_ID = re.compile(r"^brasileirao:[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_UTC_Z = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


class ContractError(ValueError):
    """A request or result does not match the Brasileirão contract (fail closed)."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def canonical(value: Any) -> bytes:
    """Canonical UTF-8 JSON: sorted keys, no whitespace, no NaN/Infinity."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def content_hash(value: Any) -> str:
    return digest(canonical(value))


def loads_strict(raw: bytes | str) -> Any:
    """Parse JSON rejecting duplicate keys and non-finite constants."""

    def pairs(items):
        out = {}
        for key, val in items:
            if key in out:
                raise ContractError("SCHEMA_INVALID", f"duplicate key {key!r}")
            out[key] = val
        return out

    def constant(name):
        raise ContractError("SCHEMA_INVALID", f"non-finite constant {name}")

    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except UnicodeDecodeError as exc:
        raise ContractError("SCHEMA_INVALID", "request is not UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ContractError("SCHEMA_INVALID", "invalid JSON") from exc


def utc(value: Any, field: str) -> datetime:
    """Request/result instants: exactly YYYY-MM-DDTHH:MM:SSZ (no offset, no guessing)."""
    if type(value) is not str or not _UTC_Z.fullmatch(value):
        raise ContractError("SCHEMA_INVALID", f"{field} must be YYYY-MM-DDTHH:MM:SSZ (UTC)")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError as exc:
        raise ContractError("SCHEMA_INVALID", f"{field} is not a timestamp") from exc


def utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("instant must be timezone-aware")
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _keys(value: Any, required: set[str], optional: set[str], label: str) -> None:
    if type(value) is not dict:
        raise ContractError("SCHEMA_INVALID", f"{label} must be an object")
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing or extra:
        raise ContractError("SCHEMA_INVALID", f"{label}: missing {sorted(missing)} unknown {sorted(extra)}")


def qualified_id(value: Any, field: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise ContractError("SCHEMA_INVALID", f"{field} must be a brasileirao:-qualified identifier")
    return value


def validate_request(request: Any) -> dict:
    """Validate a Brasileirão research request; returns it unchanged or raises ContractError.

    The request declares intent only: request type, hypothesis, competition/season/events,
    target, cutoff, decision lead and references by (name, version). It can never name a
    command, module, path, URL, SQL, handler or capital permission.
    """
    _keys(
        request,
        {
            "schema_version",
            "request_id",
            "request_type",
            "research_id",
            "hypothesis_id",
            "competition",
            "season",
            "target",
            "events",
            "data_cutoff",
            "decision_lead_minutes",
            "references",
            "priority_hint",
        },
        {"client_ref"},
        "request",
    )
    if request["schema_version"] != REQUEST_SCHEMA:
        raise ContractError("SCHEMA_INVALID", "schema_version")
    for field in ("request_id", "research_id", "hypothesis_id"):
        qualified_id(request[field], field)
    if request["request_type"] not in REQUEST_TYPES:
        raise ContractError("REQUEST_TYPE_NOT_ALLOWED", str(request["request_type"])[:64])
    if request["competition"] not in COMPETITIONS:
        raise ContractError("SCHEMA_INVALID", "competition")
    season = request["season"]
    if type(season) is not int or not 2000 <= season <= 2100:
        raise ContractError("PARAMETER_OUT_OF_BOUNDS", "season")
    if request["target"] not in TARGETS:
        raise ContractError("SCHEMA_INVALID", "target")
    events = request["events"]
    _keys(events, {"kickoff_from", "kickoff_to"}, {"fixtures"}, "events")
    start, end = utc(events["kickoff_from"], "events.kickoff_from"), utc(events["kickoff_to"], "events.kickoff_to")
    if not start < end:
        raise ContractError("PARAMETER_OUT_OF_BOUNDS", "events window must satisfy kickoff_from < kickoff_to")
    if "fixtures" in events:
        fixtures = events["fixtures"]
        if type(fixtures) is not list or not 1 <= len(fixtures) <= MAX_EVENTS:
            raise ContractError("PARAMETER_OUT_OF_BOUNDS", "events.fixtures")
        seen = set()
        for index, item in enumerate(fixtures):
            _keys(item, {"event_id", "kickoff_at"}, set(), f"events.fixtures[{index}]")
            if type(item["event_id"]) is not int or item["event_id"] <= 0:
                raise ContractError("SCHEMA_INVALID", f"events.fixtures[{index}].event_id")
            kickoff = utc(item["kickoff_at"], f"events.fixtures[{index}].kickoff_at")
            if not start <= kickoff < end:
                raise ContractError("PARAMETER_OUT_OF_BOUNDS", f"events.fixtures[{index}] outside the window")
            if item["event_id"] in seen:
                raise ContractError("SCHEMA_INVALID", "duplicate event_id in events.fixtures")
            seen.add(item["event_id"])
    utc(request["data_cutoff"], "data_cutoff")
    lead = request["decision_lead_minutes"]
    if type(lead) is not int or not LEAD_MINUTES[0] <= lead <= LEAD_MINUTES[1]:
        raise ContractError("PARAMETER_OUT_OF_BOUNDS", "decision_lead_minutes")
    refs = request["references"]
    _keys(refs, set(REFERENCE_KINDS), set(OPTIONAL_REFERENCE_KINDS), "references")
    for kind, ref in refs.items():
        _keys(ref, {"name", "version"}, set(), f"references.{kind}")
        for field in ("name", "version"):
            if type(ref[field]) is not str or not _NAME.fullmatch(ref[field]):
                raise ContractError("SCHEMA_INVALID", f"references.{kind}.{field}")
    if request["priority_hint"] not in PRIORITIES:
        raise ContractError("SCHEMA_INVALID", "priority_hint")
    if "client_ref" in request:
        try:
            raw = canonical(request["client_ref"])
        except (TypeError, ValueError) as exc:
            raise ContractError("SCHEMA_INVALID", "client_ref must be JSON") from exc
        if len(raw) > 1024:
            raise ContractError("SCHEMA_INVALID", "client_ref larger than 1024 bytes")
    return request


def idempotency_key(request: dict) -> str:
    """Two submissions are the same logical request iff they share request_id."""
    return request["request_id"]


def request_content_hash(request: dict) -> str:
    """Content identity of a request; client_ref is excluded (opaque, echoed back)."""
    return content_hash({key: value for key, value in request.items() if key != "client_ref"})


def _finite(value: Any, path: str = "result") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError("RESULT_INVALID", f"non-finite value at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            _finite(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _finite(item, f"{path}[{index}]")


RESULT_FIELDS = {
    "schema_version",
    "result_id",
    "request_id",
    "admission_id",
    "experiment_id",
    "research_id",
    "hypothesis_id",
    "result_state",
    "operational_state",
    "scientific_state",
    "economic_state",
    "capital_permission",
    "produced_at",
    "core_facts",
    "ops_facts",
    "domain_facts",
    "provenance",
}


def validate_result(result: Any) -> dict:
    """Validate a Brasileirão research result, including authority-separation invariants."""
    _keys(result, RESULT_FIELDS, set(), "result")
    if result["schema_version"] != RESULT_SCHEMA:
        raise ContractError("RESULT_INVALID", "schema_version")
    for field in ("result_id", "request_id", "admission_id", "experiment_id", "research_id", "hypothesis_id"):
        qualified_id(result[field], field)
    if result["result_state"] not in RESULT_STATES:
        raise ContractError("RESULT_INVALID", "result_state")
    if result["operational_state"] not in OPERATIONAL_STATES:
        raise ContractError("RESULT_INVALID", "operational_state")
    if result["scientific_state"] not in SCIENTIFIC_STATES:
        raise ContractError("RESULT_INVALID", "scientific_state")
    if result["economic_state"] not in ECONOMIC_STATES:
        raise ContractError("RESULT_INVALID", "economic_state")
    if result["capital_permission"] is not False:
        raise ContractError("RESULT_INVALID", "capital_permission must be false")
    utc(result["produced_at"], "produced_at")
    for block in ("core_facts", "ops_facts", "domain_facts", "provenance"):
        if type(result[block]) is not dict:
            raise ContractError("RESULT_INVALID", f"{block} must be an object")
    # Authority separation: operations never imply science; science never implies edge;
    # edge never implies capital.
    if result["operational_state"] not in {"SUCCEEDED", "SKIPPED_ALREADY_SUCCEEDED"}:
        if (result["scientific_state"], result["economic_state"], result["result_state"]) != (
            "NOT_EVALUATED",
            "NOT_EVALUATED",
            "FAILED_OPERATIONAL",
        ):
            raise ContractError("RESULT_INVALID", "failed operation cannot carry scientific or economic state")
    elif result["result_state"] == "FAILED_OPERATIONAL":
        raise ContractError("RESULT_INVALID", "FAILED_OPERATIONAL requires a failed operation")
    if result["economic_state"] == "WATCH" and result["scientific_state"] != "SUPPORTED":
        raise ContractError("RESULT_INVALID", "economic WATCH requires SUPPORTED science")
    if result["result_state"] == "WATCH_NO_CAPITAL" and result["economic_state"] != "WATCH":
        raise ContractError("RESULT_INVALID", "WATCH_NO_CAPITAL requires economic WATCH")
    if result["result_state"] == "FORECAST_ONLY" and (
        result["scientific_state"] != "NOT_EVALUATED" or result["economic_state"] != "NOT_EVALUATED"
    ):
        raise ContractError("RESULT_INVALID", "FORECAST_ONLY carries no scientific or economic claim")
    for field in ("request_content_hash", "logical_experiment_hash"):
        value = result["provenance"].get(field)
        if value is not None and not _HASH.fullmatch(str(value)):
            raise ContractError("RESULT_INVALID", f"provenance.{field}")
    _finite(result)
    canonical(result)
    return result


__all__ = [
    "DOMAIN_PREFIX",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "OUTCOME_SCHEMA",
    "REQUESTER_TRUST",
    "REQUEST_TYPES",
    "REFERENCE_KINDS",
    "OPTIONAL_REFERENCE_KINDS",
    "TARGETS",
    "RESULT_STATES",
    "OUTCOME_STATUSES",
    "EXIT_CODES",
    "OPERATIONAL_STATES",
    "SCIENTIFIC_STATES",
    "ECONOMIC_STATES",
    "ContractError",
    "canonical",
    "digest",
    "content_hash",
    "loads_strict",
    "utc",
    "utc_text",
    "qualified_id",
    "validate_request",
    "validate_result",
    "idempotency_key",
    "request_content_hash",
]
