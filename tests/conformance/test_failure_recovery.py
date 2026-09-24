"""Failure injection at the edge, restart recovery and corruption (fail closed).

Faults kill the real `brasileirao-research` process (os._exit, no cleanup) or make the real
worker crash/hang under predictor_ops. After each fault the SAME request is submitted again in
a new process: exactly one domain effect, one Ops success and one result must exist.
Gates: FAILURE_INJECTION, RESTART_RECOVERY, IDEMPOTENCY, OPS_RUNTIME.
"""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import subprocess
import threading
import time
from pathlib import Path

import pytest

from brasileirao_predictor.research_runtime.faults import FAULT_ENV, FAULT_EXIT, FAULT_POINTS, PROCESS_DEATH_POINTS

from . import fixtures
from .harness import SCRIPT, Lab, cli, outcomes, standard_lab


def _ops_successes(lab: Lab) -> int:
    total = 0
    for events in (lab.state / "x" / "o").glob("brasileirao-research-*/events.jsonl"):
        for line in events.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("run_status") == "SUCCEEDED":
                total += 1
    return total


def _results(lab: Lab) -> int:
    with sqlite3.connect(lab.state / "results.sqlite") as db:
        return db.execute("SELECT count(*) FROM results").fetchone()[0]


def _effects(lab: Lab) -> list[Path]:
    return list((lab.state / "x" / "e").rglob("domain-effect.json"))


def _single_experiment(lab: Lab) -> Path:
    created = list((lab.state / "x" / "e").iterdir())
    assert len(created) == 1
    return created[0]


@pytest.fixture
def lab():
    value = standard_lab()
    yield value
    value.cleanup()


@pytest.mark.parametrize("point", PROCESS_DEATH_POINTS)
def test_process_death_at_each_point_recovers_exactly_once(lab: Lab, point: str) -> None:
    request = fixtures.request("brasileirao:REQ-FAULT-001")
    path = lab.request_file(request)
    code, _lines, stderr = lab.process(path, env={FAULT_ENV: point})
    assert code == FAULT_EXIT, stderr[-500:]
    if point == "before_admission_commit":
        with sqlite3.connect(lab.state / "admission.sqlite") as db:
            assert db.execute("SELECT count(*) FROM request_inbox").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM admissions").fetchone()[0] == 0
    code, lines, stderr = lab.process(path)
    assert code == 0 and lines[-1]["status"] in {"RESULT", "DUPLICATE"}, (lines, stderr[-800:])
    assert _ops_successes(lab) == 1 and _results(lab) == 1 and len(_effects(lab)) == 1
    code, shown = lab.show(request["request_id"])
    assert code == 0 and shown["result"]["result_id"] == lines[-1]["result_id"]
    code, lines, _ = lab.process(path)
    assert code == 0 and lines[-1]["status"] == "DUPLICATE"
    assert _ops_successes(lab) == 1 and _results(lab) == 1
    done = cli("--state", str(lab.state), "reconcile")
    assert done.returncode == 0 and json.loads(done.stdout)["findings"] == []


def test_ops_worker_crash_is_not_a_result_and_retry_succeeds(lab: Lab) -> None:
    request = fixtures.request("brasileirao:REQ-CRASH-001")
    path = lab.request_file(request)
    code, lines, _ = lab.process(path, env={FAULT_ENV: "ops_worker_crash"})
    failed = lines[-1]
    assert code == 3 and failed["status"] == "OPS_FAILED_RETRYABLE"
    assert (failed["operational_state"], failed["scientific_state"], failed["economic_state"]) == (
        "FAILED",
        "NOT_EVALUATED",
        "NOT_EVALUATED",
    )
    assert _results(lab) == 0 and lab.show(request["request_id"])[0] == 3
    code, lines, _ = lab.process(path)
    assert code == 0 and lines[-1]["status"] == "RESULT"
    assert _ops_successes(lab) == 1 and _results(lab) == 1


