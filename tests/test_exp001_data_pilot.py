from datetime import UTC, datetime

from brasileirao_scripts.exp001_data_pilot import _latest_at_cutoff


def test_pilot_rejects_snapshots_after_cutoff():
    book = {"markets": {"101": {"outcomes": {}}}}
    for outcome, price in (("101", 2.0), ("102", 3.0), ("103", 4.0)):
        book["markets"]["101"]["outcomes"][outcome] = {
            "players": {
                "0": [
                    {"createdAt": "2026-01-01T11:59:00Z", "price": price, "active": True},
                    {"createdAt": "2026-01-01T12:01:00Z", "price": 99, "active": True},
                ]
            }
        }
    result = _latest_at_cutoff(book, datetime(2026, 1, 1, 12, tzinfo=UTC))
    assert result is not None
    assert result["home_odds"] == 2.0
    assert result["draw_odds"] == 3.0
    assert result["away_odds"] == 4.0


def test_pilot_fails_closed_when_one_1x2_leg_is_missing():
    book = {"markets": {"101": {"outcomes": {}}}}
    assert _latest_at_cutoff(book, datetime(2026, 1, 1, 12, tzinfo=UTC)) is None
