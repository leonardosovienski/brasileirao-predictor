"""Explicit allowlist of synthetic integration tests; no protected evaluator."""

import os
from pathlib import Path

if os.environ.get("BRASILEIRAO_LAB_GUARD_ACTIVE") != "1":
    raise RuntimeError("isolated_lab_guard_required")

import curl_cffi.requests
import pytest


def no_http(*args, **kwargs):
    raise PermissionError("lab_native_http_forbidden")


curl_cffi.requests.Session.request = no_http
curl_cffi.requests.AsyncSession.request = no_http
root = Path(os.environ["BRASILEIRAO_LAB_OUTPUT"])
repo = Path(os.environ["BRASILEIRAO_LAB_REPO"])
tests = ["test_lineup_inbox_redis.py", "test_redis_integration.py"]
raise SystemExit(
    pytest.main(
        [str(repo / "tests" / name) for name in tests]
        + [
            "-q",
            "-m",
            "integration",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(root / "pytest-tmp"),
            "--junitxml",
            str(root / "python-junit.xml"),
            "--tb=short",
        ]
    )
)
