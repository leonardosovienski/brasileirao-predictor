"""Verify the actual module process exit code on reserved, disposable Redis DB14."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import pytest
import redis

from brasileirao_predictor import kernel_redis_v2 as protocol

pytestmark = pytest.mark.integration


@pytest.fixture
def health_redis():
    url = os.environ.get("LINEUP_TEST_REDIS_URL")
    instance = os.environ.get("LINEUP_TEST_REDIS_RUN_ID")
    if not url and not instance:
        pytest.skip("explicit disposable Redis DB14 URL and run_id are required")
    assert url and instance, "both disposable Redis URL and run_id are required"
    target = urlparse(url)
    assert target.scheme == "redis" and target.hostname in {"127.0.0.1", "localhost", "::1"}
    assert target.port and target.port != 6379 and target.path == "/14"
    assert target.username is None and target.password is None and not target.query and not target.fragment
    assert len(instance) == 40 and all(char in "0123456789abcdefABCDEF" for char in instance)
    client = redis.from_url(url, decode_responses=True, socket_connect_timeout=5, socket_timeout=5)
    owns_health = False
    try:
        assert client.info("server")["run_id"] == instance, "test Redis identity differs"
        assert client.dbsize() == 0, "DB14 must be empty; preexisting keys are preserved"
        owns_health = True
        yield client, url
    finally:
        try:
            if owns_health:
                assert client.info("server")["run_id"] == instance, "refusing cleanup on a restarted Redis"
                client.delete(protocol.HEALTH_KEY)
                assert client.dbsize() == 0, "unexpected keys are preserved, never globally deleted"
        finally:
            client.close()


@pytest.mark.parametrize("health,expected", [("missing", 1), ("healthy", 0), ("expired", 1)])
def test_healthcheck_module_process_returns_status(health_redis, tmp_path, health, expected):
    client, url = health_redis
    payload = json.dumps({"protocol_version": protocol.PROTOCOL_VERSION, "session_id": uuid4().hex})
    if health != "missing":
        assert client.eval(protocol.HEARTBEAT_SCRIPT, 1, protocol.HEALTH_KEY, payload, protocol.HEALTH_MS, "start") == 1
    if health == "expired":
        assert client.pexpire(protocol.HEALTH_KEY, 1)
        deadline = time.monotonic() + 2
        while client.exists(protocol.HEALTH_KEY) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert client.exists(protocol.HEALTH_KEY) == 0
    elif health == "missing":
        assert client.exists(protocol.HEALTH_KEY) == 0

    # A nonexistent explicit DB path proves this branch does not need model data.
    absent_db = tmp_path / "synthetic-never-opened.db"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "brasileirao_predictor.kernel_daemon",
            "--healthcheck",
            "--db",
            str(absent_db),
            "--redis",
            url,
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=os.environ.copy(),  # Inherits the caller's isolation guard and explicit test endpoint.
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        deadline = time.monotonic() + 30
        while process.poll() is None and time.monotonic() < deadline:
            if health == "healthy":
                # Keep only this synthetic session live during slow interpreter startup.
                assert (
                    client.eval(protocol.HEARTBEAT_SCRIPT, 1, protocol.HEALTH_KEY, payload, protocol.HEALTH_MS, "renew")
                    == 1
                )
            time.sleep(0.05)
        stdout, stderr = process.communicate(timeout=1)
        assert process.returncode == expected, f"exit={process.returncode}; stdout={stdout}; stderr={stderr}"
        assert not absent_db.exists()
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate()
