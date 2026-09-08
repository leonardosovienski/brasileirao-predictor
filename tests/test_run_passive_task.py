"""Operational launcher tests: no real jobs or network requests are executed."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from brasileirao_scripts import run_passive_task as launcher


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher.sys, "executable", str(tmp_path / "venv" / "pythonw.exe"))
    monkeypatch.setattr(launcher.sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    return tmp_path


def heartbeat(root, job="h14-persist"):
    path = root / "data" / "runtime" / "passive" / job / "heartbeat.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "job,module,arguments,timeout",
    [
        ("h14-persist", "brasileirao_scripts.persist_h14_prospective", [], 900),
        ("h15-persist", "brasileirao_scripts.persist_h15_prospective", [], 900),
        ("fixture-refresh", "brasileirao_scripts.update_h9_fixtures", [], 5400),
        ("model-update", "brasileirao_predictor.cron_update_models", [], 1800),
        ("a1-collect", "brasileirao_scripts.collect_odds_a1", ["--collect"], 300),
        ("a1-discover", "brasileirao_scripts.collect_odds_a1", ["--discover"], 300),
        ("a1-metrics", "brasileirao_scripts.collector_daily_metrics", [], 300),
    ],
)
def test_allowlist_silent_windows_launch(isolated, monkeypatch, capsys, job, module, arguments, timeout):
    monkeypatch.setattr(launcher, "_a1_ready", lambda: True)

    def run(command, **options):
        assert command == [str(isolated / "venv" / "python.exe"), "-X", "utf8", "-m", module, *arguments]
        assert options["cwd"] == isolated
        assert options["shell"] is False
        assert options["creationflags"] == 0x08000000
        assert options["stdin"] == subprocess.DEVNULL
        assert options["stderr"] == subprocess.STDOUT
        assert options["timeout"] == timeout
        assert options["check"] is False
        assert options["close_fds"] is True
        assert heartbeat(isolated, job)["status"] == "started"
        options["stdout"].write(b"synthetic child output")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(launcher, "_run_command", run)
    assert launcher.main([job]) == 0
    state = heartbeat(isolated, job)
    assert state["status"] == "finished"
    assert state["exit_code"] == 0
    assert state["last_success_at"] == state["finished_at"]
    assert state["error"] is None
    assert "synthetic child output" not in json.dumps(state)
    assert len(state["wrapper_sha256"]) == 64
    logs = list((isolated / "data" / "runtime" / "passive" / job).glob("*.log"))
    assert len(logs) == 1 and logs[0].read_bytes() == b"synthetic child output"
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "failure,expected,error",
    [
        (17, 17, None),
        (subprocess.TimeoutExpired("hidden detail", 900), 124, "timeout"),
        (launcher.ProcessTreeTerminationError("hidden detail"), 125, "timeout_tree_cleanup_failed"),
        (OSError("hidden detail"), 127, "launch_or_log_error"),
    ],
)
def test_failure_exit_and_heartbeat_preserve_success(isolated, monkeypatch, capsys, failure, expected, error):
    monkeypatch.setattr(launcher, "_run_command", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    assert launcher.run_job("h14-persist") == 0
    previous_success = heartbeat(isolated)["last_success_at"]

    def run(*args, **kwargs):
        if isinstance(failure, Exception):
            raise failure
        return SimpleNamespace(returncode=failure)

    monkeypatch.setattr(launcher, "_run_command", run)
    assert launcher.run_job("h14-persist") == expected
    state = heartbeat(isolated)
    assert state["status"] == "finished" and state["finished_at"] is not None
    assert state["exit_code"] == expected and state["error"] == error
    assert state["last_success_at"] == previous_success
    assert "hidden detail" not in json.dumps(state)
    assert len(list((isolated / "data" / "runtime" / "passive" / "h14-persist").glob("*.log"))) == 2
    assert capsys.readouterr() == ("", "")


def test_reject_unknown_job_before_launch(isolated, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("An unknown job must never start a process")

    monkeypatch.setattr(launcher, "_run_command", unexpected)
    with pytest.raises(ValueError, match="Unknown passive job"):
        launcher.run_job("evaluate_h14_prospective")
    assert not (isolated / "data").exists()


def test_python_executable_is_preserved(isolated, monkeypatch):
    executable = str(isolated / "venv" / "python.exe")
    monkeypatch.setattr(launcher.sys, "executable", executable)

    def run(command, **kwargs):
        assert command[0] == executable
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(launcher, "_run_command", run)
    assert launcher.run_job("h14-persist") == 0


@pytest.mark.parametrize("case", ["ok", "missing", "mismatch", "rotation_missing", "rotation_false", "key_missing"])
def test_a1_preflight_fails_closed(isolated, monkeypatch, capsys, case):
    phase = isolated / "data" / "a1_phase0"
    metrics = isolated / "data" / "collector_metrics"
    phase.mkdir(parents=True)
    metrics.mkdir(parents=True)
    if case != "missing":
        (phase / "fingerprint.json").write_text(
            json.dumps({"fingerprint": "other" if case == "mismatch" else "synthetic-hash"}), encoding="utf-8"
        )
    if case != "rotation_missing":
        (metrics / "key_rotation_attestation.json").write_text(
            json.dumps({"rotated": case != "rotation_false"}), encoding="utf-8"
        )
    monkeypatch.setenv("ODDSPAPI_KEY", "" if case == "key_missing" else "synthetic-secret")
    monkeypatch.setitem(
        launcher.sys.modules,
        "brasileirao_scripts.a1_phase0",
        SimpleNamespace(_fingerprint=lambda: {"fingerprint": "synthetic-hash"}),
    )
    calls = []

    def run(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(launcher, "_run_command", run)
    assert launcher.run_job("a1-collect") == (0 if case == "ok" else 78)
    assert len(calls) == (1 if case == "ok" else 0)
    state = heartbeat(isolated, "a1-collect")
    assert state["status"] == "finished"
    assert state["error"] == (None if case == "ok" else "a1_preflight_failed")
    assert "synthetic-secret" not in json.dumps(state)
    assert capsys.readouterr() == ("", "")
