from copy import deepcopy
from datetime import UTC, datetime

import pytest

from brasileirao_predictor.research.price_strength.historical_admission import audit_history, latest_state

CUT = datetime(2026, 5, 1, 20, tzinfo=UTC)


def state(at="2026-05-01T19:59:50Z", price=2.0, active=True, limit=10):
    return {"createdAt": at, "price": price, "active": active, "limit": limit}


def payload():
    return {
        "fixtureId": "id123",
        "bookmakers": {
            book: {
                "markets": {
                    "101": {
                        "outcomes": {
                            outcome: {"players": {"0": [state(price=price)]}}
                            for outcome, price in zip(("101", "102", "103"), prices, strict=True)
                        }
                    }
                }
            }
            for book, prices in (("pinnacle", (2.0, 3.2, 4.0)), ("bet365", (2.4, 3.0, 3.0)))
        },
    }


def audit(value=None):
    return audit_history(
        value if value is not None else payload(),
        {"fixture_id": "id123", "kickoff_at": "2026-05-01T21:00:00Z"},
        "2026-09-09T20:00:00Z",
    )


def test_suspension_cannot_resurrect_previous_active_price():
    out = latest_state([state(), state(at="2026-05-01T20:00:00Z", active=False)], CUT)
    assert not out["valid"] and out["reason"] == "inactive_latest_state"


def test_future_state_does_not_change_past_selection():
    before = latest_state([state()], CUT)
    after = latest_state([state(), state(at="2026-05-01T20:00:01Z", price=999, active=False)], CUT)
    assert before == after


@pytest.mark.parametrize("change", [{"active": False}, {"price": 3.0}, {"active": 1}])
def test_conflicting_latest_state_fails_closed(change):
    other = {**state(), **change}
    assert latest_state([state(), other], CUT)["reason"] == "conflicting_latest_state"


@pytest.mark.parametrize("price", [True, None, "2", 1.0, -1, float("inf"), float("nan")])
def test_invalid_price_never_uses_older_good_quote(price):
    out = latest_state([state(at="2026-05-01T19:00:00Z"), state(price=price)], CUT)
    assert out["reason"] == "invalid_latest_price"


@pytest.mark.parametrize("active", [None, "true", 1])
def test_active_must_be_literal_boolean(active):
    assert latest_state([state(active=active)], CUT)["reason"] == "unverified_latest_active"


@pytest.mark.parametrize("at", [None, "bad", "2026-05-01T19:59:00"])
def test_unknown_clock_cannot_be_silently_ignored(at):
    assert latest_state([state(), state(at=at)], CUT)["reason"] == "unorderable_state_timestamp"


def test_timezone_offset_and_cutoff_inclusion():
    out = latest_state([state(at="2026-05-01T17:00:00-03:00")], CUT)
    assert out["valid"] and out["state_age_seconds"] == 0


def test_input_order_and_identical_duplicates_do_not_change_quote():
    rows = [state(), state(at="2026-05-01T19:00:00Z", price=3)]
    assert latest_state(rows, CUT) == latest_state(list(reversed(rows)) + [state()], CUT)


def test_limit_does_not_prove_fill_and_ambiguous_limit_remains_unknown():
    out = latest_state([state(), state(limit=20)], CUT)
    assert out["valid"] and out["reported_limit"] is None
    assert out["limit_currency"] is None and out["limit_is_accepted_fill"] is False


def test_retrospective_data_never_passes_execution_gate_even_with_positive_proxy():
    out = audit()
    assert out["conditional_selection"] == "home"
    assert out["conditional_net_ev"] == pytest.approx((1 / 2) / (1 / 2 + 1 / 3.2 + 1 / 4) * 2.4 - 1.02)
    assert out["archive_received_after_decision"]
    assert not out["execution_admitted"]
    assert "historical_received_at" in out["missing_execution_evidence"]


def test_mismatched_identity_is_rejected():
    obj = payload()
    obj["fixtureId"] = "id124"
    assert audit(obj)["reason"] == "payload_fixture_identity_mismatch"


def test_other_market_cannot_fill_missing_1x2():
    obj = payload()
    obj["bookmakers"]["bet365"]["markets"]["102"] = obj["bookmakers"]["bet365"]["markets"].pop("101")
    assert audit(obj)["reason"] == "incomplete_active_pair"


def test_stale_selection_and_skew_are_separate_diagnostics():
    obj = payload()
    leg = obj["bookmakers"]["bet365"]["markets"]["101"]["outcomes"]["101"]["players"]["0"][0]
    leg["createdAt"] = "2026-05-01T19:59:00Z"
    assert audit(obj)["reason"] == "state_change_skew_over_30s"
    leg["createdAt"] = "2026-05-01T19:57:59Z"
    assert audit(obj)["reason"] == "last_change_age_over_120s_not_network_freshness"


def test_no_mutation_or_use_of_result_fields():
    obj = payload()
    before = deepcopy(obj)
    expected = audit(obj)
    assert obj == before
    obj["result"] = {"home_goals": 99}
    assert audit(obj) == expected


def test_protected_time_window_cannot_enter_the_audit():
    with pytest.raises(ValueError, match="outside_allowlisted"):
        audit_history(payload(), {"fixture_id": "id123", "kickoff_at": "2026-09-09T22:00:00Z"}, "2026-09-09T20:00:00Z")
