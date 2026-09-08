"""Synthetic characterization of residual runtime guarantees, not E2E tests.

Passing assertions document existing limitations. No Redis, database, provider,
model fitting, real odds or operational commands are used here.
"""

import asyncio
import json

import numpy as np
import pytest

from brasileirao_predictor import kernel_daemon

PARAMS = (0.2, 1.0, 0.1, 0.0, 0.0, 6)


def payload(run_id, *, timestamp, elo_a=1500, identity=None):
    return json.dumps(
        {
            "protocol_version": "brasileirao.redis/1",
            "job_id": "synthetic-match",
            "run_id": run_id,
            "match_id": "synthetic-match",
            "idempotency_key": identity or f"synthetic:{run_id}",
            "elo_a": elo_a,
            "elo_b": 1500,
            "dvorp_a": 0,
            "dvorp_b": 0,
            "timestamp_t3": timestamp,
        }
    ).encode()


def synthetic_grid(lam_a, lam_b, *_):
    # Distinct input rates yield distinct normalized odds, without JIT/model IO.
    grid = np.ones((4, 4), dtype=float)
    grid[1, 0] += lam_a
    grid[0, 1] += lam_b
    return grid / grid.sum()


class MemoryRedis:
    def __init__(self):
        self.claims = {}
        self.values = {}
        self.publications = []
        self.write_calls = 0

    async def set(self, key, value, *, ex, nx):
        assert ex == 60 and nx is True
        if key in self.claims:
            return False
        self.claims[key] = value
        return True

    async def setex(self, key, ttl, value):
        assert ttl == 5
        self.write_calls += 1
        self.values[key] = value

    async def publish(self, channel, value):
        self.publications.append((channel, value))


class DelayedClaimRedis(MemoryRedis):
    def __init__(self):
        super().__init__()
        self.old_claim_reserved = asyncio.Event()
        self.release_old_response = asyncio.Event()

    async def set(self, key, value, *, ex, nx):
        claimed = await super().set(key, value, ex=ex, nx=nx)
        if value == "old-run" and claimed:
            self.old_claim_reserved.set()
            await self.release_old_response.wait()
        return claimed


def test_older_valid_invocation_can_overwrite_newer_with_correlated_ids(monkeypatch):
    monkeypatch.setattr(kernel_daemon, "_compute_grid_jit", synthetic_grid)

    async def scenario():
        redis = DelayedClaimRedis()
        old = asyncio.create_task(
            kernel_daemon._handle_invoke(
                redis, payload("old-run", timestamp=1000, elo_a=1500), PARAMS
            )
        )
        await asyncio.wait_for(redis.old_claim_reserved.wait(), timeout=1)
        await kernel_daemon._handle_invoke(
            redis, payload("new-run", timestamp=2000, elo_a=1700), PARAMS
        )
        new_response = json.loads(redis.values["fair_odds:synthetic-match"])
        assert new_response["run_id"] == "new-run"
        redis.release_old_response.set()
        await asyncio.wait_for(old, timeout=1)
        stored = json.loads(redis.values["fair_odds:synthetic-match"])
        channel, encoded = redis.publications[-1]
        notified = json.loads(encoded)

        # Characterize the gap: a later calculation existed, but old data wins.
        assert stored["run_id"] == "old-run"
        assert stored["1"] != new_response["1"]
        assert "timestamp_t3" not in stored
        assert [json.loads(raw)["run_id"] for _, raw in redis.publications] == [
            "new-run", "old-run"
        ]
        # These are exactly the identity predicates in the C# consumer.
        assert channel == "fair_odds_ready:synthetic-match"
        assert stored["match_id"] == notified["match_id"] == "synthetic-match"
        assert stored["job_id"] == notified["job_id"]
        assert stored["run_id"] == notified["run_id"]

    asyncio.run(scenario())


def test_failure_after_claim_suppresses_immediate_retry(monkeypatch):
    monkeypatch.setattr(kernel_daemon, "_compute_grid_jit", synthetic_grid)

    class FailFirstWriteRedis(MemoryRedis):
        async def setex(self, key, ttl, value):
            self.write_calls += 1
            if self.write_calls == 1:
                raise ConnectionError("synthetic transport failure")
            self.values[key] = value

    async def scenario():
        redis = FailFirstWriteRedis()
        first = payload("first-run", timestamp=1000, identity="same-event-inputs")
        retry = payload("retry-run", timestamp=2000, identity="same-event-inputs")
        with pytest.raises(ConnectionError, match="synthetic transport failure"):
            await kernel_daemon._handle_invoke(redis, first, PARAMS)
        await kernel_daemon._handle_invoke(redis, retry, PARAMS)
        assert redis.claims == {"idempotency:same-event-inputs": "first-run"}
        assert redis.write_calls == 1
        assert redis.values == {}
        assert redis.publications == []

    asyncio.run(scenario())
