from datetime import UTC, datetime

from brasileirao_predictor.research.price_strength.historical_admission import latest_state


def test_huge_integer_rejected_and_negative_limit_not_admitted():
    at = "2026-05-01T20:00:00Z"
    cut = datetime(2026, 5, 1, 20, tzinfo=UTC)
    state = {"createdAt": at, "active": True, "price": 10**500, "limit": 0}
    assert latest_state([state], cut)["reason"] == "invalid_latest_price"
    state["price"] = 2
    assert latest_state([state], cut)["reported_limit"] == 0
    state["limit"] = -1e-301
    assert latest_state([state], cut)["reported_limit"] is None
