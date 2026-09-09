from copy import deepcopy

import pytest

from brasileirao_predictor.research.price_strength.live_capture_admission import audit_capture


def payload():
    return {
        "fixtureId": "id1",
        "statusId": 0,
        "startTime": "2026-09-12T00:00:00Z",
        "bookmakerOdds": {
            b: {
                "bookmakerIsActive": True,
                "suspended": False,
                "markets": {
                    "101": {
                        "marketActive": True,
                        "outcomes": {
                            o: {
                                "players": {
                                    "0": {
                                        "active": True,
                                        "price": 3.0,
                                        "limit": None,
                                        "changedAt": "2026-09-09T10:00:00Z",
                                        "bookmakerChangedAt": None,
                                    }
                                }
                            }
                            for o in ("101", "102", "103")
                        },
                    }
                },
            }
            for b in ("pinnacle", "bet365.bet.br")
        },
    }


def audit(obj):
    return audit_capture(obj, {"requested_at": "2026-09-09T20:00:00Z", "received_at": "2026-09-09T20:00:01Z"}, "id1")


def test_active_children_cannot_override_inactive_parent():
    obj = payload()
    obj["bookmakerOdds"]["bet365.bet.br"]["bookmakerIsActive"] = False
    out = audit(obj)
    assert not out["pair_api_state_admitted"]
    assert "bookmaker_not_active" in out["bookmakers"]["bet365.bet.br"]["reasons"]


@pytest.mark.parametrize("change", ["suspended", "market", "selection", "missing_suspension_flag"])
def test_suspension_and_missing_flags_reject(change):
    obj = payload()
    book = obj["bookmakerOdds"]["bet365.bet.br"]
    if change == "suspended":
        book["suspended"] = True
    elif change == "market":
        book["markets"]["101"]["marketActive"] = False
    elif change == "selection":
        book["markets"]["101"]["outcomes"]["102"]["players"]["0"]["active"] = False
    else:
        del book["suspended"]
    assert not audit(obj)["pair_api_state_admitted"]


def test_network_receipt_is_not_bookmaker_change_or_execution():
    out = audit(payload())
    assert out["pair_api_state_admitted"]
    assert out["round_trip_seconds"] == 1
    assert not out["execution_admitted"]
    assert out["bookmakers"]["bet365.bet.br"]["legs"]["home"]["limit_currency"] is None


def test_generic_bet365_cannot_substitute_regional_book():
    obj = payload()
    obj["bookmakerOdds"]["bet365"] = obj["bookmakerOdds"].pop("bet365.bet.br")
    assert not audit(obj)["pair_api_state_admitted"]


def test_postkickoff_or_foreign_identity_cannot_be_admitted():
    obj = payload()
    obj["fixtureId"] = "id2"
    assert audit(obj)["reason"] == "fixture_identity_mismatch"
    obj = payload()
    obj["startTime"] = "2026-09-09T19:00:00Z"
    assert audit(obj)["reason"] == "not_pre_game"


def test_payload_is_not_modified():
    obj = payload()
    old = deepcopy(obj)
    audit(obj)
    assert obj == old


def test_boolean_status_cannot_masquerade_as_numeric_pre_game():
    obj = payload()
    obj["statusId"] = False
    assert audit(obj)["reason"] == "not_pre_game"
