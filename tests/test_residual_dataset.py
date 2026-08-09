from src.research.residual_dataset import materialize_total_market_records


def _quote(book, selection, odd, captured="2026-08-09T10:00:00+00:00"):
    return {
        "source_event_id": "e",
        "market": "ou2.5",
        "line": 2.5,
        "selection": selection,
        "bookmaker": book,
        "decimal_odds": odd,
        "odds_captured_at": captured,
        "kickoff_at": "2026-08-11T12:00:00+00:00",
    }


def test_materializes_only_complete_books_available_at_horizon():
    observations = [
        _quote("a", "over", 2.0),
        _quote("a", "under", 1.9),
        _quote("b", "over", 2.1),
        _quote("b", "under", 1.8),
        _quote("late", "over", 9.0, "2026-08-11T11:00:00+00:00"),
        _quote("late", "under", 9.0, "2026-08-11T11:00:00+00:00"),
    ]
    results = [{"source_event_id": "e", "home_goals": 2, "away_goals": 1, "settled_at": "2026-08-11T14:00:00+00:00"}]
    rows = materialize_total_market_records(observations, results, horizon_hours=24)
    assert len(rows) == 1
    assert rows[0]["outcome"] == 1
    assert rows[0]["best_odds"] == 2.1
    assert rows[0]["book_count"] == 2
    assert rows[0]["scientific_state"] == "COLLECTION_ONLY"


def test_does_not_materialize_without_result_or_complete_market():
    assert materialize_total_market_records([_quote("a", "over", 2.0)], [], horizon_hours=24) == []
