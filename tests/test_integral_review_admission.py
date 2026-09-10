"""Regressions for contradictory current state and ambiguous capture payloads."""

import json
from pathlib import Path

import pytest
from test_followup_capture_contract import audit_result, rig  # noqa: F401
from test_live_capture_admission import audit, payload


@pytest.mark.parametrize(
    "field,value",
    [
        ("trueStartTime", "2026-09-09T19:00:00Z"),
        ("trueEndTime", "2026-09-09T19:00:00Z"),
        ("hasOdds", False),
    ],
)
def test_contradictory_fixture_state_cannot_admit_pre_game_prices(field, value):
    obj = payload()
    obj[field] = value
    assert not audit(obj).get("pair_api_state_admitted", False)


def test_missing_required_change_clock_is_not_verified_state():
    obj = payload()
    del obj["bookmakerOdds"]["bet365.bet.br"]["markets"]["101"]["outcomes"]["101"]["players"]["0"]["changedAt"]
    assert not audit(obj)["pair_api_state_admitted"]


def test_duplicate_conflicting_active_keys_are_rejected(rig):  # noqa: F811
    body = json.dumps(rig.state.odds).replace(
        '"bookmakerIsActive": true', '"bookmakerIsActive": false, "bookmakerIsActive": true'
    )
    rig.state.odds = body.encode()
    rig.collector.main()
    rig.auditor.main()
    assert not audit_result(rig)["prospective_price_observation_admitted"]


def test_duplicate_receipt_keys_are_rejected(rig):  # noqa: F811
    rig.collector.main()
    p = rig.root / "followup/receipt.json"
    p.write_text(p.read_text().replace('"http_status": 200', '"http_status": 503, "http_status": 200'))
    rig.auditor.main()
    assert not audit_result(rig)["prospective_price_observation_admitted"]


def test_nonfinite_payload_metadata_cannot_be_admitted(rig):  # noqa: F811
    rig.state.odds["updatedAt"] = float("nan")
    rig.collector.main()
    rig.auditor.main()
    assert not audit_result(rig)["prospective_price_observation_admitted"]


def test_hash_integrity_does_not_authorize_swapped_participants(rig):  # noqa: F811
    rig.state.odds.update(participant1Id=1967, participant2Id=1982, sportId=10, tournamentId=325, seasonId=137706)
    rig.collector.main()
    rig.auditor.main()
    assert not audit_result(rig)["prospective_price_observation_admitted"]


def test_concurrent_publisher_cannot_overwrite_completed_audit(rig, monkeypatch):  # noqa: F811
    rig.collector.main()
    original_write = Path.write_text
    competing = {"status": "ALREADY_FROZEN_BY_ANOTHER_PROCESS"}

    def publish_competitor(path, text, *args, **kwargs):
        result = original_write(path, text, *args, **kwargs)
        if path.parent == rig.auditor.OUTPUT and path.suffix == ".tmp":
            original_write(rig.auditor.OUTPUT / "audit.json", json.dumps(competing), encoding="utf-8")
        return result

    monkeypatch.setattr(Path, "write_text", publish_competitor)
    rig.auditor.main()
    assert audit_result(rig) == competing
