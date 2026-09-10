"""Exercise the future collector and auditor with synthetic HTTP responses only."""

import importlib.util
import json
import urllib.error
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "docs/continuation/data_completion_2026-09-09/reproducao"
FIXTURE = "id1000032566887012"
SECRET = "SYNTHETIC_KEY_NEVER_USED_ON_NETWORK"


def load(name):
    spec = importlib.util.spec_from_file_location("contract_test_" + name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_payload():
    return {
        "fixtureId": FIXTURE,
        "startTime": "2026-09-12T00:00:00Z",
        "statusId": 0,
        "hasOdds": True,
        "participant1Id": 1982,
        "participant2Id": 1967,
        "sportId": 10,
        "tournamentId": 325,
        "seasonId": 137706,
        "bookmakerOdds": {
            book: {
                "bookmakerIsActive": True,
                "suspended": False,
                "markets": {
                    "101": {
                        "marketActive": True,
                        "outcomes": {
                            side: {
                                "players": {
                                    "0": {
                                        "price": 3.0,
                                        "active": True,
                                        "limit": None,
                                        "changedAt": "2026-09-11T22:58:00Z",
                                    }
                                }
                            }
                            for side in ("101", "102", "103")
                        },
                    }
                },
            }
            for book in ("pinnacle", "bet365.bet.br")
        },
    }


@pytest.fixture
def rig(tmp_path, monkeypatch):
    collector, helper, auditor = load("followup_capture"), load("capture_pilot"), load("audit_followup")
    helper.PRIVATE = tmp_path / "synthetic_api_config.json"
    helper.PRIVATE.write_text(json.dumps({"values": {"ODDSPAPI_KEY": SECRET}}), encoding="utf-8")
    collector.ROOT = tmp_path
    auditor.INPUT, auditor.OUTPUT = tmp_path / "followup", tmp_path / "followup_audit"
    # The outer isolated pytest harness still enforces real IO restrictions.
    monkeypatch.setattr(auditor.sys, "addaudithook", lambda hook: None)
    state = SimpleNamespace(
        now=collector.DECISION - timedelta(minutes=3),
        calls=[],
        used=67,
        price=None,
        odds=fixture_payload(),
        http_failure=False,
    )

    class Clock:
        @staticmethod
        def now(tz):
            return state.now.astimezone(tz)

    class Response:
        status = 200

        def __init__(self, raw):
            self.raw = raw
            self.headers = {"Date": state.now.strftime("%a, %d %b %Y %H:%M:%S GMT")}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            return self.raw[:size]

    class Opener:
        def open(self, request, timeout):
            endpoint = request.full_url.split("?")[0].rsplit("/", 1)[1]
            state.calls.append(endpoint)
            state.now += timedelta(milliseconds=100)
            if endpoint == "odds":
                state.used += 1
                if state.http_failure:
                    raise urllib.error.HTTPError(request.full_url, 429, SECRET, {}, None)
                body = state.odds if isinstance(state.odds, bytes) else json.dumps(state.odds).encode()
            else:
                body = json.dumps(
                    {
                        "current_subscription_id": "synthetic",
                        "subscriptions": [
                            {
                                "subscription_id": "synthetic",
                                "is_active": True,
                                "price": state.price,
                                "currency": "USD",
                                "auto_renew": False,
                                "request_limit": 250,
                                "request_count": state.used,
                            }
                        ],
                    }
                ).encode()
            return Response(body)

    class Loader:
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            module.__dict__.update(helper.__dict__)

    monkeypatch.setattr(
        collector.importlib.util,
        "spec_from_file_location",
        lambda *args: SimpleNamespace(
            loader=Loader(),
            name="synthetic_helper",
            submodule_search_locations=None,
            origin=None,
            cached=None,
            has_location=False,
        ),
    )
    monkeypatch.setattr(collector, "datetime", Clock)
    monkeypatch.setattr(
        collector.time, "sleep", lambda seconds: setattr(state, "now", state.now + timedelta(seconds=seconds))
    )
    monkeypatch.setattr(collector.urllib.request, "build_opener", lambda *args: Opener())
    return SimpleNamespace(collector=collector, auditor=auditor, helper=helper, state=state, root=tmp_path)


def receipt(rig):
    return json.loads((rig.root / "followup/receipt.json").read_text(encoding="utf-8"))


def audit_result(rig):
    return json.loads((rig.root / "followup_audit/audit.json").read_text(encoding="utf-8"))


def test_whole_capture_keeps_one_metered_call_and_is_idempotent(rig):
    rig.collector.main()
    assert rig.state.calls == ["account", "odds", "account"]
    assert receipt(rig)["status"] == "CAPTURED_REQUIRES_OFFLINE_AUDIT"
    rig.collector.main()
    assert rig.state.calls == ["account", "odds", "account"]
    rig.auditor.main()
    assert audit_result(rig)["frozen_decision_clock_admitted"]
    assert audit_result(rig)["prospective_price_observation_admitted"]
    assert not audit_result(rig)["execution_admitted"]


@pytest.mark.parametrize("offset", [-301, -45])
def test_outside_window_does_not_read_credentials_or_call_api(rig, offset):
    rig.state.now = rig.collector.DECISION + timedelta(seconds=offset)
    rig.helper.PRIVATE.unlink()
    rig.collector.main()
    assert rig.state.calls == []
    assert not (rig.root / "followup").exists()


@pytest.mark.parametrize("remaining,paid,expected", [(20, None, 0), (21, None, 1), (183, 10, 0)])
def test_quota_reserve_and_paid_plan_block_before_odds(rig, remaining, paid, expected):
    rig.state.used = 250 - remaining
    rig.state.price = paid
    rig.collector.main()
    assert rig.state.calls.count("odds") == expected
    assert 250 - rig.state.used >= 20


def test_http_failure_is_not_retried_and_does_not_expose_key(rig, capsys):
    rig.state.http_failure = True
    rig.collector.main()
    assert rig.state.calls == ["account", "odds", "account"]
    assert receipt(rig)["status"] == "STOPPED"
    assert receipt(rig)["requests"][1]["http_status"] == 429
    assert SECRET not in (rig.root / "followup/receipt.json").read_text(encoding="utf-8")
    assert SECRET not in capsys.readouterr().out


def test_invalid_json_response_is_preserved_and_audited_as_rejected(rig):
    rig.state.odds = b'{"fixtureId":'
    rig.collector.main()
    assert (rig.root / "followup/capture.json").read_bytes() == rig.state.odds
    rig.auditor.main()
    assert not audit_result(rig)["prospective_price_observation_admitted"]
    assert audit_result(rig)["status"] == "REJECTED_INVALID_INPUT"


def test_credential_failure_still_leaves_sanitized_receipt(rig):
    rig.helper.PRIVATE.write_text('{"values": {}}', encoding="utf-8")
    rig.collector.main()
    assert rig.state.calls == []
    assert receipt(rig)["status"] == "STOPPED"
    assert receipt(rig)["reason"] == "ACQUISITION_SETUP_FAILED"


def test_missing_kickoff_produces_rejection_instead_of_crashing(rig):
    rig.state.odds = {"fixtureId": FIXTURE}
    rig.collector.main()
    rig.auditor.main()
    assert audit_result(rig)["status"] == "REJECTED_INVALID_INPUT"
    assert not audit_result(rig)["prospective_price_observation_admitted"]


def test_partial_audit_directory_does_not_prevent_recovery(rig):
    rig.collector.main()
    rig.auditor.OUTPUT.mkdir()
    rig.auditor.main()
    assert audit_result(rig)["source_hash"]


def test_relabelled_provider_endpoint_cannot_be_admitted(rig):
    rig.collector.main()
    state = receipt(rig)
    state["requests"][1]["endpoint"] = "https://unverified.example/v4/odds"
    (rig.root / "followup/receipt.json").write_text(json.dumps(state), encoding="utf-8")
    rig.auditor.main()
    assert audit_result(rig)["status"] == "REJECTED_INVALID_INPUT"
    assert audit_result(rig)["reason"] == "receipt_contract_mismatch"


@pytest.mark.parametrize("received", ["2026-09-11T23:00:01+00:00", "2026-09-11T22:58:30"])
def test_late_or_timezone_free_receipt_cannot_pass_price_gate(rig, received):
    rig.collector.main()
    state = receipt(rig)
    state["requests"][1]["received_at"] = received
    (rig.root / "followup/receipt.json").write_text(json.dumps(state), encoding="utf-8")
    rig.auditor.main()
    assert not audit_result(rig)["prospective_price_observation_admitted"]


def test_rescheduled_fixture_does_not_move_frozen_decision(rig):
    rig.state.odds["startTime"] = "2026-09-12T01:00:00Z"
    rig.collector.main()
    rig.auditor.main()
    assert not audit_result(rig)["frozen_kickoff_unchanged"]
    assert not audit_result(rig)["prospective_price_observation_admitted"]
