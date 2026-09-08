"""Real Lua on an explicitly identified disposable Redis; no global cleanup.

Synthetic registration here does not exercise .NET registration. Only UUID
keys/members created by a scenario are removed. No FLUSHDB or FLUSHALL.
"""

import asyncio
import json
import os
from urllib.parse import urlparse
from uuid import uuid4

import numpy as np
import pytest
import redis.asyncio as redis

from brasileirao_predictor import kernel_daemon
from brasileirao_predictor import kernel_redis_v2 as protocol

pytestmark = pytest.mark.integration
PARAMS = (0.2, 1.0, 0.1, 0.0, 0.0, 6)


def _test_endpoint():
    url = os.environ.get("LINEUP_TEST_REDIS_URL")
    instance = os.environ.get("LINEUP_TEST_REDIS_RUN_ID")
    if not url and not instance:
        pytest.skip("explicit disposable Redis URL and run_id are required")
    assert url and instance, "both disposable Redis URL and run_id are required"
    target = urlparse(url)
    assert target.scheme == "redis" and target.hostname in {"127.0.0.1", "localhost", "::1"}
    assert target.port and target.port != 6379
    assert target.path.lstrip("/").isdigit() and 1 <= int(target.path[1:]) <= 15
    return url, instance


class Scenario:
    def __init__(self, client):
        self.client = client
        self.match = "synthetic-kernel-" + uuid4().hex
        self.keys = {protocol.CURRENT_PREFIX + self.match, "fair_odds:" + self.match, "lineup_state:" + self.match}
        self.runs = set()

    def request(self, *, version="1", elo_a=1500):
        run = uuid4().hex
        self.runs.add(run)
        self.keys.update({protocol.REQUEST_PREFIX + run, protocol.LEASE_PREFIX + run})
        return json.dumps(
            {
                "protocol_version": protocol.PROTOCOL_VERSION,
                "job_id": self.match,
                "run_id": run,
                "match_id": self.match,
                "idempotency_key": "synthetic:" + uuid4().hex,
                "state_version": version,
                "elo_a": elo_a,
                "elo_b": 1500,
                "dvorp_a": 0,
                "dvorp_b": 0,
                "timestamp_t3": 1,
            },
            separators=(",", ":"),
        ).encode()

    async def register(self, raw, *, ttl_ms=60000):
        run = json.loads(raw)["run_id"]
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.set(protocol.CURRENT_PREFIX + self.match, raw, px=60000)
            pipe.set("lineup_state:" + self.match, "{}", px=60000)
            pipe.hset(
                protocol.REQUEST_PREFIX + run, mapping={"payload": raw, "status": "pending", "lineup_state": "{}"}
            )
            pipe.pexpire(protocol.REQUEST_PREFIX + run, ttl_ms)
            pipe.zadd(protocol.PENDING_KEY, {run: 0})
            await pipe.execute()

    async def claim(self, raw, token):
        run = json.loads(raw)["run_id"]
        return await self.client.eval(
            protocol.CLAIM_SCRIPT,
            5,
            protocol.CURRENT_PREFIX + self.match,
            protocol.REQUEST_PREFIX + run,
            protocol.LEASE_PREFIX + run,
            protocol.PENDING_KEY,
            "lineup_state:" + self.match,
            raw,
            run,
            token,
            protocol.LEASE_MS,
        )

    async def complete(self, raw, token, *, client=None):
        msg = json.loads(raw)
        fair = {
            key: msg[key]
            for key in ("protocol_version", "job_id", "run_id", "match_id", "idempotency_key", "state_version")
        }
        fair.update({"1": 2.5, "X": 4.0, "2": 2.8571, "o25": 2.0, "u25": 2.0})
        return await (client or self.client).eval(
            protocol.COMPLETE_SCRIPT,
            6,
            protocol.CURRENT_PREFIX + self.match,
            protocol.REQUEST_PREFIX + msg["run_id"],
            protocol.LEASE_PREFIX + msg["run_id"],
            "fair_odds:" + self.match,
            protocol.PENDING_KEY,
            "lineup_state:" + self.match,
            raw,
            msg["run_id"],
            token,
            json.dumps(fair),
            protocol.FAIR_MS,
            "fair_odds_ready:" + self.match,
            protocol.RETRY_MS,
        )

    async def release(self, raw, token):
        run = json.loads(raw)["run_id"]
        return await self.client.eval(
            protocol.RELEASE_SCRIPT,
            5,
            protocol.CURRENT_PREFIX + self.match,
            protocol.REQUEST_PREFIX + run,
            protocol.LEASE_PREFIX + run,
            protocol.PENDING_KEY,
            "lineup_state:" + self.match,
            raw,
            run,
            token,
            protocol.RETRY_MS,
        )

    async def poll(self):
        return await self.client.eval(
            protocol.POLL_SCRIPT,
            1,
            protocol.PENDING_KEY,
            protocol.POLL_LIMIT,
            protocol.REQUEST_PREFIX,
            protocol.CURRENT_PREFIX,
            protocol.LEASE_PREFIX,
        )


