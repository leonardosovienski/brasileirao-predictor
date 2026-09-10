"""Exercise the real daemon using fixed synthetic parameters, never a DB."""

import asyncio
import os
import time
from pathlib import Path

if os.environ.get("BRASILEIRAO_LAB_GUARD_ACTIVE") != "1":
    raise RuntimeError("isolated_lab_guard_required")

import redis

from brasileirao_predictor import kernel_daemon


async def main():
    url = os.environ["LINEUP_E2E_REDIS_URL"]
    if url != "redis://127.0.0.1:26380/13":
        raise ValueError("explicit_test_database_required")
    with redis.from_url(url, socket_timeout=5) as client:
        if client.info("server")["run_id"] != os.environ["LINEUP_E2E_REDIS_RUN_ID"]:
            raise ValueError("disposable_server_identity_mismatch")
    params = (0.2, 1.0, 0.1, 0.0, 0.0, 6)
    kernel_daemon._warmup_jit(params)
    root = Path(os.environ["BRASILEIRAO_LAB_OUTPUT"]).resolve()
    ready = Path(os.environ["LINEUP_E2E_READY_FILE"]).resolve()
    start = Path(os.environ["LINEUP_E2E_START_FILE"]).resolve()
    if not ready.is_relative_to(root) or not start.is_relative_to(root) or ready == start:
        raise ValueError("synthetic_bootstrap_barrier_must_stay_in_lab")
    with ready.open("x", encoding="utf-8") as file:
        file.write("imports-and-jit-ready-no-subscription")
    deadline = time.monotonic() + 60
    while not start.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("synthetic_bootstrap_not_released")
        await asyncio.sleep(0.02)
    await kernel_daemon._serve_sessions(params, url, asyncio.Event())


asyncio.run(main())
