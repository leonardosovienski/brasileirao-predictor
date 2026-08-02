from scripts.smoke_odds_source import report


def test_smoke_lists_only_sanitized_bookmaker_metadata():
    rows = [
        {
            "source_event_id": "a",
            "bookmaker": "pinnacle",
            "odds_captured_at": "2026-07-22T10:00:00+00:00",
        },
        {
            "source_event_id": "a",
            "bookmaker": "pinnacle",
            "odds_captured_at": "2026-07-22T10:00:00+00:00",
        },
        {
            "source_event_id": "b",
            "bookmaker": "betfair",
            "odds_captured_at": "2026-07-22T10:01:00+00:00",
        },
    ]
    result = report(rows, "eu")
    assert result["bookmakers"] == [
        {"key": "betfair", "quotes": 1, "events": 1},
        {"key": "pinnacle", "quotes": 2, "events": 1},
    ]
    assert result["recommendation"] == "HUMAN_DECISION_REQUIRED"
    assert result["persistence"] == "none"
