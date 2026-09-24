"""Recoverable Brasileirão-owned execution of admitted research requests (no envelope).

Every admitted request becomes one logical experiment. The domain effect is produced by the
compiled worker running as a real predictor_ops job through the SAME mechanism as the shadow
routine (brasileirao_scripts/sombra_diaria.py): a jobs file (schema_version "3") validated by
the Ops and ``sys.executable -m predictor_ops run --job <id> --config <file>`` in a child
process. Lock, heartbeat, timeout, attempt record, economic idempotency and terminal events
are produced by predictor_ops; the executor only reads them back. The scientific state is
read back from the predictor_core trial registry. The authoritative result is persisted in
the ResultStore and re-read after restart, never recomputed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from predictor_core.contracts.trial_v2 import TrialRegistryV2

from brasileirao_predictor.research_runtime.contract import (
    RESULT_SCHEMA,
    canonical,
    content_hash,
    digest,
    utc,
    validate_result,
)
from brasileirao_predictor.research_runtime.durable import Busy, atomic_write, exclusive, read_json_object, sha256_file
from brasileirao_predictor.research_runtime.faults import FAULT_ENV, fault, worker_flag

HANDLER = "brasileirao.handlers.walkforward_forecast_evaluation.v1"
WORKER_MODULE = "brasileirao_predictor.research_runtime.worker"
OPS_CONFIG_VERSION = "brasileirao-research-ops/1"
# Short on-disk layout: the deepest predictor_ops file under OPS_DIR is
# idempotency/.economic-<sha256>.json.<uuid>.tmp (~129 chars); a Windows state root must stay
# within MAX_STATE_ROOT_CHARS to keep every path under MAX_PATH (260).
EXEC_DIR = "x"
EXPERIMENTS_DIR = "e"
OPS_DIR = "o"
MAX_STATE_ROOT_CHARS = 120
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
STATES = (
    "PLANNED",
    "MATERIALIZED",
    "SCHEDULED",
    "RUNNING",
    "DOMAIN_EFFECT_COMMITTED",
    "MEASURED",
    "RESULT_CREATED",
    "RESULT_STORED",
    "COMPLETED",
    "FAILED_ATTEMPT",
    "REFUSED",
    "RECONCILIATION_REQUIRED",
)
_HASH = re.compile(r"[0-9a-f]{64}")
SQLITE_MAGIC = b"SQLite format 3\x00"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _dist_identity(name: str) -> dict:
    """Installed distribution identity: version and sha256 of its RECORD."""
    from importlib.metadata import PackageNotFoundError, distribution

    try:
        dist = distribution(name)
    except PackageNotFoundError:
        return {"package": name, "version": None, "record_sha256": None}
    record = next((item for item in (dist.files or []) if item.name == "RECORD"), None)
    record_sha = sha256_file(Path(str(dist.locate_file(record)))) if record is not None else None
    return {"package": name, "version": dist.version, "record_sha256": record_sha}


class ExecutionError(RuntimeError):
    """Raised with an outcome status the entrypoint maps to an exit code."""

    def __init__(self, status: str, reason: str, detail: dict | None = None):
        super().__init__(f"{status}: {reason}")
        self.status = status
        self.reason = reason
        self.detail = detail or {}


class ReferenceStore:
    """Operator-owned immutable objects; requests only select registry hashes.

    JSON references (model, features, baseline, cost_model, odds, dataset manifest) and SQLite
    dataset snapshots are content-addressed files, made read-only on write.
    """

    def __init__(self, root: str | Path, *, max_json_bytes: int = 4 * 1024 * 1024, max_blob_bytes: int = 1 << 30):
        self.root = Path(root).resolve()
        self.max_json_bytes = max_json_bytes
        self.max_blob_bytes = max_blob_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def object_path(self, object_hash: str) -> Path:
        if not _HASH.fullmatch(object_hash):
            raise ValueError("invalid content hash")
        return self.root / object_hash[:2] / object_hash

    def _store(self, raw_path: Path, object_hash: str) -> str:
        target = self.object_path(object_hash)
        if target.exists():
            if sha256_file(target) != object_hash:
                raise ValueError("operator object corruption")
            return object_hash
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(raw_path, target)
        target.chmod(stat.S_IREAD)
        return object_hash

    def put_operator_bytes(self, raw: bytes) -> str:
        """Administrative provisioning of a JSON reference; never called with request data."""
        if not raw or len(raw) > self.max_json_bytes:
            raise ValueError("operator object size denied")
        read_json_object_bytes(raw)
        object_hash = hashlib.sha256(raw).hexdigest()
        target = self.object_path(object_hash)
        if target.exists():
            if sha256_file(target) != object_hash:
                raise ValueError("operator object corruption")
            return object_hash
        atomic_write(target, raw)
        target.chmod(stat.S_IREAD)
        return object_hash

    def put_dataset(self, source: Path, *, as_of: str, label: str) -> dict:
        """Snapshot a SQLite database with sqlite3.backup (source opened read-only) and register
        the blob plus a JSON manifest. Returns {manifest_hash, sqlite_sha256, manifest}."""
        as_of_dt = utc(as_of, "as_of")
        captured = datetime.now(UTC)
        if as_of_dt > captured:
            raise ValueError("as_of cannot be after the capture instant")
        source = Path(source).resolve(strict=True)
        with tempfile.TemporaryDirectory(dir=self.root, prefix=".capture-") as tmp:
            staging = Path(tmp) / "snapshot.sqlite3"
            src = sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)
            dst = sqlite3.connect(staging)
            try:
                src.backup(dst)
                if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("snapshot integrity_check failed")
                tables = {
                    name: dst.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                    for (name,) in dst.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                }
            finally:
                dst.close()
                src.close()
            if staging.stat().st_size > self.max_blob_bytes:
                raise ValueError("dataset snapshot too large")
            blob_hash = self._store(staging, sha256_file(staging))
        manifest = {
            "schema": "brasileirao-dataset/1",
            "sqlite_sha256": blob_hash,
            "as_of": as_of,
            "captured_at": captured.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "label": label,
            "method": "sqlite3.backup from a read-only source connection; PRAGMA integrity_check ok",
            "tables": tables,
        }
        manifest_hash = self.put_operator_bytes(canonical(manifest))
        return {"manifest_hash": manifest_hash, "sqlite_sha256": blob_hash, "manifest": manifest}

    def _verified_source(self, object_hash: str, kind: str) -> Path:
        source = self.object_path(object_hash)
        if not source.exists() or source.is_symlink() or getattr(source, "is_junction", lambda: False)():
            raise FileNotFoundError(f"admitted reference object unavailable: {kind}")
        resolved = source.resolve(strict=True)
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise PermissionError("reference object escapes operator store")
        if sha256_file(resolved) != object_hash:
            raise ValueError(f"reference hash verification failed: {kind}")
        return resolved

    def _copy_verified(self, source: Path, target: Path, expected: str, kind: str) -> str:
        if target.exists() and sha256_file(target) != expected:
            raise ValueError(f"materialized reference changed after materialization: {kind}")
        if not target.exists():
            shutil.copyfile(source, target)
            target.chmod(stat.S_IREAD)
            fault("during_materialization")
        observed = sha256_file(target)
        if observed != expected:
            raise ValueError(f"materialized reference changed: {kind}")
        return observed

    def materialize(self, references: list[dict], destination: str | Path) -> list[dict]:
        destination = Path(destination).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        materialized = []
        kinds = set()
        for reference in references:
            if set(reference) != {"kind", "name", "version", "revision_id", "content_hash"}:
                raise ValueError("resolved reference shape changed")
            kind, expected = reference["kind"], reference["content_hash"]
            if kind in kinds or not re.fullmatch(r"[a-z_]{1,32}", kind):
                raise ValueError("reference kinds must be unique and bounded")
            kinds.add(kind)
            source = self._verified_source(expected, kind)
            target = destination / f"{kind}.json"
            observed = self._copy_verified(source, target, expected, kind)
            entry = {
                **reference,
                "expected_hash": expected,
                "observed_hash": observed,
                "resolver_id": "brasileirao-operator-cas",
                "resolver_version": "1",
                "path": str(target),
                "size": target.stat().st_size,
                "verification": "PASS",
            }
            if kind == "dataset":
                manifest = read_json_object(target)
                blob = manifest.get("sqlite_sha256")
                if manifest.get("schema") != "brasileirao-dataset/1" or not isinstance(blob, str):
                    raise ValueError("dataset manifest schema")
                blob_source = self._verified_source(blob, "dataset snapshot")
                with blob_source.open("rb") as handle:
                    if handle.read(len(SQLITE_MAGIC)) != SQLITE_MAGIC:
                        raise ValueError("dataset snapshot is not a SQLite database")
                snapshot = destination / "dataset.sqlite3"
                self._copy_verified(blob_source, snapshot, blob, "dataset snapshot")
                entry["snapshot"] = {"path": str(snapshot), "sqlite_sha256": blob, "as_of": manifest["as_of"]}
            materialized.append(entry)
        return materialized


def read_json_object_bytes(raw: bytes) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "o.json"
        path.write_bytes(raw)
        return read_json_object(path)


class ExperimentJournal:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS experiments(
                  experiment_id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                  logical_hash TEXT NOT NULL, state TEXT NOT NULL,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                  effect_hash TEXT, result_hash TEXT, ops_run_id TEXT, error TEXT
                );
                CREATE TABLE IF NOT EXISTS transitions(
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT, experiment_id TEXT NOT NULL,
                  state TEXT NOT NULL, recorded_at TEXT NOT NULL, detail TEXT
                );
                CREATE TABLE IF NOT EXISTS attempts(
                  attempt_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, number INTEGER NOT NULL,
                  ops_run_id TEXT, ops_status TEXT, ops_exit_code INTEGER, state TEXT NOT NULL,
                  started_at TEXT NOT NULL, finished_at TEXT, ops_record_hash TEXT, error TEXT
                );
                CREATE INDEX IF NOT EXISTS attempts_experiment ON attempts(experiment_id,number);
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

    def ensure(self, experiment_id: str, request_id: str, logical_hash: str) -> dict:
        now = _now()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM experiments WHERE request_id=?", (request_id,)).fetchone()
            if row:
                if row["experiment_id"] != experiment_id or row["logical_hash"] != logical_hash:
                    raise ExecutionError("RECONCILIATION_REQUIRED", "EXPERIMENT_IDENTITY_CONFLICT")
                return dict(row)
            db.execute(
                "INSERT INTO experiments(experiment_id,request_id,logical_hash,state,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?)",
                (experiment_id, request_id, logical_hash, "PLANNED", now, now),
            )
            db.execute(
                "INSERT INTO transitions(experiment_id,state,recorded_at,detail) VALUES(?,?,?,?)",
                (experiment_id, "PLANNED", now, "admitted logical identity"),
            )
        return self.get(experiment_id)

    def transition(self, experiment_id: str, state: str, *, detail: str = "", **fields: Any) -> dict:
        if state not in STATES or set(fields) - {"effect_hash", "result_hash", "ops_run_id", "error"}:
            raise ValueError("invalid journal transition")
        now = _now()
        assignments = ["state=?", "updated_at=?"] + [f"{key}=?" for key in fields]
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone() is None:
                raise ValueError("unknown experiment")
            db.execute(
                f"UPDATE experiments SET {','.join(assignments)} WHERE experiment_id=?",
                [state, now, *fields.values(), experiment_id],
            )
            db.execute(
                "INSERT INTO transitions(experiment_id,state,recorded_at,detail) VALUES(?,?,?,?)",
                (experiment_id, state, now, detail[:1000]),
            )
        return self.get(experiment_id)

    def get(self, experiment_id: str) -> dict:
        with self.connection() as db:
            row = db.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
        if row is None:
            raise ValueError("unknown experiment")
        return dict(row)

    def first_transition_at(self, experiment_id: str, state: str) -> str | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT recorded_at FROM transitions WHERE experiment_id=? AND state=? ORDER BY sequence LIMIT 1",
                (experiment_id, state),
            ).fetchone()
        return row["recorded_at"] if row else None

    def start_attempt(self, experiment_id: str) -> tuple[str, int]:
        attempt_id = "brasileirao:ATTEMPT-" + uuid4().hex
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            number = (
                db.execute("SELECT count(*) FROM attempts WHERE experiment_id=?", (experiment_id,)).fetchone()[0] + 1
            )
            db.execute(
                "INSERT INTO attempts(attempt_id,experiment_id,number,state,started_at) VALUES(?,?,?,?,?)",
                (attempt_id, experiment_id, number, "RUNNING", _now()),
            )
        return attempt_id, number

    def finish_attempt(self, attempt_id: str, *, state: str, run: dict | None = None, error: str | None = None) -> None:
        if state not in {"SUCCEEDED", "FAILED", "SKIPPED_ALREADY_SUCCEEDED", "REFUSED"}:
            raise ValueError("invalid attempt state")
        with self.connection() as db:
            db.execute(
                "UPDATE attempts SET state=?,ops_run_id=?,ops_status=?,ops_exit_code=?,finished_at=?,"
                "ops_record_hash=?,error=? WHERE attempt_id=?",
                (
                    state,
                    (run or {}).get("run_id"),
                    (run or {}).get("run_status"),
                    (run or {}).get("exit_code"),
                    _now(),
                    content_hash(run) if run is not None else None,
                    (error or "")[:2000] or None,
                    attempt_id,
                ),
            )

    def attempts(self, experiment_id: str) -> list[dict]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM attempts WHERE experiment_id=? ORDER BY number", (experiment_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def close_interrupted_attempts(self, experiment_id: str) -> int:
        """Attempts left RUNNING by a crashed process are closed as FAILED (never counted as success)."""
        with self.connection() as db:
            cursor = db.execute(
                "UPDATE attempts SET state='FAILED',finished_at=?,error='INTERRUPTED: process ended during attempt' "
                "WHERE experiment_id=? AND state='RUNNING'",
                (_now(), experiment_id),
            )
        return cursor.rowcount


def experiment_dir(execution_root: Path, logical_hash: str) -> Path:
    return Path(execution_root) / EXPERIMENTS_DIR / logical_hash[:16]


def ops_records(ops_root: Path, job_id: str) -> list[dict]:
    """Records written by predictor_ops (events.jsonl), oldest first."""
    events = ops_root / job_id / "events.jsonl"
    if not events.exists():
        return []
    records = []
    for line in events.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if isinstance(record, dict):
                records.append(record)
    return records


def job_id_for(logical_hash: str) -> str:
    return "brasileirao-research-" + logical_hash[:24]


class ResearchExecutor:
    def __init__(
        self,
        root: str | Path,
        *,
        admission_store: Any,
        result_store: Any,
        reference_store: ReferenceStore,
        python_executable: str | None = None,
    ):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.admission_store = admission_store
        self.result_store = result_store
        self.references = reference_store
        self.python = python_executable or sys.executable
        self.journal = ExperimentJournal(self.root / "journal.sqlite")
        self.ops_root = self.root / OPS_DIR
        self.identities = {
            "core": _dist_identity("predictor-core"),
            "ops": _dist_identity("predictor-ops"),
            "brasileirao": _dist_identity("brasileirao-predictor"),
        }

    @staticmethod
    def logical_identity(context: dict) -> tuple[str, str]:
        receipt, request = context["receipt"], context["request"]
        logical_hash = content_hash(
            {
                "request_id": request["request_id"],
                "request_content_hash": context["request_content_hash"],
                "admission_id": receipt["admission_id"],
                "handler": receipt["admitted_handler"],
                "references": receipt["resolved_references"],
            }
        )
        return "brasileirao:EXP-" + logical_hash[:32], logical_hash

    def _work(self, logical_hash: str) -> Path:
        return experiment_dir(self.root, logical_hash)

    def _job_config(
        self, context, experiment_id, logical_hash, work, request_path, effect_path, trial_path, number
    ) -> dict:
        request = context["request"]
        budget = context["receipt"]["resource_budget"]
        command = [
            self.python,
            "-m",
            WORKER_MODULE,
            "--request",
            str(request_path),
            "--effect",
            str(effect_path),
            "--trial-registry",
            str(trial_path),
            *worker_flag(),
        ]
        return {
            "id": job_id_for(logical_hash),
            "command": command,
            "cwd": str(work),
            "environment": {FAULT_ENV: ""},
            "timeout_seconds": budget["timeout_seconds"],
            "heartbeat_interval_seconds": 1,
            "max_output_bytes": 1048576,
            "expected_artifact": str(effect_path),
            "provenance": {
                "domain": "brasileirao",
                "request_id": request["request_id"],
                "request_content_hash": context["request_content_hash"],
                "admission_id": context["receipt"]["admission_id"],
                "logical_hash": logical_hash,
                "wheel": self.identities["brasileirao"],
            },
            "provenance_mode": "strict",
            "config_version": OPS_CONFIG_VERSION,
            "input_reference": sha256_file(request_path),
            "output_reference": str(effect_path),
            "retry_count": number - 1,
            "scientific_state": "RESEARCH_FORECAST_EVALUATION",
            "job_type": "FORECAST_GENERATION",
            "economic_key": {
                "domain": "brasileirao",
                "event_id": experiment_id,
                "market": request["target"],
                "decision_stage": "research_forecast",
                "logical_time": request["data_cutoff"],
            },
            "capital_permission": False,
            "exit_statuses": {"0": "SUCCEEDED"},
            "runtime": {"backend": "local", "root": str(self.ops_root)},
        }

    def _run_ops(self, job: dict, jobs_path: Path) -> tuple[dict | None, dict]:
        """Run one job through the Ops CLI exactly like the shadow routine; return its terminal record."""
        jobs = {"schema_version": "3", "jobs": [job]}
        atomic_write(jobs_path, json.dumps(jobs, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8"))
        before = len(ops_records(self.ops_root, job["id"]))
        environment = os.environ.copy()
        environment.pop(FAULT_ENV, None)
        completed = subprocess.run(
            [self.python, "-m", "predictor_ops", "run", "--job", job["id"], "--config", str(jobs_path)],
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=_NO_WINDOW,
        )
        cli = {"exit_code": completed.returncode, "stderr_tail": completed.stderr[-2000:]}
        new = ops_records(self.ops_root, job["id"])[before:]
        terminal = [r for r in new if r.get("finished_at")]
        if len(terminal) > 1:
            raise ExecutionError("RECONCILIATION_REQUIRED", "OPS_WROTE_MORE_THAN_ONE_TERMINAL_RECORD")
        return (terminal[0] if terminal else None), cli

    def execute(self, request_id: str) -> dict:
        context = self.admission_store.admitted_context(request_id)
        receipt = context["receipt"]
        if receipt["admitted_handler"] != HANDLER:
            raise ExecutionError("REJECTED", "HANDLER_NOT_COMPILED")
        experiment_id, logical_hash = self.logical_identity(context)
        # One live executor per experiment: a concurrent submission of the same request never
        # interleaves with materialization, the Ops job or the result write (BR-F014).
        try:
            with exclusive(self.root / EXPERIMENTS_DIR / f".{logical_hash[:16]}.lock"):
                return self._execute_locked(request_id, context, experiment_id, logical_hash)
        except Busy as exc:
            raise ExecutionError(
                "OPS_FAILED_RETRYABLE", "EXPERIMENT_BUSY", {"operational_state": "NOT_RUN", "detail": str(exc)}
            ) from exc

    def _execute_locked(self, request_id: str, context: dict, experiment_id: str, logical_hash: str) -> dict:
        receipt, request = context["receipt"], context["request"]
        row = self.journal.ensure(experiment_id, request_id, logical_hash)
        work = self._work(logical_hash)
        effect_path, result_path = work / "domain-effect.json", work / "research-result.json"
        existing = self.result_store.read_by_request(request_id)
        if existing is None and self.journal.first_transition_at(experiment_id, "RESULT_STORED"):
            self.journal.transition(
                experiment_id,
                "RECONCILIATION_REQUIRED",
                error="journal says the result was stored but the store has none",
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "STORED_RESULT_MISSING_FROM_INDEX")
        if existing is not None:
            self._check_integrity(experiment_id, row, effect_path, result_path)
            # Authoritative result already stored: finish any step a crash interrupted.
            self.admission_store.mark_terminal(request_id, existing["result_id"])
            if row["state"] != "COMPLETED":
                self.journal.transition(experiment_id, "COMPLETED", detail="reconciled from stored result")
            return {"status": "DUPLICATE", "result": existing, "experiment_id": experiment_id}
        # No authoritative result yet: the current policy must still admit the request (a stored
        # result is an immutable fact and is returned above whatever the policy says).
        revalidated = self.admission_store.revalidate(request_id)
        if revalidated["decision"] != "ACCEPTED":
            raise ExecutionError("REJECTED", revalidated["reason_code"])
        if row["state"] in {"REFUSED", "RECONCILIATION_REQUIRED"}:
            error = row["error"] or row["state"]
            if error.startswith("TEMPORAL"):
                raise ExecutionError("TEMPORAL_INTEGRITY_VIOLATION", error)
            raise ExecutionError(
                "RECONCILIATION_REQUIRED" if row["state"] == "RECONCILIATION_REQUIRED" else "REJECTED", error
            )
        self.journal.close_interrupted_attempts(experiment_id)
        refs_dir = work / "references"
        trial_path = work / "trials-v2.json"
        refusal_path = work / "worker-refusal.json"

        receipt_path = work / "reference-materialization.json"
        try:
            materialized = self.references.materialize(receipt["resolved_references"], refs_dir)
        except FileNotFoundError as exc:
            raise ExecutionError("NOT_READY", str(exc)) from exc
        except (ValueError, PermissionError) as exc:
            self.journal.transition(experiment_id, "RECONCILIATION_REQUIRED", error=f"REFERENCE: {exc}")
            raise ExecutionError("RECONCILIATION_REQUIRED", f"REFERENCE: {exc}") from exc
        materialization = {
            "schema": "brasileirao-reference-materialization/1",
            "request_id": request_id,
            "experiment_id": experiment_id,
            "references": materialized,
        }
        if receipt_path.exists():
            recorded = read_json_object(receipt_path)
            if (recorded.get("request_id"), recorded.get("experiment_id")) != (request_id, experiment_id):
                self.journal.transition(
                    experiment_id,
                    "RECONCILIATION_REQUIRED",
                    error="REFERENCE: materialization belongs to another request",
                )
                raise ExecutionError("RECONCILIATION_REQUIRED", "REFERENCE_FROM_ANOTHER_REQUEST")
            if recorded != materialization:
                self.journal.transition(
                    experiment_id, "RECONCILIATION_REQUIRED", error="REFERENCE: materialization receipt conflict"
                )
                raise ExecutionError("RECONCILIATION_REQUIRED", "MATERIALIZATION_RECEIPT_CONFLICT")
        else:
            atomic_write(receipt_path, canonical(materialization))
        materialization_hash = sha256_file(receipt_path)
        if row["state"] == "PLANNED":
            self.journal.transition(experiment_id, "MATERIALIZED", detail="all admitted hashes verified")

        dataset = next(item for item in materialized if item["kind"] == "dataset")
        worker_request = {
            "schema": "brasileirao-admitted-research/1",
            "handler": HANDLER,
            "experiment_id": experiment_id,
            "trial_id": "brasileirao:TRIAL-" + logical_hash[:32],
            "request": {key: value for key, value in request.items() if key != "client_ref"},
            "references": {item["kind"]: item["path"] for item in materialized},
            "identities": {item["kind"]: item["content_hash"] for item in materialized},
            "identities_named": {item["kind"]: f"{item['name']}@{item['version']}" for item in materialized},
            "dataset": {"path": dataset["snapshot"]["path"], "sqlite_sha256": dataset["snapshot"]["sqlite_sha256"]},
            "registered_at": self.journal.get(experiment_id)["created_at"][:19] + "Z",
            "code_version": "brasileirao-predictor=={version}+record.{record}".format(
                version=self.identities["brasileirao"]["version"],
                record=(self.identities["brasileirao"]["record_sha256"] or "none")[:16],
            ),
        }
        request_path = work / "worker-request.json"
        raw_request = canonical(worker_request)
        if request_path.exists() and request_path.read_bytes() != raw_request:
            self.journal.transition(experiment_id, "RECONCILIATION_REQUIRED", error="worker request conflict")
            raise ExecutionError("RECONCILIATION_REQUIRED", "WORKER_REQUEST_CONFLICT")
        if not request_path.exists():
            atomic_write(request_path, raw_request)

        self._check_integrity(experiment_id, self.journal.get(experiment_id), effect_path, result_path)
        fault("before_ops")

        if not effect_path.exists():
            attempts = self.journal.attempts(experiment_id)
            failed = sum(1 for item in attempts if item["state"] == "FAILED")
            if failed > receipt["resource_budget"]["max_retries"]:
                return self._terminal_failure(context, experiment_id, logical_hash, attempts, materialization_hash)
            attempt_id, number = self.journal.start_attempt(experiment_id)
            job = self._job_config(
                context, experiment_id, logical_hash, work, request_path, effect_path, trial_path, number
            )
            self.journal.transition(experiment_id, "SCHEDULED", detail="compiled worker selected by handler identity")
            self.journal.transition(
                experiment_id, "RUNNING", detail=f"delegated to predictor_ops (CLI) attempt {number}"
            )
            try:
                run, cli = self._run_ops(job, work / f"ops-job.{number}.json")
            except ExecutionError:
                self.journal.finish_attempt(attempt_id, state="FAILED", error="OPS_WROTE_MORE_THAN_ONE_TERMINAL_RECORD")
                raise
            fault("after_ops")
            status = (run or {}).get("run_status")
            if run is None:
                self.journal.finish_attempt(
                    attempt_id, state="FAILED", error=f"OPS_CLI_NO_TERMINAL_RECORD {json.dumps(cli)}"
                )
                self.journal.transition(experiment_id, "FAILED_ATTEMPT", error=f"OPS_CLI_EXIT_{cli['exit_code']}")
                raise ExecutionError(
                    "OPS_FAILED_RETRYABLE",
                    f"OPS_CLI_EXIT_{cli['exit_code']}",
                    {"operational_state": "FAILED", "attempt_id": attempt_id},
                )
            if status == "SKIPPED" and run.get("reason") == "economic_operation_already_claimed":
                # Ops already holds a SUCCEEDED run for this experiment: reconcile, never re-run.
                self.journal.finish_attempt(attempt_id, state="SKIPPED_ALREADY_SUCCEEDED", run=run)
                if not effect_path.exists():
                    self.journal.transition(
                        experiment_id,
                        "RECONCILIATION_REQUIRED",
                        error="Ops reports SUCCEEDED but effect bytes are missing",
                    )
                    raise ExecutionError("RECONCILIATION_REQUIRED", "EFFECT_MISSING_AFTER_OPS_SUCCESS")
            elif status == "SKIPPED":
                self.journal.finish_attempt(attempt_id, state="FAILED", run=run, error=str(run.get("reason")))
                self.journal.transition(experiment_id, "FAILED_ATTEMPT", error=f"OPS_SKIPPED {run.get('reason')}")
                raise ExecutionError(
                    "OPS_FAILED_RETRYABLE",
                    f"OPS_SKIPPED {run.get('reason')}",
                    {"operational_state": "FAILED", "ops_run_id": run.get("run_id")},
                )
            elif status != "SUCCEEDED":
                timed_out = (run.get("termination") or {}).get("reason") == "timeout"
                if refusal_path.exists():
                    refusal = read_json_object(refusal_path)
                    self.journal.finish_attempt(attempt_id, state="REFUSED", run=run, error=refusal.get("reason"))
                    if refusal.get("exit_code") == 6:
                        refusal_path.replace(refusal_path.with_name(f"worker-refusal.{attempt_id.split('-')[-1]}.json"))
                        self.journal.transition(
                            experiment_id, "RECONCILIATION_REQUIRED", error=f"REFERENCE: {refusal.get('reason')}"
                        )
                        raise ExecutionError(
                            "RECONCILIATION_REQUIRED",
                            f"REFERENCE: {refusal.get('reason')}",
                            {"operational_state": status, "ops_run_id": run.get("run_id")},
                        )
                    temporal = refusal.get("exit_code") == 4
                    error = ("TEMPORAL: " if temporal else "REFUSED: ") + str(refusal.get("reason"))
                    self.journal.transition(experiment_id, "REFUSED", error=error)
                    self.admission_store.mark_terminal(request_id, "brasileirao:REFUSED-" + logical_hash[:32])
                    raise ExecutionError(
                        "TEMPORAL_INTEGRITY_VIOLATION" if temporal else "REJECTED",
                        error,
                        {"operational_state": status, "ops_run_id": run.get("run_id")},
                    )
                self.journal.finish_attempt(
                    attempt_id,
                    state="FAILED",
                    run=run,
                    error=json.dumps(
                        {
                            "run_status": status,
                            "exit_code": run.get("exit_code"),
                            "termination": run.get("termination"),
                        },
                        sort_keys=True,
                    ),
                )
                self.journal.transition(
                    experiment_id, "FAILED_ATTEMPT", error=f"OPS_{'TIMEOUT' if timed_out else status}"
                )
                raise ExecutionError(
                    "OPS_FAILED_RETRYABLE",
                    f"OPS_{'TIMEOUT' if timed_out else status}",
                    {
                        "operational_state": "TIMEOUT" if timed_out else "FAILED",
                        "ops_run_id": run.get("run_id"),
                        "exit_code": run.get("exit_code"),
                        "attempt_id": attempt_id,
                    },
                )
            else:
                self.journal.finish_attempt(attempt_id, state="SUCCEEDED", run=run)
            fault("after_domain_effect")

        effect_hash = sha256_file(effect_path)
        recorded = self.journal.get(experiment_id)
        if recorded["effect_hash"] and recorded["effect_hash"] != effect_hash:
            self.journal.transition(experiment_id, "RECONCILIATION_REQUIRED", error="effect hash mismatch")
            raise ExecutionError("RECONCILIATION_REQUIRED", "EFFECT_HASH_MISMATCH")
        ops_record = self._ops_success_record(logical_hash)
        self.journal.transition(
            experiment_id,
            "DOMAIN_EFFECT_COMMITTED",
            detail="immutable effect verified",
            effect_hash=effect_hash,
            ops_run_id=ops_record["run_id"],
        )
        effect = read_json_object(effect_path)
        if effect.get("experiment_id") != experiment_id:
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error="effect belongs to another experiment"
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "EFFECT_EXPERIMENT_MISMATCH")
        core_trial = self._core_trial(effect, trial_path, experiment_id)
        self.journal.transition(experiment_id, "MEASURED", detail="domain output and Core trial loaded")

        # The result is a deterministic function of committed inputs; its hash is journaled
        # BEFORE the bytes are written (intent), so a crash either finds matching bytes,
        # regenerates the same bytes, or fails closed.
        attempts = self.journal.attempts(experiment_id)
        produced_at = self.journal.first_transition_at(experiment_id, "DOMAIN_EFFECT_COMMITTED")
        result = self._result(
            context,
            experiment_id,
            logical_hash,
            effect,
            effect_hash,
            core_trial,
            ops_record,
            attempts,
            materialization_hash,
            produced_at or _now(),
        )
        raw = canonical(result)
        result_hash = digest(raw)
        recorded = self.journal.get(experiment_id)
        if recorded["result_hash"] is None:
            self.journal.transition(
                experiment_id,
                "RESULT_CREATED",
                detail="brasileirao-research-result/1 validated",
                result_hash=result_hash,
            )
        elif recorded["result_hash"] != result_hash:
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error="regenerated result differs from journal"
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "RESULT_NOT_REPRODUCIBLE")
        if result_path.exists():
            if sha256_file(result_path) != result_hash:
                self.journal.transition(experiment_id, "RECONCILIATION_REQUIRED", error="result file hash mismatch")
                raise ExecutionError("RECONCILIATION_REQUIRED", "RESULT_HASH_MISMATCH")
        else:
            if os.environ.get(FAULT_ENV) == "during_result_write":
                partial = result_path.with_name(f".{result_path.name}.{uuid4().hex}.tmp")
                partial.write_bytes(raw[: len(raw) // 2])
                fault("during_result_write")
            atomic_write(result_path, raw)
        fault("after_result_write")
        stored = self.result_store.store(result, result_path)
        fault("after_result_store")
        self.journal.transition(experiment_id, "RESULT_STORED", detail=stored["status"])
        self.admission_store.mark_terminal(request_id, result["result_id"])
        self.journal.transition(experiment_id, "COMPLETED", detail="logical execution completed")
        return {
            "status": "RESULT" if stored["status"] == "stored" else "DUPLICATE",
            "result": self.result_store.read_by_request(request_id),
            "experiment_id": experiment_id,
        }

    def _check_integrity(self, experiment_id: str, recorded: dict, effect_path: Path, result_path: Path) -> None:
        if recorded["effect_hash"] and not effect_path.exists():
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error="effect metadata exists without bytes"
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "EFFECT_BYTES_MISSING")
        if recorded["effect_hash"] and effect_path.exists() and sha256_file(effect_path) != recorded["effect_hash"]:
            self.journal.transition(experiment_id, "RECONCILIATION_REQUIRED", error="effect hash mismatch")
            raise ExecutionError("RECONCILIATION_REQUIRED", "EFFECT_HASH_MISMATCH")
        if recorded["result_hash"] and result_path.exists() and sha256_file(result_path) != recorded["result_hash"]:
            self.journal.transition(experiment_id, "RECONCILIATION_REQUIRED", error="result hash mismatch")
            raise ExecutionError("RECONCILIATION_REQUIRED", "RESULT_HASH_MISMATCH")

    def _ops_success_record(self, logical_hash: str) -> dict:
        records = [
            r for r in ops_records(self.ops_root, job_id_for(logical_hash)) if r.get("run_status") == "SUCCEEDED"
        ]
        if not records:
            raise ExecutionError("RECONCILIATION_REQUIRED", "OPS_SUCCESS_RECEIPT_MISSING")
        if len(records) > 1:
            raise ExecutionError("RECONCILIATION_REQUIRED", "OPS_REPORTS_MORE_THAN_ONE_SUCCESS")
        return records[0]

    def _core_trial(self, effect: dict, trial_path: Path, experiment_id: str) -> dict:
        rows = [row for row in TrialRegistryV2(trial_path).load() if row["trial_id"] == effect["trial"]["trial_id"]]
        if len(rows) != 1 or rows[0] != effect["trial"] or rows[0]["experiment_id"] != experiment_id:
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error="Core trial registry disagrees with effect"
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "CORE_TRIAL_MISMATCH")
        return rows[0]

    def _result(
        self,
        context,
        experiment_id,
        logical_hash,
        effect,
        effect_hash,
        core_trial,
        ops_record,
        attempts,
        materialization_hash,
        produced_at,
    ) -> dict:
        request, receipt = context["request"], context["receipt"]
        scientific = core_trial["status"]
        if scientific != effect["scientific_state"]:
            raise ExecutionError("RECONCILIATION_REQUIRED", "CORE_STATE_DISAGREES_WITH_EFFECT")
        attempt_ids = [item["attempt_id"] for item in attempts]
        ops_run_ids = [item["ops_run_id"] for item in attempts if item["ops_run_id"]]
        result = {
            "schema_version": RESULT_SCHEMA,
            "result_id": "brasileirao:RESULT-" + logical_hash[:32],
            "request_id": request["request_id"],
            "admission_id": receipt["admission_id"],
            "experiment_id": experiment_id,
            "research_id": request["research_id"],
            "hypothesis_id": request["hypothesis_id"],
            "result_state": effect["result_state"],
            "operational_state": "SUCCEEDED",
            "scientific_state": scientific,
            "economic_state": effect["economic_state"],
            "capital_permission": False,
            "produced_at": produced_at[:19] + "Z",
            "core_facts": {
                "identity": self.identities["core"],
                "trial_ids": [core_trial["trial_id"]],
                "trial_registry": "predictor_core.contracts.trial_v2.TrialRegistryV2",
                "scientific_state_source": "core_trial_registry",
                "trial_row_hash": content_hash(core_trial),
                "dataset_fingerprint": core_trial["dataset_hash"],
                "temporal_validation": effect["temporal_validation"],
                "statistics": core_trial["result"],
                "metrics_source": "predictor_core.measurement.metrics + bootstrap.bootstrap_ci",
            },
            "ops_facts": {
                "identity": self.identities["ops"],
                "mechanism": "jobs file schema_version 3 + python -m predictor_ops run --job <id> --config <file>",
                "job_id": ops_record["job_id"],
                "job_type": ops_record.get("job_type"),
                "economic_lock_id": ops_record.get("economic_lock_id"),
                "ops_run_id": ops_record["run_id"],
                "ops_run_ids": ops_run_ids,
                "attempt_ids": attempt_ids,
                "attempts": len(attempts),
                "retry_count": ops_record.get("retry_count"),
                "operational_state": ops_record["run_status"],
                "started_at": ops_record["started_at"],
                "finished_at": ops_record["finished_at"],
                "exit_code": ops_record["exit_code"],
                "heartbeat_at": ops_record.get("heartbeat_at"),
                "library_provenance": ops_record.get("library_provenance"),
                "ops_record_hash": content_hash(ops_record),
            },
            "domain_facts": {
                "identity": self.identities["brasileirao"],
                "handler": receipt["admitted_handler"],
                "references": {
                    ref["kind"]: {k: ref[k] for k in ("name", "version", "revision_id", "content_hash")}
                    for ref in receipt["resolved_references"]
                },
                "target": effect["target"],
                "data_cutoff": effect["data_cutoff"],
                "dataset_as_of": effect["dataset_as_of"],
                "data_quality": effect["data_quality"],
                "predictions": effect["predictions"],
                "evaluation": effect["evaluation"],
                "economics": effect["economics"],
                "effect_sha256": effect_hash,
            },
            "provenance": {
                "request_content_hash": context["request_content_hash"],
                "admission_policy_id": receipt["policy_id"],
                "admission_policy_version": receipt["policy_version"],
                "admission_policy_hash": receipt["policy_hash"],
                "resolved_references_hash": content_hash(receipt["resolved_references"]),
                "handler_identity": receipt["admitted_handler"],
                "logical_experiment_hash": logical_hash,
                "reference_materialization_receipt_hash": materialization_hash,
                "journal_identity": content_hash({"experiment_id": experiment_id, "attempt_ids": attempt_ids}),
            },
        }
        return validate_result(result)

    def _terminal_failure(self, context, experiment_id, logical_hash, attempts, materialization_hash) -> dict:
        request, receipt = context["request"], context["receipt"]
        result = {
            "schema_version": RESULT_SCHEMA,
            "result_id": "brasileirao:RESULT-" + logical_hash[:32],
            "request_id": request["request_id"],
            "admission_id": receipt["admission_id"],
            "experiment_id": experiment_id,
            "research_id": request["research_id"],
            "hypothesis_id": request["hypothesis_id"],
            "result_state": "FAILED_OPERATIONAL",
            "operational_state": "FAILED",
            "scientific_state": "NOT_EVALUATED",
            "economic_state": "NOT_EVALUATED",
            "capital_permission": False,
            "produced_at": _now()[:19] + "Z",
            "core_facts": {"identity": self.identities["core"], "trial_ids": []},
            "ops_facts": {
                "identity": self.identities["ops"],
                "ops_run_ids": [item["ops_run_id"] for item in attempts if item["ops_run_id"]],
                "attempt_ids": [item["attempt_id"] for item in attempts],
                "attempts": len(attempts),
                "attempt_errors": [item["error"] for item in attempts],
                "retry_budget": receipt["resource_budget"]["max_retries"],
            },
            "domain_facts": {"identity": self.identities["brasileirao"], "handler": receipt["admitted_handler"]},
            "provenance": {
                "request_content_hash": context["request_content_hash"],
                "admission_policy_hash": receipt["policy_hash"],
                "resolved_references_hash": content_hash(receipt["resolved_references"]),
                "logical_experiment_hash": logical_hash,
                "reference_materialization_receipt_hash": materialization_hash,
            },
        }
        validate_result(result)
        work = self._work(logical_hash)
        result_path = work / "research-result.json"
        if not result_path.exists():
            atomic_write(result_path, canonical(result))
        else:
            result = read_json_object(result_path)
        self.journal.transition(
            experiment_id, "RESULT_CREATED", detail="retry budget exhausted", result_hash=sha256_file(result_path)
        )
        stored = self.result_store.store(result, result_path)
        self.journal.transition(experiment_id, "RESULT_STORED", detail=stored["status"])
        self.admission_store.mark_terminal(request["request_id"], result["result_id"])
        self.journal.transition(experiment_id, "COMPLETED", detail="terminal operational failure")
        return {
            "status": "RESULT",
            "result": self.result_store.read_by_request(request["request_id"]),
            "experiment_id": experiment_id,
        }


def reconcile_execution(root: str | Path, result_store: Any) -> list[dict]:
    """Read-only integrity findings over the journal, experiment files and result store."""
    root = Path(root)
    findings: list[dict] = []
    journal_path = root / "journal.sqlite"
    rows = []
    if journal_path.exists():
        with ExperimentJournal(journal_path).connection() as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM experiments").fetchall()]
    for row in rows:
        work = experiment_dir(root, row["logical_hash"])
        effect, result = work / "domain-effect.json", work / "research-result.json"
        eid = row["experiment_id"]
        if effect.exists() and row["effect_hash"] and sha256_file(effect) != row["effect_hash"]:
            findings.append({"experiment_id": eid, "finding": "EFFECT_HASH_MISMATCH"})
        elif row["effect_hash"] and not effect.exists():
            findings.append({"experiment_id": eid, "finding": "EFFECT_MISSING_BYTES"})
        elif effect.exists() and not row["effect_hash"] and row["state"] != "REFUSED":
            findings.append({"experiment_id": eid, "finding": "ORPHAN_EFFECT_RECOVERABLE"})
        if result.exists() and row["result_hash"] and sha256_file(result) != row["result_hash"]:
            findings.append({"experiment_id": eid, "finding": "RESULT_HASH_MISMATCH"})
        elif row["state"] == "COMPLETED" and not result.exists():
            findings.append({"experiment_id": eid, "finding": "RESULT_MISSING_BYTES"})
        if row["state"] == "COMPLETED":
            with result_store.connection() as db:
                indexed = db.execute("SELECT 1 FROM results WHERE experiment_id=?", (eid,)).fetchone()
            if indexed is None:
                findings.append({"experiment_id": eid, "finding": "RESULT_MISSING_FROM_INDEX"})
        if row["state"] == "RECONCILIATION_REQUIRED":
            findings.append({"experiment_id": eid, "finding": "RECONCILIATION_REQUIRED", "error": row["error"]})
    findings.extend(result_store.reconcile())
    return findings


__all__ = [
    "EXEC_DIR",
    "EXPERIMENTS_DIR",
    "HANDLER",
    "MAX_STATE_ROOT_CHARS",
    "OPS_DIR",
    "WORKER_MODULE",
    "ExecutionError",
    "ExperimentJournal",
    "ReferenceStore",
    "ResearchExecutor",
    "experiment_dir",
    "job_id_for",
    "ops_records",
    "reconcile_execution",
]
