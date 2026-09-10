import pytest

from brasileirao_predictor.research.residual_dataset import materialize_total_market_records


def quotes():
    return [
        {
            "source_event_id": "e",
            "source": "synthetic",
            "market": "ou2.5",
            "period": "FT",
            "line": 2.5,
            "selection": side,
            "bookmaker": book,
            "decimal_odds": odd,
            "status": "ACTIVE",
            "observed_at": "2024-01-01T11:59:00Z",
            "available_at": "2024-01-01T11:59:01Z",
            "retrieved_at": "2024-01-01T11:59:02Z",
            "odds_captured_at": "2024-01-01T11:59:00Z",
            "kickoff_at": "2024-01-02T12:00:00Z",
        }
        for book, side, odd in [("a", "over", 1.9), ("a", "under", 1.9), ("b", "over", 2.5), ("b", "under", 1.5)]
    ]


def result():
    return [{"source_event_id": "e", "home_goals": 2, "away_goals": 1, "settled_at": "2024-01-02T14:00:00Z"}]


def materialize(rows, outcomes):
    return materialize_total_market_records(
        rows,
        outcomes,
        context={
            "e": {
                "available_at": "2024-01-01T11:58:00Z",
                "xg_form_delta": 0.1,
                "rest_days_delta": 0,
                "current_starters": [str(i) for i in range(11)],
                "expected_starters": [str(i) for i in range(11)],
            }
        },
        offer_bookmaker="b",
    )


def test_offer_book_is_excluded_from_its_own_probability_reference():
    row = materialize(quotes(), result())[0]
    assert row["market_probability"] == pytest.approx(0.5)
    assert row["best_odds_by_selection"] == {"over": 2.5, "under": 1.5}
    assert row["reference_books"] == ["a"]


def test_unfinished_event_is_preserved_without_fabricated_label():
    row = materialize(quotes(), [])[0]
    assert row["outcome"] is None and row["settled_at"] is None


def test_late_receipt_cannot_become_historical_offer():
    rows = quotes()
    for row in rows:
        if row["bookmaker"] == "b":
            row["retrieved_at"] = "2024-01-02T11:00:00Z"
    row = materialize(rows, result())[0]
    assert row["data_status"] == "ABSTAIN_DATA"
    assert row["best_odds_by_selection"] is None


def test_suspension_cannot_resurrect_old_quote():
    rows = quotes()
    rows.append({**rows[-2], "status": "SUSPENDED", "retrieved_at": "2024-01-01T11:59:30Z"})
    row = materialize(rows, result())[0]
    assert row["data_status"] == "ABSTAIN_DATA"


def test_reference_and_offer_must_satisfy_cross_book_clock_skew():
    rows = quotes()
    for row in rows:
        if row["bookmaker"] == "a":
            row.update(
                observed_at="2024-01-01T11:58:01Z",
                available_at="2024-01-01T11:58:02Z",
                retrieved_at="2024-01-01T11:58:03Z",
            )
        else:
            row.update(
                observed_at="2024-01-01T11:59:59Z",
                available_at="2024-01-01T11:59:59Z",
                retrieved_at="2024-01-01T11:59:59Z",
            )
    assert materialize(rows, result())[0]["data_status"] == "ABSTAIN_DATA"


@pytest.mark.parametrize("score", [True, 1.9, -1, "2"])
def test_scores_must_be_nonnegative_integer_counts(score):
    outcomes = result()
    outcomes[0]["home_goals"] = score
    with pytest.raises(ValueError, match="goals"):
        materialize(quotes(), outcomes)
