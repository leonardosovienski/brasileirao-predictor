"""Windows timeout integration uses only a short, temporary synthetic tree."""

import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from brasileirao_scripts import run_passive_task as launcher


@pytest.mark.skipif(sys.platform != "win32", reason="Windows process-tree regression")
def test_timeout_terminates_descendants_before_finished_heartbeat(tmp_path, monkeypatch):
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL

    marker = tmp_path / "grandchild_survived.txt"
    ready = tmp_path / "leaf_started.txt"
    leaf_code = (
        "import os,time; from pathlib import Path; "
        "Path('leaf_started.txt').write_text(str(os.getpid()), encoding='ascii'); "
        "time.sleep(30); Path('grandchild_survived.txt').write_text('synthetic')"
    )
    parent_code = (
        "import subprocess,sys,time\n"
        f"subprocess.Popen([sys.executable, '-c', {leaf_code!r}], creationflags=subprocess.CREATE_NO_WINDOW)\n"
        "time.sleep(40)\n"
    )
    (tmp_path / "synthetic_refresh_parent.py").write_text(parent_code, encoding="utf-8")
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher, "JOBS", {"fixture-refresh": ("synthetic_refresh_parent", (), 2.0)})
    original_popen = launcher.subprocess.Popen
    original_heartbeat = launcher._write_heartbeat
    parent = None
    leaf_handle = None
    checked_finished = []

    def start(command, **options):
        nonlocal parent, leaf_handle
        process = original_popen(command, **options)
        if "synthetic_refresh_parent" not in command:
            return process
        parent = process
        # Start the timeout only once the descendant is observed alive. A fixed
        # 300ms gap to its natural exit raced taskkill's Windows enumeration.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if ready.exists():
                try:
                    leaf_pid = int(ready.read_text(encoding="ascii"))
                except ValueError:
                    time.sleep(0.01)  # creation may precede the short PID write
                    continue
                leaf_handle = kernel.OpenProcess(0x100000 | 0x0001, False, leaf_pid)
                if not leaf_handle:
                    raise ctypes.WinError(ctypes.get_last_error())
                assert kernel.WaitForSingleObject(leaf_handle, 0) == 258  # WAIT_TIMEOUT: alive
                return process
            time.sleep(0.01)
        pytest.fail("Synthetic descendant did not become ready")

    def write_heartbeat(path, state):
        if state["status"] == "finished":
            assert leaf_handle is not None
            # An open handle identifies this exact process, even after exit;
            # absence of a delayed marker alone would not prove termination.
            assert kernel.WaitForSingleObject(leaf_handle, 0) == 0  # WAIT_OBJECT_0: exited
            assert not marker.exists()
            checked_finished.append(True)
        return original_heartbeat(path, state)

    monkeypatch.setattr(launcher.subprocess, "Popen", start)
    monkeypatch.setattr(launcher, "_write_heartbeat", write_heartbeat)
    try:
        assert launcher.run_job("fixture-refresh") == 124
        state = json.loads(
            (tmp_path / "data/runtime/passive/fixture-refresh/heartbeat.json").read_text(encoding="utf-8")
        )
        assert state["status"] == "finished" and state["error"] == "timeout"
        assert checked_finished == [True]
    finally:
        # On a failed assertion, clean up only this fixture's own tree/handle.
        try:
            if parent is not None and parent.poll() is None:
                taskkill = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/taskkill.exe"
                try:
                    launcher.subprocess.run(
                        [str(taskkill), "/PID", str(parent.pid), "/T", "/F"],
                        stdout=launcher.subprocess.DEVNULL,
                        stderr=launcher.subprocess.DEVNULL,
                        creationflags=launcher.subprocess.CREATE_NO_WINDOW,
                        timeout=15,
                        check=False,
                    )
                finally:
                    if parent.poll() is None:
                        parent.kill()
                    parent.wait(timeout=5)
        finally:
            if leaf_handle is not None:
                try:
                    if kernel.WaitForSingleObject(leaf_handle, 0) == 258:
                        if not kernel.TerminateProcess(leaf_handle, 1):
                            raise ctypes.WinError(ctypes.get_last_error())
                        assert kernel.WaitForSingleObject(leaf_handle, 5000) == 0
                finally:
                    kernel.CloseHandle(leaf_handle)


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