def run_scenario(scenario):
    url, instance = _test_endpoint()

    async def exercise():
        client = redis.from_url(url, decode_responses=False)
        state = Scenario(client)
        verified = False
        try:
            assert (await client.info("server"))["run_id"] == instance
            verified = True
            await scenario(state)
        finally:
            # Do not clean a different/restarted server at a reused address.
            try:
                if verified and (await client.info("server"))["run_id"] == instance:
                    await client.delete(*state.keys)
                    if state.runs:
                        await client.zrem(protocol.PENDING_KEY, *state.runs)
            finally:
                await client.aclose()

    asyncio.run(exercise())


@pytest.fixture(autouse=True)
def synthetic_grid(monkeypatch):
    def grid(lam_a, lam_b, *_):
        result = np.ones((4, 4))
        result[1, 0] += lam_a
        result[0, 1] += lam_b
        return result / result.sum()

    monkeypatch.setattr(kernel_daemon, "_compute_grid_jit", grid)


def test_registered_request_completes_once_without_extending_ttl():
    async def scenario(s):
        raw = s.request()
        await s.register(raw)
        subscriber = s.client.pubsub()
        await subscriber.subscribe("fair_odds_ready:" + s.match)
        await subscriber.get_message(timeout=1)
        try:
            await asyncio.gather(*(kernel_daemon._handle_invoke(s.client, raw, PARAMS) for _ in range(8)))
            fair_key = "fair_odds:" + s.match
            fair = json.loads(await s.client.get(fair_key))
            run = json.loads(raw)["run_id"]
            assert fair["run_id"] == run and fair["state_version"] == "1"
            assert await s.client.hget(protocol.REQUEST_PREFIX + run, "status") == b"completed"
            assert await s.client.zscore(protocol.PENDING_KEY, run) is None
            assert await s.client.get(protocol.LEASE_PREFIX + run) is None
            message = await subscriber.get_message(ignore_subscribe_messages=True, timeout=1)
            assert message and json.loads(message["data"]) == fair
            await s.client.pexpire(fair_key, 1000)
            await kernel_daemon._handle_invoke(s.client, raw, PARAMS)
            assert 0 < await s.client.pttl(fair_key) <= 1000
            assert await subscriber.get_message(ignore_subscribe_messages=True, timeout=0.05) is None
        finally:
            await subscriber.aclose()

    run_scenario(scenario)


def test_older_completion_cannot_overwrite_newer_current():
    async def scenario(s):
        old, new = s.request(), s.request(version="2", elo_a=1700)
        await s.register(old)
        assert await s.claim(old, "old-token") == b"CLAIMED"
        await s.register(new)
        await kernel_daemon._handle_invoke(s.client, new, PARAMS)
        before = await s.client.get("fair_odds:" + s.match)
        assert await s.complete(old, "old-token") == b"STALE"
        assert await s.client.get("fair_odds:" + s.match) == before
        assert json.loads(before)["run_id"] == json.loads(new)["run_id"]
        assert await s.client.zscore(protocol.PENDING_KEY, json.loads(old)["run_id"]) is None

    run_scenario(scenario)


def test_unregistered_or_modified_payload_cannot_claim_current_request():
    async def scenario(s):
        raw = s.request()
        assert await s.claim(raw, "unregistered") == b"EXPIRED"
        await s.register(raw)
        modified = json.dumps({**json.loads(raw), "elo_a": 1900}).encode()
        assert await s.claim(modified, "modified") == b"UNREGISTERED"
        assert await s.client.zscore(protocol.PENDING_KEY, json.loads(raw)["run_id"]) is not None
        assert await s.client.get(protocol.LEASE_PREFIX + json.loads(raw)["run_id"]) is None
        assert await s.claim(raw, "correct") == b"CLAIMED"

    run_scenario(scenario)


def test_lineup_snapshot_change_blocks_claim_and_completion_without_head_change():
    async def scenario(s):
        raw = s.request()
        await s.register(raw)
        assert await s.claim(raw, "token") == b"CLAIMED"
        await s.client.set("lineup_state:" + s.match, '{"changed":true}')
        assert await s.complete(raw, "token") == b"STALE"
        assert await s.client.get("fair_odds:" + s.match) is None
        await s.register(raw)
        await s.client.set("lineup_state:" + s.match, '{"changed":true}')
        assert await s.claim(raw, "later") == b"STALE"
        assert await s.client.get("fair_odds:" + s.match) is None

    run_scenario(scenario)