def test_ops_timeout_kills_the_worker_and_is_not_a_result() -> None:
    lab = standard_lab(timeout_seconds=3)
    try:
        request = fixtures.request("brasileirao:REQ-TIMEOUT-001")
        path = lab.request_file(request)
        started = time.monotonic()
        code, lines, _ = lab.process(path, env={FAULT_ENV: "ops_worker_hang"})
        failed = lines[-1]
        assert time.monotonic() - started < 120
        assert code == 3 and failed["status"] == "OPS_FAILED_RETRYABLE"
        assert failed["operational_state"] == "TIMEOUT" and failed["reason"] == "OPS_TIMEOUT"
        assert failed["scientific_state"] == "NOT_EVALUATED" and failed["economic_state"] == "NOT_EVALUATED"
        assert not _effects(lab)
        events = [
            json.loads(x)
            for p in (lab.state / "x" / "o").glob("*/events.jsonl")
            for x in p.read_text(encoding="utf-8").splitlines()
            if x.strip()
        ]
        timed_out = [e for e in events if (e.get("termination") or {}).get("reason") == "timeout"]
        assert timed_out and timed_out[0]["exit_code"] == 124 and timed_out[0]["run_status"] == "FAILED"
        # The operator raises the budget: a new policy hash forces readmission (never a silent rerun).
        lab.write_policy(timeout_seconds=1800)
        code, lines, _ = lab.process(path)
        assert code == 2 and lines[-1]["status"] == "REJECTED" and lines[-1]["reason"] == "POLICY_CHANGED"
        code, lines, _ = lab.process(lab.request_file(fixtures.request("brasileirao:REQ-TIMEOUT-002")))
        assert code == 0 and lines[-1]["status"] == "RESULT"
    finally:
        lab.cleanup()


def test_slow_worker_still_produces_exactly_one_result(lab: Lab) -> None:
    request = fixtures.request("brasileirao:REQ-SLOW-001")
    code, lines, _ = lab.process(lab.request_file(request), env={FAULT_ENV: "ops_worker_slow"})
    assert code == 0 and lines[-1]["status"] == "RESULT"
    assert _ops_successes(lab) == 1 and _results(lab) == 1


def test_retry_budget_exhaustion_is_a_terminal_operational_failure() -> None:
    lab = standard_lab(max_retries=1)
    try:
        request = fixtures.request("brasileirao:REQ-BUDGET-001")
        path = lab.request_file(request)
        for _ in range(2):
            code, lines, _ = lab.process(path, env={FAULT_ENV: "ops_worker_crash"})
            assert code == 3 and lines[-1]["status"] == "OPS_FAILED_RETRYABLE"
        code, lines, _ = lab.process(path)
        outcome = lines[-1]
        assert code == 0 and outcome["result_state"] == "FAILED_OPERATIONAL"
        assert (outcome["operational_state"], outcome["scientific_state"], outcome["economic_state"]) == (
            "FAILED",
            "NOT_EVALUATED",
            "NOT_EVALUATED",
        )
        assert lab.show(request["request_id"])[1]["result"]["result_state"] == "FAILED_OPERATIONAL"
    finally:
        lab.cleanup()


def test_ops_lock_held_by_another_run_is_retryable_never_a_second_effect(lab: Lab) -> None:
    request = fixtures.request("brasileirao:REQ-LOCK-001")
    path = lab.request_file(request)
    assert lab.process(path, env={FAULT_ENV: "before_ops"})[0] == FAULT_EXIT
    assert not list((lab.state / "x" / "o").glob("brasileirao-research-*"))  # Ops not started yet
    from predictor_ops.models import EconomicJobKey, JobConfig
    from predictor_ops.operations import economic_lock_id

    from brasileirao_predictor.research_runtime.admission import AdmissionStore
    from brasileirao_predictor.research_runtime.execution import ResearchExecutor, job_id_for

    context = AdmissionStore(lab.state / "admission.sqlite", lab.policy_path).admitted_context(request["request_id"])
    experiment_id, logical = ResearchExecutor.logical_identity(context)
    key = EconomicJobKey(
        domain="brasileirao",
        event_id=experiment_id,
        market=request["target"],
        decision_stage="research_forecast",
        logical_time=request["data_cutoff"],
    )
    job = JobConfig(id=job_id_for(logical), command=["x"], job_type="FORECAST_GENERATION", economic_key=key)
    lock = lab.state / "x" / "o" / economic_lock_id(job) / "run.lock"  # the Ops locks the economic key
    lock.parent.mkdir(parents=True, exist_ok=True)
    # A live owner (this test process) holds the Ops lock of the job.
    lock.write_text(
        json.dumps({"run_id": "other-run", "pid": os.getpid(), "created_at": time.time()}), encoding="utf-8"
    )
    code, lines, _ = lab.process(path)
    assert code == 3 and lines[-1]["status"] == "OPS_FAILED_RETRYABLE" and "lock_not_acquired" in lines[-1]["reason"]
    assert not _effects(lab)
    lock.unlink()
    code, lines, _ = lab.process(path)
    assert code == 0 and lines[-1]["status"] == "RESULT"
    assert _ops_successes(lab) == 1 and _results(lab) == 1


