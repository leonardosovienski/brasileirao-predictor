"""Windows timeout integration uses only a short, temporary synthetic tree."""

import json
import sys
import time
from types import SimpleNamespace

import pytest

from brasileirao_scripts import run_passive_task as launcher


@pytest.mark.skipif(sys.platform != "win32", reason="Windows process-tree regression")
def test_timeout_terminates_descendants_before_finished_heartbeat(tmp_path, monkeypatch):
    marker = tmp_path / "grandchild_survived.txt"
    leaf_code = (
        "import time; from pathlib import Path; "
        "Path('leaf_started.txt').write_text('synthetic'); "
        "time.sleep(2.3); Path('grandchild_survived.txt').write_text('synthetic')"
    )
    parent_code = (
        "import subprocess,sys,time\n"
        f"subprocess.Popen([sys.executable, '-c', {leaf_code!r}], creationflags=subprocess.CREATE_NO_WINDOW)\n"
        "time.sleep(20)\n"
    )
    (tmp_path / "synthetic_refresh_parent.py").write_text(parent_code, encoding="utf-8")
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher, "JOBS", {"fixture-refresh": ("synthetic_refresh_parent", (), 2.0)})
    assert launcher.run_job("fixture-refresh") == 124
    state = json.loads((tmp_path / "data/runtime/passive/fixture-refresh/heartbeat.json").read_text(encoding="utf-8"))
    assert state["status"] == "finished" and state["error"] == "timeout"
    assert (tmp_path / "leaf_started.txt").exists(), "Synthetic descendant must actually have started"
    time.sleep(1.0)
    assert not marker.exists()


def test_failed_tree_cleanup_is_explicit_and_waits_are_bounded(monkeypatch):
    waits, killed, kill_commands = [], [], []

    class Child:
        pid = 424242

        def wait(self, timeout):
            waits.append(timeout)
            if len(waits) == 1:
                raise launcher.subprocess.TimeoutExpired("synthetic", timeout)
            return -1

        def poll(self):
            return None

        def kill(self):
            killed.append(True)

    def fake_taskkill(command, **options):
        kill_commands.append(command)
        assert options["shell"] is False
        assert options["timeout"] == 15
        assert options["stdout"] == options["stderr"] == launcher.subprocess.DEVNULL
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(launcher.sys, "platform", "win32")
    monkeypatch.setattr(launcher.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: Child())
    monkeypatch.setattr(launcher.subprocess, "run", fake_taskkill)
    with pytest.raises(launcher.ProcessTreeTerminationError):
        launcher._run_command(["synthetic"], timeout=1, check=False)
    assert kill_commands[0][1:] == ["/PID", "424242", "/T", "/F"]
    assert killed == [True]
    assert waits == [1, 10]