def test_lost_completion_response_cannot_reset_completed_work_or_republish():
    async def scenario(s):
        raw = s.request()
        await s.register(raw)

        class LostResponse:
            async def eval(self, script, *args):
                value = await s.client.eval(script, *args)
                if script == protocol.COMPLETE_SCRIPT:
                    raise ConnectionError("synthetic loss after real commit")
                return value

        await kernel_daemon._handle_invoke(LostResponse(), raw, PARAMS)
        run = json.loads(raw)["run_id"]
        assert await s.client.hget(protocol.REQUEST_PREFIX + run, "status") == b"completed"
        before = await s.client.get("fair_odds:" + s.match)
        await s.client.pexpire("fair_odds:" + s.match, 1000)
        await kernel_daemon._handle_invoke(s.client, raw, PARAMS)
        assert await s.client.get("fair_odds:" + s.match) == before
        assert 0 < await s.client.pttl("fair_odds:" + s.match) <= 1000

    run_scenario(scenario)


def test_lost_owner_cannot_finish_or_release_reclaimed_attempt():
    async def scenario(s):
        raw = s.request()
        run = json.loads(raw)["run_id"]
        await s.register(raw)
        assert await s.claim(raw, "old") == b"CLAIMED"
        await s.client.pexpire(protocol.LEASE_PREFIX + run, 1)
        await asyncio.sleep(0.01)
        assert await s.claim(raw, "new") == b"CLAIMED"
        assert await s.complete(raw, "old") == b"LEASE_LOST"
        assert await s.release(raw, "old") == b"LEASE_LOST"
        assert await s.client.get(protocol.LEASE_PREFIX + run) == b"new"
        assert await s.complete(raw, "new") == b"COMPLETED"

    run_scenario(scenario)


def test_poll_recovers_lost_wakeup_and_removes_superseded_or_expired():
    async def scenario(s):
        old, raw = s.request(), s.request(version="2")
        await s.register(old)
        await s.register(raw)
        assert await s.poll() == [raw]
        run = json.loads(raw)["run_id"]
        assert await s.claim(raw, "dead-worker") == b"CLAIMED"
        await s.client.pexpire(protocol.LEASE_PREFIX + run, 1)
        await s.client.zadd(protocol.PENDING_KEY, {run: 0})
        await asyncio.sleep(0.01)
        assert await s.poll() == [raw]
        await kernel_daemon._handle_invoke(s.client, raw, PARAMS)
        assert await s.client.hget(protocol.REQUEST_PREFIX + run, "status") == b"completed"
        expired = s.request(version="3")
        await s.register(expired, ttl_ms=1)
        await asyncio.sleep(0.01)
        assert await s.poll() == []
        assert await s.claim(expired, "too-late") == b"EXPIRED"

    run_scenario(scenario)


def test_request_expiry_blocks_completion_and_completion_does_not_renew_request():
    async def scenario(s):
        raw = s.request()
        await s.register(raw)
        run = json.loads(raw)["run_id"]
        assert await s.claim(raw, "token") == b"CLAIMED"
        await s.client.pexpire(protocol.REQUEST_PREFIX + run, 1)
        await asyncio.sleep(0.01)
        assert await s.complete(raw, "token") == b"STALE"
        assert await s.client.get("fair_odds:" + s.match) is None
        current = s.request(version="2")
        await s.register(current)
        run = json.loads(current)["run_id"]
        await s.client.pexpire(protocol.REQUEST_PREFIX + run, 1000)
        await kernel_daemon._handle_invoke(s.client, current, PARAMS)
        assert 0 < await s.client.pttl(protocol.REQUEST_PREFIX + run) <= 1000
        assert 0 < await s.client.pttl("fair_odds:" + s.match) <= 1000

    run_scenario(scenario)