def test_database_lock_waits_and_then_completes_once(lab: Lab) -> None:
    request = fixtures.request("brasileirao:REQ-DBLOCK-001")
    path = lab.request_file(request)
    lab.state.mkdir(parents=True, exist_ok=True)
    blocker = sqlite3.connect(lab.state / "results.sqlite", timeout=30, isolation_level=None, check_same_thread=False)
    blocker.execute("BEGIN EXCLUSIVE")  # another process holds the result store for 4 s
    released = threading.Timer(4.0, lambda: (blocker.rollback(), blocker.close()))
    released.start()
    try:
        code, lines, stderr = lab.process(path)
    finally:
        released.join()
    assert code == 0 and lines[-1]["status"] == "RESULT", stderr[-800:]
    assert _ops_successes(lab) == 1 and _results(lab) == 1


def test_concurrent_submissions_of_the_same_request_produce_one_effect(lab: Lab) -> None:
    request = fixtures.request("brasileirao:REQ-CONCURRENT-001")
    path = lab.request_file(request)
    args = [
        str(SCRIPT),
        "--state",
        str(lab.state),
        "process",
        "--policy",
        str(lab.policy_path),
        "--objects",
        str(lab.objects),
        str(path),
    ]
    procs = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
    results = [p.communicate(timeout=600) for p in procs]
    statuses = sorted(
        json.loads([x for x in out.splitlines() if x.startswith("{")][-1])["status"] for out, _err in results
    )
    # One wins; the other is DUPLICATE (arrived after) or retryable EXPERIMENT_BUSY, never a reconciliation.
    assert "RESULT" in statuses and set(statuses) <= {"RESULT", "DUPLICATE", "OPS_FAILED_RETRYABLE"}, results
    code, lines, _ = lab.process(path)
    assert code == 0 and lines[-1]["status"] in {"RESULT", "DUPLICATE"}
    assert _ops_successes(lab) == 1 and _results(lab) == 1 and len(_effects(lab)) == 1


def test_out_of_order_requests_are_independent_and_deterministic(lab: Lab) -> None:
    late = fixtures.request("brasileirao:REQ-ORDER-LATE", kickoff_from="2023-08-01T00:00:00Z")
    early = fixtures.request("brasileirao:REQ-ORDER-EARLY", kickoff_to="2023-08-01T00:00:00Z")
    code, lines, _ = lab.process(lab.request_file(late), lab.request_file(early))
    assert code == 0 and [x["status"] for x in lines] == ["RESULT", "RESULT"]
    other = standard_lab()
    try:
        code, lines2, _ = other.process(other.request_file(early), other.request_file(late))
        assert code == 0
        a = {x["request_id"]: other.show(x["request_id"])[1]["result"]["domain_facts"]["predictions"] for x in lines2}
        b = {x["request_id"]: lab.show(x["request_id"])[1]["result"]["domain_facts"]["predictions"] for x in lines}
        assert a == b
    finally:
        other.cleanup()


def _completed(request_id: str) -> tuple[Lab, Path, Path]:
    lab = standard_lab()
    path = lab.request_file(fixtures.request(request_id))
    assert lab.process(path)[0] == 0
    return lab, path, _single_experiment(lab)


def _writable(path: Path) -> None:
    path.chmod(stat.S_IWRITE | stat.S_IREAD)


def test_db_says_result_exists_but_file_is_gone() -> None:
    lab, path, work = _completed("brasileirao:REQ-CORRUPT-001")
    try:
        (work / "research-result.json").unlink()
        assert lab.show("brasileirao:REQ-CORRUPT-001")[0] == 5
        code, lines, _ = lab.process(path)
        assert code == 5 and lines[-1]["status"] == "RECONCILIATION_REQUIRED"
        assert not (work / "research-result.json").exists()  # no silent repair
        assert cli("--state", str(lab.state), "reconcile").returncode == 5
    finally:
        lab.cleanup()


