import asyncio
import json

from brasileirao_predictor.kernel_daemon import _handle_invoke

PARAMS = (0.2, 1.0, 0.1, 0.0, 0.0, 6)


class FakeRedis:
    def __init__(self, *, claim: bool = True):
        self.claim = claim
        self.claim_calls = []
        self.values = {}
        self.publications = []

    async def set(self, key, value, **kwargs):
        self.claim_calls.append((key, value, kwargs))
        return self.claim

    async def setex(self, key, ttl, value):
        self.values[key] = (ttl, value)

    async def publish(self, channel, value):
        self.publications.append((channel, value))


def payload(**updates) -> bytes:
    value = {
        "protocol_version": "brasileirao.redis/1",
        "job_id": "job-1",
        "run_id": "run-1",
        "match_id": "match-1",
        "idempotency_key": "idem-1",
        "elo_a": 1600,
        "elo_b": 1500,
        "dvorp_a": 0,
        "dvorp_b": 0,
        "timestamp_t3": 1,
    }
    value.update(updates)
    return json.dumps(value).encode()


def run(client: FakeRedis, raw: bytes) -> None:
    asyncio.run(_handle_invoke(client, raw, PARAMS))


def test_invalid_json_and_unknown_version_are_rejected() -> None:
    client = FakeRedis()
    run(client, b"not-json")
    run(client, payload(protocol_version="brasileirao.redis/999"))
    assert not client.claim_calls and not client.values


def test_missing_identifier_is_rejected() -> None:
    client = FakeRedis()
    run(client, payload(run_id=""))
    assert not client.claim_calls and not client.values


def test_duplicate_idempotency_claim_is_safe() -> None:
    client = FakeRedis(claim=False)
    run(client, payload())
    assert client.claim_calls == [("idempotency:idem-1", "run-1", {"ex": 60, "nx": True})]
    assert not client.values and not client.publications


def test_valid_payload_writes_versioned_ttl_response() -> None:
    client = FakeRedis()
    run(client, payload())
    ttl, encoded = client.values["fair_odds:match-1"]
    response = json.loads(encoded)
    assert ttl == 5
    assert response["protocol_version"] == "brasileirao.redis/1"
    assert response["job_id"] == "job-1"
    assert response["run_id"] == "run-1"
    assert response["match_id"] == "match-1"
    assert client.publications == [("fair_odds_ready:match-1", encoded)]
