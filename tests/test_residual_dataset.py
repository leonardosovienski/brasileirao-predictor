from brasileirao_predictor.research.residual_dataset import materialize_total_market_records


def _quote(book, selection, odd, captured="2026-08-10T11:59:00+00:00"):
    return {
        "source_event_id": "e",
        "market": "ou2.5",
        "line": 2.5,
        "selection": selection,
        "bookmaker": book,
        "decimal_odds": odd,
        "odds_captured_at": captured,
        "kickoff_at": "2026-08-11T12:00:00+00:00",
        "source": "synthetic",
        "period": "FT",
        "status": "ACTIVE",
        "observed_at": captured,
        "available_at": captured,
        "retrieved_at": captured,
    }


def _context():
    return {
        "e": {
            "available_at": "2026-08-10T11:58:00+00:00",
            "xg_form_delta": 0,
            "rest_days_delta": 0,
            "current_starters": [],
            "expected_starters": [],
        }
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
    rows = materialize_total_market_records(
        observations, results, horizon_hours=24, offer_bookmaker="b", context=_context()
    )
    assert len(rows) == 1
    assert rows[0]["outcome"] == 1
    assert rows[0]["best_odds"] == 2.1
    assert rows[0]["best_odds_by_selection"] == {"over": 2.1, "under": 1.8}
    assert rows[0]["book_count"] == 1
    assert rows[0]["scientific_state"] == "COLLECTION_ONLY"


def test_keeps_unfinished_event_and_incomplete_market_as_abstention():
    rows = materialize_total_market_records([_quote("a", "over", 2.0)], [], horizon_hours=24, offer_bookmaker="b")
    assert len(rows) == 1 and rows[0]["outcome"] is None
    assert rows[0]["data_status"] == "ABSTAIN_DATA"


def test_rejects_synthetic_pair_from_different_market_states():
    observations = [
        _quote("a", "over", 2.0, "2026-08-10T11:50:00+00:00"),
        _quote("a", "under", 1.9, "2026-08-10T11:55:00+00:00"),
        _quote("b", "over", 2.1),
        _quote("b", "under", 1.8),
    ]
    results = [{"source_event_id": "e", "home_goals": 2, "away_goals": 1, "settled_at": "2026-08-11T14:00:00+00:00"}]
    rows = materialize_total_market_records(
        observations, results, horizon_hours=24, max_quote_age_seconds=3600, offer_bookmaker="b", context=_context()
    )
    assert rows[0]["data_status"] == "ABSTAIN_DATA"
    assert rows[0]["best_odds_by_selection"] is None
