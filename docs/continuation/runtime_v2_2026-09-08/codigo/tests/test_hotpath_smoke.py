"""Smoke tooling may wake registered work but must not manufacture authority."""

import json

import pytest
import redis

from brasileirao_scripts import hotpath_smoke


class RegisteredRedis:
    def __init__(self, *, registered=True, status="ready", response_run="run", response_identity="identity"):
        self.request = json.dumps(
            {
                "protocol_version": "brasileirao.redis/2",
                "job_id": "job",
                "run_id": "run",
                "match_id": "synthetic",
                "state_version": "9007199254740993",
                "idempotency_key": "identity",
                "elo_a": 1600,
                "elo_b": 1500,
                "dvorp_a": 0,
                "dvorp_b": 0,
                "timestamp_t3": 1,
            }
        )
        self.registered = registered
        self.status = status
        self.response_run = response_run
        self.response_identity = response_identity
        self.publications = []

    def get(self, key):
        assert key == "kernel:v2:current:synthetic"
        return self.request

    def hget(self, key, field):
        assert (key, field) == ("kernel:v2:request:run", "payload")
        return self.request if self.registered else None

    def publish(self, channel, payload):
        self.publications.append((channel, payload))

    def eval(self, script, count, *args):
        assert count == 4
        request = json.loads(self.request)
        fair = {
            **{
                key: request[key]
                for key in ("protocol_version", "job_id", "run_id", "match_id", "state_version", "idempotency_key")
            },
            "run_id": self.response_run,
            "idempotency_key": self.response_identity,
            "1": None,
            "X": 1.0,
            "2": None,
            "o25": None,
            "u25": 1.0,
        }
        return [self.status, json.dumps(fair)]


def test_smoke_wakes_only_the_exact_registered_v2_request():
    client = RegisteredRedis()
    result = hotpath_smoke.verify_registered_request(client, "synthetic")
    assert result["status"] == "VERIFIED_CURRENT_RESULT"
    assert client.publications == [("system:invoke_kernel:v2", client.request)]


def test_smoke_cannot_create_a_missing_registration():
    client = RegisteredRedis(registered=False)
    with pytest.raises(ValueError, match="registration"):
        hotpath_smoke.verify_registered_request(client, "synthetic")
    assert not client.publications


@pytest.mark.parametrize("status", ["superseded", "expired", "inconsistent", "unregistered"])
def test_smoke_rejects_noncurrent_results(status):
    with pytest.raises(ValueError, match="superseded, expired or inconsistent"):
        hotpath_smoke.verify_registered_request(RegisteredRedis(status=status), "synthetic")


def test_smoke_requires_result_correlation():
    with pytest.raises(ValueError, match="does not match"):
        hotpath_smoke.verify_registered_request(RegisteredRedis(response_run="other"), "synthetic")


def test_smoke_requires_idempotency_identity_correlation():
    with pytest.raises(ValueError, match="does not match"):
        hotpath_smoke.verify_registered_request(RegisteredRedis(response_identity="other"), "synthetic")


def test_smoke_rejects_incomplete_registered_payload_before_wakeup():
    client = RegisteredRedis()
    fields = json.loads(client.request)
    fields.pop("elo_a")
    client.request = json.dumps(fields)
    with pytest.raises(ValueError, match="contrato"):
        hotpath_smoke.verify_registered_request(client, "synthetic")
    assert not client.publications


def test_smoke_times_out_without_creating_a_replacement_request():
    client = RegisteredRedis(status="pending")
    with pytest.raises(TimeoutError):
        hotpath_smoke.verify_registered_request(client, "synthetic", timeout=0)
    assert len(client.publications) == 1


def test_cli_does_not_echo_a_connection_error_or_redis_credentials(monkeypatch, capsys):
    class Connection:
        closed = False

        def ping(self):
            raise redis.ConnectionError("SYNTHETIC_SECRET_MARKER")

        def close(self):
            self.closed = True

    client = Connection()
    monkeypatch.setattr(hotpath_smoke.redis, "from_url", lambda *args, **kwargs: client)
    assert (
        hotpath_smoke.main(["--match-id", "synthetic", "--redis", "redis://user:SYNTHETIC_SECRET_MARKER@localhost"])
        == 1
    )
    assert "SYNTHETIC_SECRET_MARKER" not in capsys.readouterr().out
    assert client.closed


def test_synthetic_smoke_sends_lineups_to_worker_without_registering_itself():
    class WorkerFixture:
        events = []

        def publish(self, channel, raw):
            assert channel == "lineups:synthetic-smoke"
            self.events.append(json.loads(raw))

        def get(self, key):
            assert key == "kernel:v2:current:" + self.events[0]["MatchId"]
            return json.dumps({"run_id": "worker-registered-run"})

        def hget(self, key, field):
            assert (key, field) == ("kernel:v2:request:worker-registered-run", "lineup_state")
            return json.dumps({"HomeLineupComplete": True, "AwayLineupComplete": True})

    client = WorkerFixture()
    match = hotpath_smoke.register_synthetic_lineup(client)
    assert match.startswith("synthetic-smoke-")
    assert [event["Side"] for event in client.events] == ["home", "away"]
    assert all(len(event["Starters"]) == 11 and event["MatchId"] == match for event in client.events)