def test_file_exists_but_index_lost_the_result() -> None:
    lab, path, _work = _completed("brasileirao:REQ-CORRUPT-002")
    try:
        with sqlite3.connect(lab.state / "results.sqlite") as db:
            db.execute("DELETE FROM results")
        code, lines, _ = lab.process(path)
        assert code == 5 and lines[-1]["status"] == "RECONCILIATION_REQUIRED"
        assert _results(lab) == 0  # no silent re-index
        assert cli("--state", str(lab.state), "reconcile").returncode == 5
    finally:
        lab.cleanup()


def test_modified_result_and_modified_effect_fail_closed() -> None:
    lab, path, work = _completed("brasileirao:REQ-CORRUPT-003")
    try:
        result = work / "research-result.json"
        result.write_bytes(
            result.read_bytes().replace(b'"capital_permission":false', b'"capital_permission":false ', 1)
        )
        assert lab.show("brasileirao:REQ-CORRUPT-003")[0] == 5
    finally:
        lab.cleanup()
    lab, path, work = _completed("brasileirao:REQ-CORRUPT-004")
    try:
        effect = work / "domain-effect.json"
        effect.write_bytes(effect.read_bytes() + b" ")
        code, lines, _ = lab.process(path)
        assert code == 5 and lines[-1]["reason"] == "EFFECT_HASH_MISMATCH"
        done = cli("--state", str(lab.state), "reconcile")
        assert done.returncode == 5 and any(
            f["finding"] == "EFFECT_HASH_MISMATCH" for f in json.loads(done.stdout)["findings"]
        )
    finally:
        lab.cleanup()


def test_corrupted_dataset_snapshot_in_the_object_store_fails_before_ops(lab: Lab) -> None:
    blob = lab.datasets["synthetic"]["sqlite_sha256"]
    target = lab.objects / blob[:2] / blob
    _writable(target)
    data = bytearray(target.read_bytes())
    data[-100] ^= 0xFF
    target.write_bytes(bytes(data))
    code, lines, _ = lab.process(lab.request_file(fixtures.request("brasileirao:REQ-HASH-001")))
    assert code == 5 and "REFERENCE" in lines[-1]["reason"]
    assert not (lab.state / "x" / "o").exists()


def test_missing_reference_object_is_not_ready(lab: Lab) -> None:
    model = next(e for e in lab.registry if e["kind"] == "model")
    target = lab.objects / model["content_hash"][:2] / model["content_hash"]
    _writable(target)
    target.unlink()
    code, lines, _ = lab.process(lab.request_file(fixtures.request("brasileirao:REQ-MISSING-001")))
    assert code == 3 and lines[-1]["status"] == "NOT_READY"


def test_reference_changed_after_materialization_fails_closed(lab: Lab) -> None:
    request = fixtures.request("brasileirao:REQ-MAT-001")
    path = lab.request_file(request)
    assert lab.process(path, env={FAULT_ENV: "before_ops"})[0] == FAULT_EXIT
    snapshot = _single_experiment(lab) / "references" / "dataset.sqlite3"
    _writable(snapshot)
    data = bytearray(snapshot.read_bytes())
    data[-100] ^= 0xFF
    snapshot.write_bytes(bytes(data))
    code, lines, _ = lab.process(path)
    assert code == 5 and "changed after materialization" in lines[-1]["reason"]
    assert _results(lab) == 0


def test_backup_and_restore_into_a_new_root_reread_the_same_result(lab: Lab) -> None:
    request = fixtures.request("brasileirao:REQ-BACKUP-001")
    assert lab.process(lab.request_file(request))[0] == 0
    before = lab.show(request["request_id"])[1]["result_sha256"]
    bundle = lab.root / "bundle"
    assert cli("--state", str(lab.state), "backup", "--out", str(bundle)).returncode == 0
    restored = lab.root / "r"
    done = cli("restore", "--bundle", str(bundle), "--into", str(restored))
    assert done.returncode == 0 and json.loads(done.stdout)["status"] == "RESTORED_TO_NEW_ROOT"
    import hashlib

    restored_results = [hashlib.sha256(p.read_bytes()).hexdigest() for p in restored.rglob("research-result.json")]
    assert restored_results == [before]


def test_fault_points_are_the_frozen_matrix() -> None:
    assert PROCESS_DEATH_POINTS == (
        "before_admission_commit",
        "after_admission",
        "during_materialization",
        "before_ops",
        "after_ops",
        "after_domain_effect",
        "during_result_write",
        "after_result_write",
        "after_result_store",
    )
    assert FAULT_POINTS[-3:] == ("ops_worker_crash", "ops_worker_hang", "ops_worker_slow")
    assert outcomes  # harness helper exported
