import asyncio
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

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


def assert_rejected(raw: bytes) -> None:
    client = FakeRedis()
    run(client, raw)
    assert not client.claim_calls, "Invalid input must not reserve an idempotency key"
    assert not client.values
    assert not client.publications


@pytest.mark.parametrize("missing", tuple(json.loads(payload())))
def test_each_required_field_is_rejected_when_missing(missing: str) -> None:
    value = json.loads(payload())
    del value[missing]
    assert_rejected(json.dumps(value).encode())


@pytest.mark.parametrize("field", ["job_id", "run_id", "match_id", "idempotency_key"])
@pytest.mark.parametrize("invalid", [None, "", 123, True, [], {}])
def test_invalid_identifier_is_rejected_without_coercion(field: str, invalid) -> None:
    assert_rejected(payload(**{field: invalid}))


@pytest.mark.parametrize("field", ["elo_a", "elo_b", "dvorp_a", "dvorp_b"])
@pytest.mark.parametrize("invalid", [None, "1500", True, [], {}, float("nan"), float("inf"), -float("inf"), 10**400])
def test_invalid_number_is_rejected_before_claim(field: str, invalid) -> None:
    assert_rejected(payload(**{field: invalid}))


@pytest.mark.parametrize("invalid", [None, "1", True, -1, -1.0, 0.5, [], {}, float("nan"), float("inf")])
def test_invalid_timestamp_is_rejected_before_claim(invalid) -> None:
    assert_rejected(payload(timestamp_t3=invalid))


@pytest.mark.parametrize("raw", [b"null", b"[]", b"1", b"true", b'"message"', b"{", b"\xff"])
def test_non_object_or_malformed_payload_is_rejected(raw: bytes) -> None:
    assert_rejected(raw)


def test_additional_properties_are_rejected() -> None:
    assert_rejected(payload(unexpected="value"))


@pytest.mark.parametrize("invalid", [None, 1, True, [], {}])
def test_non_string_protocol_version_is_rejected(invalid) -> None:
    assert_rejected(payload(protocol_version=invalid))


@pytest.mark.parametrize("elo_a", [1e308, -1e308])
def test_unrepresentable_rates_are_rejected_before_claim(elo_a: float) -> None:
    assert_rejected(payload(elo_a=elo_a))


def test_invalid_message_does_not_poison_valid_retry() -> None:
    class ClaimOnceRedis(FakeRedis):
        async def set(self, key, value, **kwargs):
            first_claim = not self.claim_calls
            await super().set(key, value, **kwargs)
            return first_claim

    client = ClaimOnceRedis()
    run(client, payload(elo_a="invalid"))
    run(client, payload())
    assert len(client.claim_calls) == 1
    assert "fair_odds:match-1" in client.values
    assert len(client.publications) == 1


@pytest.mark.parametrize("timestamp", [0, 1, 1.0, 1e20])
def test_schema_valid_numeric_representations_are_accepted(timestamp) -> None:
    value = json.loads(payload(timestamp_t3=timestamp, elo_a=1600.0, dvorp_a=-0.25))
    schema = json.loads((Path(__file__).parents[1] / "contracts" / "redis-protocol-v1.schema.json").read_text())
    Draft202012Validator(schema).validate(value)
    client = FakeRedis()
    run(client, json.dumps(value).encode())
    assert len(client.claim_calls) == 1
    assert "fair_odds:match-1" in client.values
