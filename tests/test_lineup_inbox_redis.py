"""Real producer Lua on an explicitly identified, empty disposable Redis DB14.

The fixed inbox key is the only key created or removed. No global cleanup is
allowed. The caller must reserve this DB for the duration of these tests.
"""

import json
import os
from urllib.parse import urlparse
from uuid import uuid4

import pytest
import redis

from brasileirao_scripts.lineup_inbox import INBOX_KEY, MAX_PENDING, enqueue_lineup

pytestmark = pytest.mark.integration


@pytest.fixture
def inbox_redis():
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
    owns_inbox = False
    try:
        assert client.info("server")["run_id"] == instance, "test Redis identity differs"
        assert client.dbsize() == 0, "DB14 must be empty; preexisting keys are preserved"
        owns_inbox = True
        yield client
    finally:
        try:
            if owns_inbox:
                assert client.info("server")["run_id"] == instance, "refusing cleanup on a restarted Redis"
                client.delete(INBOX_KEY)
                assert client.dbsize() == 0, "unexpected keys are preserved, never globally deleted"
        finally:
            client.close()


def _event():
    return {
        "MatchId": "synthetic-inbox-" + uuid4().hex,
        "HomeTeam": "SYNTHETIC São Paulo",
        "AwayTeam": "SYNTHETIC_AWAY",
        "Side": "home",
        "Starters": [f"SYNTHETIC_PLAYER_{index}" for index in range(11)],
        "Subs": [],
        "CapturedAt": "2030-01-01T12:34:56.123456+00:00",
    }


def test_capacity_10000_refuses_10001_without_trimming_pending_entries(inbox_redis):
    client = inbox_redis
    assert MAX_PENDING == 10000
    event = _event()
    entry_ids = [enqueue_lineup(client, event) for _ in range(MAX_PENDING)]
    group = "synthetic-group-" + uuid4().hex
    client.xgroup_create(INBOX_KEY, group, id="0-0")
    claimed = client.xreadgroup(group, "synthetic-consumer", {INBOX_KEY: ">"}, count=7)
    assert [entry_id for entry_id, _ in claimed[0][1]] == entry_ids[:7]
    assert client.xpending(INBOX_KEY, group)["pending"] == 7

    with pytest.raises(redis.ResponseError, match="lineup inbox full"):
        enqueue_lineup(client, event)

    contents = client.xrange(INBOX_KEY)
    assert client.xlen(INBOX_KEY) == MAX_PENDING
    assert [entry_id for entry_id, _ in contents] == entry_ids
    expected = json.dumps(event, allow_nan=False, ensure_ascii=False)
    assert all(fields == {"payload": expected} for _, fields in contents)
    pending = client.xpending_range(INBOX_KEY, group, min="-", max="+", count=7)
    assert [entry["message_id"] for entry in pending] == entry_ids[:7]
    assert client.xpending(INBOX_KEY, group)["pending"] == 7


def test_identical_retry_preserves_payload_and_capture_without_mutating_event(inbox_redis):
    event = _event()
    before = json.dumps(event, allow_nan=False, ensure_ascii=False)
    first = enqueue_lineup(inbox_redis, event)
    second = enqueue_lineup(inbox_redis, event)

    assert first != second  # Producer stores both; Worker registration deduplicates.
    assert inbox_redis.xrange(INBOX_KEY) == [
        (first, {"payload": before}),
        (second, {"payload": before}),
    ]
    assert json.dumps(event, allow_nan=False, ensure_ascii=False) == before


def test_invalid_inbox_type_is_rejected_without_replacing_its_value(inbox_redis):
    sentinel = "synthetic-owned-inbox-" + uuid4().hex
    assert inbox_redis.set(INBOX_KEY, sentinel, nx=True)

    with pytest.raises(redis.ResponseError, match="invalid inbox type"):
        enqueue_lineup(inbox_redis, _event())

    assert inbox_redis.type(INBOX_KEY) == "string"
    assert inbox_redis.get(INBOX_KEY) == sentinel
    assert inbox_redis.dbsize() == 1
