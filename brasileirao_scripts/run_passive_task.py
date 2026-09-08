"""Silent, allowlisted scheduled-job launcher; heartbeat contains operational data only.

Invoke through pythonw.exe on Windows. Task Scheduler must use IgnoreNew for
each job: this wrapper deliberately does not implement a second locking system.
Child output stays in local logs and is never parsed or printed by the wrapper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
JOBS = {
    "h14-persist": ("brasileirao_scripts.persist_h14_prospective", (), 900),
    "h15-persist": ("brasileirao_scripts.persist_h15_prospective", (), 900),
    "fixture-refresh": ("brasileirao_scripts.update_h9_fixtures", (), 5400),
    "model-update": ("brasileirao_predictor.cron_update_models", (), 1800),
    "a1-collect": ("brasileirao_scripts.collect_odds_a1", ("--collect",), 300),
    "a1-discover": ("brasileirao_scripts.collect_odds_a1", ("--discover",), 300),
    "a1-metrics": ("brasileirao_scripts.collector_daily_metrics", (), 300),
}


class ProcessTreeTerminationError(OSError):
    """The timed-out Windows process tree could not be confirmed terminated."""


def _run_command(command: list[str], **options) -> subprocess.CompletedProcess:
    """Keep the parent alive until its entire Windows process tree is stopped.

    subprocess.run kills only its direct child on timeout. Fixture refresh has
    children of its own, so killing that parent first would orphan active work.
    """
    if sys.platform != "win32":
        return subprocess.run(command, **options)
    timeout = options.pop("timeout")
    options.pop("check", None)
    process = subprocess.Popen(command, **options)
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        taskkill = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
        try:
            terminated = subprocess.run(
                [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                close_fds=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=15,
                check=False,
            )
            if terminated.returncode != 0:
                raise ProcessTreeTerminationError("process_tree_termination_failed")
            process.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            # Best effort for the direct child; do not misreport its unknown
            # descendants as cleaned up, or enter an unbounded context exit.
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                pass
            raise ProcessTreeTerminationError("process_tree_termination_failed") from None
        raise
    return subprocess.CompletedProcess(command, returncode)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _write_heartbeat(path: Path, state: dict) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _a1_ready() -> bool:
    """Read only initialization/rotation evidence; never collect or evaluate."""
    try:
        from brasileirao_scripts.a1_phase0 import _fingerprint

        initialized = json.loads((ROOT / "data/a1_phase0/fingerprint.json").read_text(encoding="utf-8"))
        rotation = json.loads(
            (ROOT / "data/collector_metrics/key_rotation_attestation.json").read_text(encoding="utf-8")
        )
        current = _fingerprint()["fingerprint"]
        return (
            isinstance(current, str)
            and bool(current)
            and initialized["fingerprint"] == current
            and rotation["rotated"] is True
            and bool(os.environ.get("ODDSPAPI_KEY", "").strip())
        )
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        return False


def run_job(job: str) -> int:
    """Run a fixed command, retain its exit status, and update local heartbeat."""
    if job not in JOBS:
        raise ValueError("Unknown passive job")
    module, arguments, timeout = JOBS[job]
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        executable = executable.with_name("python.exe")
    command = [str(executable), "-X", "utf8", "-m", module, *arguments]
    directory = ROOT / "data" / "runtime" / "passive" / job
    directory.mkdir(parents=True, exist_ok=True)
    heartbeat = directory / "heartbeat.json"
    last_success = None
    try:
        previous = json.loads(heartbeat.read_text(encoding="utf-8"))
        if isinstance(previous, dict) and isinstance(previous.get("last_success_at"), str):
            last_success = previous["last_success_at"]
    except (OSError, ValueError):
        pass
    started = _now()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid4().hex[:8]
    log_path = directory / f"{run_id}.log"
    state = {
        "job": job,
        "run_id": run_id,
        "status": "started",
        "started_at": started,
        "finished_at": None,
        "exit_code": None,
        "last_success_at": last_success,
        "command": command,
        "cwd": str(ROOT),
        "timeout_seconds": timeout,
        "log_path": str(log_path),
        "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    _write_heartbeat(heartbeat, state)
    error = None
    if job.startswith("a1-") and not _a1_ready():
        exit_code, error = 78, "a1_preflight_failed"
    else:
        try:
            with log_path.open("xb") as log:
                result = _run_command(
                    command,
                    cwd=ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    shell=False,
                    close_fds=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    timeout=timeout,
                    check=False,
                )
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            exit_code, error = 124, "timeout"
        except ProcessTreeTerminationError:
            exit_code, error = 125, "timeout_tree_cleanup_failed"
        except OSError:
            exit_code, error = 127, "launch_or_log_error"
    finished = _now()
    state.update(status="finished", finished_at=finished, exit_code=exit_code, error=error)
    if exit_code == 0:
        state["last_success_at"] = finished
    _write_heartbeat(heartbeat, state)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", choices=JOBS)
    return run_job(parser.parse_args(argv).job)


if __name__ == "__main__":
    raise SystemExit(main())
