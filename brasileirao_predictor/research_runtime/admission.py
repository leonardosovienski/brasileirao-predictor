"""Brasileirão-owned durable admission for local research requests (no envelope).

This module does not execute requests. It validates a research request against the domain
contract, applies the operator admission policy (season policy with the sealed holdout,
protected hypotheses, competitions, limits), maps the request type to one compiled
handler identity and freezes registry references for the executor.

Requester trust is LOCAL_FILE_ONLY: requests are files placed by the operator. The request
never chooses a command, module, path, URL, SQL, handler or capital permission.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from brasileirao_predictor.research_runtime.contract import (
    REQUESTER_TRUST,
    ContractError,
    canonical,
    content_hash,
    digest,
    request_content_hash,
    utc,
    validate_request,
)
from brasileirao_predictor.research_runtime.faults import fault

POLICY_SCHEMA = "BrasileiraoResearchAdmissionPolicyV1"
DECISIONS = {"ACCEPTED", "REJECTED", "CONFLICT", "REQUIRES_READMISSION"}
KNOWN_HANDLERS = {"WALKFORWARD_FORECAST_EVALUATION": "brasileirao.handlers.walkforward_forecast_evaluation.v1"}
SEASON_LABELS = {"DEVELOPMENT", "VALIDATION", "HOLDOUT_SEALED", "EXPLORATORY"}
REQUIRED_PROTECTED = {"brasileirao:H8", "brasileirao:H9", "brasileirao:H14", "brasileirao:H15", "brasileirao:A1"}
LIMIT_FIELDS = {
    "max_pending_requests",
    "max_request_bytes",
    "max_parameter_bytes",
    "max_concurrency",
    "cpu_seconds",
    "memory_mb",
    "disk_mb",
    "timeout_seconds",
    "max_retries",
    "max_priority",
}
BUDGET_FIELDS = ("max_concurrency", "cpu_seconds", "memory_mb", "disk_mb", "timeout_seconds", "max_retries")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _keys(value: Any, expected: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f"POLICY_INVALID: unexpected or missing {label} fields")


def load_policy(path: Path) -> dict:
    policy = json.loads(Path(path).read_text(encoding="utf-8"))
    _keys(
        policy,
        {
            "schema_version",
            "policy_id",
            "policy_version",
            "owner",
            "requester_trust",
            "handlers",
            "hypotheses",
            "protected_hypotheses",
            "season_policy",
            "allowed_competitions",
            "registry",
            "limits",
        },
        "policy",
    )
    if policy["schema_version"] != POLICY_SCHEMA or policy["owner"] != "BRASILEIRAO_OPERATOR":
        raise ValueError("POLICY_INVALID: Brasileirão/operator ownership required")
    if policy["requester_trust"] != REQUESTER_TRUST:
        raise ValueError("POLICY_INVALID: requester_trust must be LOCAL_FILE_ONLY in stage A")
    if type(policy["policy_id"]) is not str or type(policy["policy_version"]) is not int:
        raise ValueError("POLICY_INVALID: identity")
    if policy["handlers"] != KNOWN_HANDLERS:
        raise ValueError("POLICY_INVALID: handlers must equal the compiled allowlist")
    if type(policy["hypotheses"]) is not dict or not policy["hypotheses"]:
        raise ValueError("POLICY_INVALID: hypotheses")
    for hypothesis, entry in policy["hypotheses"].items():
        if not hypothesis.startswith("brasileirao:"):
            raise ValueError("POLICY_INVALID: hypothesis ids must be brasileirao:-qualified")
        _keys(entry, {"hypothesis_family", "purpose"}, "hypothesis entry")
    protected = policy["protected_hypotheses"]
    if type(protected) is not list or not REQUIRED_PROTECTED <= set(protected):
        raise ValueError("POLICY_INVALID: protected_hypotheses must include H8, H9, H14, H15 and A1")
    if set(protected) & set(policy["hypotheses"]):
        raise ValueError("POLICY_INVALID: a protected hypothesis cannot be admitted")
    seasons = policy["season_policy"]
    if (
        type(seasons) is not dict
        or not seasons
        or any(not key.isdigit() or value not in SEASON_LABELS for key, value in seasons.items())
    ):
        raise ValueError("POLICY_INVALID: season_policy")
    if seasons.get("2025") != "HOLDOUT_SEALED":
        raise ValueError("POLICY_INVALID: 2025 must stay HOLDOUT_SEALED")
    if type(policy["allowed_competitions"]) is not list or not policy["allowed_competitions"]:
        raise ValueError("POLICY_INVALID: allowed_competitions")
    if type(policy["registry"]) is not list or not policy["registry"]:
        raise ValueError("POLICY_INVALID: registry")
    seen = set()
    for entry in policy["registry"]:
        _keys(entry, {"kind", "name", "version", "revision_id", "content_hash"}, "registry entry")
        identity = (entry["kind"], entry["name"], entry["version"])
        if identity in seen:
            raise ValueError("POLICY_INVALID: duplicate registry entry")
        if type(entry["content_hash"]) is not str or len(entry["content_hash"]) != 64:
            raise ValueError("POLICY_INVALID: registry identity")
        seen.add(identity)
    _keys(policy["limits"], LIMIT_FIELDS, "limits")
    numeric = {key: value for key, value in policy["limits"].items() if key != "max_priority"}
    if any(type(value) is not int or value < 0 for value in numeric.values()):
        raise ValueError("POLICY_INVALID: numeric limits")
    if policy["limits"]["timeout_seconds"] < 1 or policy["limits"]["max_pending_requests"] < 1:
        raise ValueError("POLICY_INVALID: timeout and pending limits must be positive")
    if policy["limits"]["max_priority"] not in {"LOW", "NORMAL", "HIGH"}:
        raise ValueError("POLICY_INVALID: max_priority")
    return policy


class AdmissionStore:
    def __init__(self, path: Path, policy_path: Path, *, available_handlers=None):
        self.path = Path(path)
        self.policy_path = Path(policy_path)
        self.available_handlers = frozenset(
            KNOWN_HANDLERS.values() if available_handlers is None else available_handlers
        )
        if not self.available_handlers <= set(KNOWN_HANDLERS.values()):
            raise ValueError("Unknown local handler registration")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.policy()
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS request_inbox(
                  request_id TEXT PRIMARY KEY,
                  content_hash TEXT NOT NULL,
                  request BLOB NOT NULL,
                  received_at TEXT NOT NULL,
                  terminal_at TEXT,
                  result_id TEXT
                );
                CREATE TABLE IF NOT EXISTS admissions(
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  admission_id TEXT NOT NULL,
                  request_id TEXT NOT NULL,
                  content_hash TEXT NOT NULL,
                  decision TEXT NOT NULL,
                  reason_code TEXT NOT NULL,
                  policy_id TEXT NOT NULL,
                  policy_version INTEGER NOT NULL,
                  policy_hash TEXT NOT NULL,
                  decided_at TEXT NOT NULL,
                  resolved_references BLOB NOT NULL,
                  admitted_handler TEXT,
                  resource_budget BLOB NOT NULL,
                  normalized_priority TEXT
                );
                CREATE INDEX IF NOT EXISTS admissions_request ON admissions(request_id,sequence);
                CREATE TABLE IF NOT EXISTS invalid_submissions(
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  submission_hash TEXT NOT NULL,
                  reason_code TEXT NOT NULL,
                  detail TEXT NOT NULL,
                  decided_at TEXT NOT NULL
                );
                """
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def policy(self) -> dict:
        return load_policy(self.policy_path)

    @staticmethod
    def policy_hash(policy: dict) -> str:
        return content_hash(policy)

    @staticmethod
    def _resolve(policy: dict, request: dict) -> list[dict]:
        resolved = []
        for kind, ref in request["references"].items():
            match = next(
                (
                    entry
                    for entry in policy["registry"]
                    if (entry["kind"], entry["name"], entry["version"]) == (kind, ref["name"], ref["version"])
                ),
                None,
            )
            if match is None:
                raise PermissionError("REFERENCE_UNAUTHORIZED_OR_UNKNOWN")
            resolved.append({key: match[key] for key in ("kind", "name", "version", "revision_id", "content_hash")})
        return sorted(resolved, key=lambda item: item["kind"])

    @staticmethod
    def _priority(requested: str, maximum: str) -> str:
        levels = ["LOW", "NORMAL", "HIGH"]
        return levels[min(levels.index(requested), levels.index(maximum))]

    @staticmethod
    def _season_decision(policy: dict, request: dict) -> tuple[str, str] | None:
        season = request["season"]
        label = policy["season_policy"].get(str(season))
        start = utc(request["events"]["kickoff_from"], "events.kickoff_from")
        end = utc(request["events"]["kickoff_to"], "events.kickoff_to")
        # Any overlap with a sealed season is refused, whatever season the request names.
        for year, value in policy["season_policy"].items():
            if value != "HOLDOUT_SEALED":
                continue
            sealed_from = datetime(int(year), 1, 1, tzinfo=UTC)
            sealed_to = datetime(int(year) + 1, 1, 1, tzinfo=UTC)
            if start < sealed_to and end > sealed_from:
                return "REJECTED", "HOLDOUT_SEALED"
        if label is None:
            return "REJECTED", "SEASON_NOT_ALLOWED"
        if not (datetime(season, 1, 1, tzinfo=UTC) <= start and end <= datetime(season + 1, 1, 1, tzinfo=UTC)):
            return "REJECTED", "WINDOW_OUTSIDE_SEASON"
        return None

    def _evaluate(self, request: dict, policy: dict, size: int):
        limits = policy["limits"]
        if size > limits["max_request_bytes"]:
            return "REJECTED", "REQUEST_SIZE_LIMIT", [], None
        if len(canonical(request["events"])) > limits["max_parameter_bytes"]:
            return "REJECTED", "PARAMETER_SIZE_LIMIT", [], None
        if request["hypothesis_id"] in policy["protected_hypotheses"]:
            return "REJECTED", "PROTECTED_HYPOTHESIS", [], None
        if request["hypothesis_id"] not in policy["hypotheses"]:
            return "REJECTED", "HYPOTHESIS_NOT_ADMITTED", [], None
        if request["competition"] not in policy["allowed_competitions"]:
            return "REJECTED", "COMPETITION_NOT_ALLOWED", [], None
        season = self._season_decision(policy, request)
        if season is not None:
            return season[0], season[1], [], None
        handler = policy["handlers"].get(request["request_type"])
        if handler not in KNOWN_HANDLERS.values():
            return "REJECTED", "HANDLER_NOT_ALLOWED", [], None
        if handler not in self.available_handlers:
            return "REJECTED", "HANDLER_UNAVAILABLE", [], None
        try:
            resolved = self._resolve(policy, request)
        except PermissionError:
            return "REJECTED", "REFERENCE_UNAUTHORIZED_OR_UNKNOWN", [], None
        return "ACCEPTED", "ADMITTED", resolved, handler

    def _receipt(self, request, chash, policy, now, decision, reason, resolved, handler) -> dict:
        policy_hash = self.policy_hash(policy)
        budget = {key: policy["limits"][key] for key in BUDGET_FIELDS}
        admission_id = (
            "brasileirao:ADM-" + digest(canonical([request["request_id"], chash, policy_hash, decision, reason]))[:32]
        )
        return {
            "admission_id": admission_id,
            "request_id": request["request_id"],
            "content_hash": chash,
            "decision": decision,
            "reason_code": reason,
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
            "policy_hash": policy_hash,
            "decided_at": now,
            "resolved_references": resolved,
            "admitted_handler": handler,
            "resource_budget": budget,
            "normalized_priority": self._priority(request["priority_hint"], policy["limits"]["max_priority"])
            if decision == "ACCEPTED"
            else None,
        }

    @staticmethod
    def _persist_receipt(db: sqlite3.Connection, receipt: dict) -> None:
        db.execute(
            "INSERT INTO admissions(admission_id,request_id,content_hash,decision,reason_code,policy_id,"
            "policy_version,policy_hash,decided_at,resolved_references,admitted_handler,resource_budget,"
            "normalized_priority) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                receipt["admission_id"],
                receipt["request_id"],
                receipt["content_hash"],
                receipt["decision"],
                receipt["reason_code"],
                receipt["policy_id"],
                receipt["policy_version"],
                receipt["policy_hash"],
                receipt["decided_at"],
                canonical(receipt["resolved_references"]),
                receipt["admitted_handler"],
                canonical(receipt["resource_budget"]),
                receipt["normalized_priority"],
            ),
        )

    def record_invalid(self, raw: bytes, error: ContractError) -> dict:
        """Audit an invalid submission. It never reaches the inbox."""
        entry = {
            "submission_hash": digest(raw),
            "reason_code": error.reason,
            "detail": str(error)[:500],
            "decided_at": _now(),
        }
        with self.connection() as db:
            db.execute(
                "INSERT INTO invalid_submissions(submission_hash,reason_code,detail,decided_at) VALUES(?,?,?,?)",
                (entry["submission_hash"], entry["reason_code"], entry["detail"], entry["decided_at"]),
            )
        return entry

    def submit(self, request: dict, *, size: int | None = None) -> dict:
        validate_request(request)
        policy = self.policy()
        now = _now()
        chash = request_content_hash(request)
        size = len(canonical(request)) if size is None else size
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT content_hash FROM request_inbox WHERE request_id=?", (request["request_id"],)
            ).fetchone()
            if existing and existing["content_hash"] != chash:
                receipt = self._receipt(
                    request, chash, policy, now, "CONFLICT", "REQUEST_ID_CONTENT_CONFLICT", [], None
                )
                self._persist_receipt(db, receipt)
                return receipt
            if existing:
                row = db.execute(
                    "SELECT * FROM admissions WHERE request_id=? AND content_hash=? AND decision='ACCEPTED' "
                    "ORDER BY sequence LIMIT 1",
                    (request["request_id"], chash),
                ).fetchone()
                decoded = self._decode_receipt(row)
                if decoded is None:
                    raise ValueError("ADMISSION_RECEIPT_NOT_FOUND")
                return decoded | {"duplicate": True}
            decision, reason, resolved, handler = self._evaluate(request, policy, size)
            pending = db.execute("SELECT count(*) FROM request_inbox WHERE terminal_at IS NULL").fetchone()[0]
            if decision == "ACCEPTED" and pending >= policy["limits"]["max_pending_requests"]:
                decision, reason, resolved, handler = "REJECTED", "PENDING_QUOTA", [], None
            receipt = self._receipt(request, chash, policy, now, decision, reason, resolved, handler)
            if decision == "ACCEPTED":
                db.execute(
                    "INSERT INTO request_inbox(request_id,content_hash,request,received_at) VALUES(?,?,?,?)",
                    (request["request_id"], chash, canonical(request), now),
                )
            self._persist_receipt(db, receipt)
            fault("before_admission_commit")  # dies with the transaction still open
        return receipt

    def mark_terminal(self, request_id: str, result_id: str) -> None:
        """Release the pending slot once an authoritative terminal outcome exists."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT terminal_at,result_id FROM request_inbox WHERE request_id=?", (request_id,)
            ).fetchone()
            if row is None:
                raise ValueError("REQUEST_NOT_FOUND")
            if row["terminal_at"] is not None:
                if row["result_id"] != result_id:
                    raise ValueError("TERMINAL_RESULT_CONFLICT")
                return
            db.execute(
                "UPDATE request_inbox SET terminal_at=?,result_id=? WHERE request_id=?", (_now(), result_id, request_id)
            )

    @staticmethod
    def _decode_receipt(row) -> dict | None:
        if row is None:
            return None
        value = dict(row)
        value.pop("sequence", None)
        for key in ("resolved_references", "resource_budget"):
            value[key] = json.loads(value[key])
        return value

    def receipt(self, request_id: str) -> dict | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM admissions WHERE request_id=? AND decision='ACCEPTED' ORDER BY sequence LIMIT 1",
                (request_id,),
            ).fetchone()
        return self._decode_receipt(row)

    def admitted_context(self, request_id: str) -> dict:
        """Return the immutable request and its accepted receipt, or fail closed."""
        with self.connection() as db:
            inbox = db.execute(
                "SELECT request,content_hash FROM request_inbox WHERE request_id=?", (request_id,)
            ).fetchone()
        receipt = self.receipt(request_id)
        if inbox is None or receipt is None or receipt["decision"] != "ACCEPTED":
            raise PermissionError("EXECUTION_NOT_AUTHORIZED: request has no accepted admission")
        request = json.loads(inbox["request"])
        if request_content_hash(request) != inbox["content_hash"] or inbox["content_hash"] != receipt["content_hash"]:
            raise ValueError("ADMISSION_STATE_CORRUPT: request content does not match its admission")
        return {"request": request, "request_content_hash": inbox["content_hash"], "receipt": receipt}

    def revalidate(self, request_id: str) -> dict:
        current = self.policy()
        previous = self.receipt(request_id)
        if previous is None:
            raise ValueError("ADMISSION_RECEIPT_NOT_FOUND")
        context = self.admitted_context(request_id)
        if previous["policy_hash"] != self.policy_hash(current):
            return {"decision": "REQUIRES_READMISSION", "reason_code": "POLICY_CHANGED"}
        decision, reason, resolved, handler = self._evaluate(
            context["request"], current, len(canonical(context["request"]))
        )
        if decision != "ACCEPTED":
            return {"decision": decision, "reason_code": reason}
        if resolved != previous["resolved_references"] or handler != previous["admitted_handler"]:
            return {"decision": "REQUIRES_READMISSION", "reason_code": "RESOLUTION_CHANGED"}
        return {
            "decision": "ACCEPTED",
            "reason_code": "REVALIDATED",
            "admission_id": previous["admission_id"],
            "admitted_handler": handler,
            "resolved_references": resolved,
        }


__all__ = ["AdmissionStore", "KNOWN_HANDLERS", "POLICY_SCHEMA", "REQUIRED_PROTECTED", "load_policy"]
