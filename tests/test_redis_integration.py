import asyncio
import json
import os

import pytest
import redis.asyncio as redis

from brasileirao_predictor import kernel_daemon

pytestmark = pytest.mark.integration


async def exercise() -> None:
    redis_url = os.environ["REDIS_URL"]
    client = redis.from_url(redis_url, decode_responses=False)
    await client.flushdb()
    subscriber = client.pubsub()
    await subscriber.subscribe("fair_odds_ready:match-integration")
    await subscriber.get_message(ignore_subscribe_messages=False, timeout=2)
    payload = {
        "protocol_version": "brasileirao.redis/1",
        "job_id": "job-integration",
        "run_id": "run-integration",
        "match_id": "match-integration",
        "idempotency_key": "idem-integration",
        "elo_a": 1600,
        "elo_b": 1500,
        "dvorp_a": 0,
        "dvorp_b": 0,
        "timestamp_t3": 1,
    }
    try:
        params = (0.2, 1.0, 0.1, 0, 0, 6)
        await kernel_daemon._handle_invoke(client, b"not-json", params)
        await kernel_daemon._handle_invoke(
            client, json.dumps({**payload, "protocol_version": "brasileirao.redis/999"}).encode(), params
        )
        await kernel_daemon._handle_invoke(
            client, json.dumps({key: value for key, value in payload.items() if key != "run_id"}).encode(), params
        )
        assert await client.dbsize() == 0

        await asyncio.gather(
            *(kernel_daemon._handle_invoke(client, json.dumps(payload).encode(), params) for _ in range(8))
        )
        raw = await client.get("fair_odds:match-integration")
        assert raw is not None
        response = json.loads(raw)
        assert response["protocol_version"] == "brasileirao.redis/1"
        assert response["match_id"] == "match-integration"
        assert 0 < await client.ttl("fair_odds:match-integration") <= 5
        message = await subscriber.get_message(ignore_subscribe_messages=True, timeout=2)
        assert message is not None and message["channel"] == b"fair_odds_ready:match-integration"

        assert await client.ttl("idempotency:idem-integration") > 0
        await kernel_daemon._handle_invoke(client, json.dumps(payload).encode(), params)
        assert await client.get("idempotency:idem-integration") == b"run-integration"
    finally:
        await subscriber.aclose()
        await client.aclose()


def test_python_redis_protocol_ttl_idempotency_and_notification(monkeypatch) -> None:
    python_grid = kernel_daemon._compute_grid_jit.py_func
    monkeypatch.setattr(kernel_daemon, "_compute_grid_jit", python_grid)
    asyncio.run(exercise())