@pytest.mark.parametrize("denied", ["channel", "hset", "zrem", "del", "set", "publish"])
def test_acl_error_keeps_work_retryable_without_fair_output(denied):
    async def scenario(s):
        raw = s.request()
        await s.register(raw)
        run = json.loads(raw)["run_id"]
        assert await s.claim(raw, "token") == b"CLAIMED"
        user = "synthetic-kernel-" + uuid4().hex
        restrictions = ["resetchannels"] if denied == "channel" else ["allchannels", "-" + denied]
        await s.client.execute_command("ACL", "SETUSER", user, "on", "nopass", "~*", "+@all", *restrictions)
        restricted = redis.from_url(os.environ["LINEUP_TEST_REDIS_URL"], username=user, decode_responses=False)
        try:
            assert await s.complete(raw, "token", client=restricted) == b"ACL_DENIED"
            assert await s.client.hget(protocol.REQUEST_PREFIX + run, "status") == b"pending"
            assert await s.client.get("fair_odds:" + s.match) is None
            assert await s.client.get(protocol.LEASE_PREFIX + run) == b"token"
            assert await s.client.zscore(protocol.PENDING_KEY, run) is not None
            assert await s.release(raw, "token") == b"RETRY"
            assert await s.claim(raw, "retry") == b"CLAIMED"
            assert await s.complete(raw, "retry") == b"COMPLETED"
        finally:
            await restricted.aclose()
            if (await s.client.info("server"))["run_id"] == os.environ["LINEUP_TEST_REDIS_RUN_ID"]:
                await s.client.execute_command("ACL", "DELUSER", user)

    run_scenario(scenario)


def test_health_heartbeat_expires_after_crash_without_cleanup():
    async def scenario(s):
        key = "synthetic-health:" + s.match
        s.keys.add(key)
        value = json.dumps({"protocol_version": protocol.PROTOCOL_VERSION, "session_id": "crashed"})
        assert await s.client.eval(protocol.HEARTBEAT_SCRIPT, 1, key, value, 50, "start") == 1
        assert await s.client.eval(protocol.HEALTHCHECK_SCRIPT, 1, key) == 1
        await asyncio.sleep(0.06)
        assert await s.client.eval(protocol.HEALTHCHECK_SCRIPT, 1, key) == 0

    run_scenario(scenario)


def test_old_session_cannot_renew_or_remove_new_session_heartbeat():
    async def scenario(s):
        key = "synthetic-health:" + s.match
        s.keys.add(key)
        old = json.dumps({"protocol_version": protocol.PROTOCOL_VERSION, "session_id": "old"})
        new = json.dumps({"protocol_version": protocol.PROTOCOL_VERSION, "session_id": "new"})
        assert await s.client.eval(protocol.HEARTBEAT_SCRIPT, 1, key, old, 5000, "start") == 1
        assert await s.client.eval(protocol.HEARTBEAT_SCRIPT, 1, key, new, 5000, "start") == 1
        assert await s.client.eval(protocol.HEARTBEAT_SCRIPT, 1, key, old, 5000, "renew") == 0
        assert await s.client.eval(protocol.HEARTBEAT_SCRIPT, 1, key, old, 5000, "release") == 0
        assert await s.client.get(key) == new.encode()
        assert await s.client.eval(protocol.HEALTHCHECK_SCRIPT, 1, key) == 1

    run_scenario(scenario)


def test_disconnected_poller_stops_renewal_and_health_expires(monkeypatch):
    async def scenario(s):
        key = "synthetic-health:" + s.match
        s.keys.add(key)
        monkeypatch.setattr(protocol, "HEALTH_KEY", key)
        value = json.dumps({"protocol_version": protocol.PROTOCOL_VERSION, "session_id": "disconnected"})
        await s.client.eval(protocol.HEARTBEAT_SCRIPT, 1, key, value, 50, "start")

        class Disconnected:
            async def eval(self, script, *args):
                if script == protocol.HEARTBEAT_SCRIPT:
                    raise ConnectionError("synthetic disconnected socket")
                return await s.client.eval(script, *args)

        with pytest.raises(ConnectionError):
            await kernel_daemon._poll_pending(Disconnected(), PARAMS, asyncio.Event(), value)
        await asyncio.sleep(0.06)
        assert await s.client.eval(protocol.HEALTHCHECK_SCRIPT, 1, key) == 0

    run_scenario(scenario)


def test_healthcheck_rejects_legacy_or_durable_flags():
    async def scenario(s):
        key = "synthetic-health:" + s.match
        s.keys.add(key)
        await s.client.set(key, "ready")
        assert await s.client.eval(protocol.HEALTHCHECK_SCRIPT, 1, key) == 0
        value = json.dumps({"protocol_version": protocol.PROTOCOL_VERSION, "session_id": "no-deadline"})
        await s.client.set(key, value)
        assert await s.client.eval(protocol.HEALTHCHECK_SCRIPT, 1, key) == 0
        await s.client.set(key, json.dumps({"protocol_version": "brasileirao.redis/1", "session_id": "old"}), px=5000)
        assert await s.client.eval(protocol.HEALTHCHECK_SCRIPT, 1, key) == 0

    run_scenario(scenario)
