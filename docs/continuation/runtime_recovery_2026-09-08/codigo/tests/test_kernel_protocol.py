import asyncio
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from brasileirao_predictor import kernel_redis_v2 as protocol
from brasileirao_predictor.kernel_daemon import _handle_invoke

PARAMS = (0.2, 1.0, 0.1, 0.0, 0.0, 6)


class FakeRedis:
    """Handler wiring double; real Lua state transitions use opt-in Redis tests."""

    def __init__(self, *, claim: bool = True):
        self.claim = claim
        self.claim_calls = []
        self.values = {}
        self.publications = []

    async def eval(self, script, count, *values):
        keys, args = values[:count], values[count:]
        if script == protocol.CLAIM_SCRIPT:
            self.claim_calls.append((keys, args))
            return b"CLAIMED" if self.claim else b"COMPLETED"
        if script == protocol.COMPLETE_SCRIPT:
            self.values[keys[3]] = (args[4] / 1000, args[3])
            self.publications.append((args[5], args[3]))
            return b"COMPLETED"
        if script == protocol.RELEASE_SCRIPT:
            return b"LEASE_LOST"
        raise AssertionError("unexpected script")


def payload(**updates) -> bytes:
    value = {
        "protocol_version": protocol.PROTOCOL_VERSION,
        "job_id": "job-1",
        "run_id": "run-1",
        "match_id": "match-1",
        "idempotency_key": "idem-1",
        "elo_a": 1600,
        "elo_b": 1500,
        "dvorp_a": 0,
        "dvorp_b": 0,
        "timestamp_t3": 1,
        "state_version": "1",
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
    assert len(client.claim_calls) == 1
    keys, args = client.claim_calls[0]
    assert keys == (
        "kernel:v2:current:match-1",
        "kernel:v2:request:run-1",
        "kernel:v2:lease:run-1",
        "kernel:v2:pending",
        "lineup_state:match-1",
    )
    assert args[:2] == (payload(), "run-1")
    assert len(args[2]) == 32 and args[3] == 5000
    assert not client.values and not client.publications


def test_valid_payload_writes_versioned_ttl_response() -> None:
    client = FakeRedis()
    run(client, payload())
    ttl, encoded = client.values["fair_odds:match-1"]
    response = json.loads(encoded)
    assert ttl == 5
    assert response["protocol_version"] == protocol.PROTOCOL_VERSION
    assert response["job_id"] == "job-1"
    assert response["run_id"] == "run-1"
    assert response["match_id"] == "match-1"
    assert response["state_version"] == "1"
    assert response["idempotency_key"] == "idem-1"
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
    client = FakeRedis()
    run(client, payload(elo_a="invalid"))
    run(client, payload())
    assert len(client.claim_calls) == 1
    assert "fair_odds:match-1" in client.values
    assert len(client.publications) == 1


@pytest.mark.parametrize("timestamp", [0, 1, 1.0, 1e20])
def test_schema_valid_numeric_representations_are_accepted(timestamp) -> None:
    value = json.loads(payload(timestamp_t3=timestamp, elo_a=1600.0, dvorp_a=-0.25))
    schema = json.loads((Path(__file__).parents[1] / "contracts" / "redis-protocol-v2.schema.json").read_text())
    Draft202012Validator(schema).validate(value)
    client = FakeRedis()
    run(client, json.dumps(value).encode())
    assert len(client.claim_calls) == 1
    assert "fair_odds:match-1" in client.values


@pytest.mark.parametrize(
    "invalid", [None, True, 1, "", "0", "01", "-1", "1.0", "1e3", "１２", "١", "9223372036854775808", "1" * 20]
)
def test_state_version_requires_canonical_positive_redis_integer(invalid) -> None:
    assert_rejected(payload(state_version=invalid))


def test_version_above_lua_double_precision_is_preserved_as_string() -> None:
    client = FakeRedis()
    run(client, payload(state_version="9223372036854775807"))
    assert json.loads(client.values["fair_odds:match-1"][1])["state_version"] == "9223372036854775807"


def test_legacy_v1_cannot_bypass_registered_v2_lifecycle() -> None:
    raw = json.loads(payload(protocol_version="brasileirao.redis/1"))
    del raw["state_version"]
    assert_rejected(json.dumps(raw).encode())
