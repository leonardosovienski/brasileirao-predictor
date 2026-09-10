import pytest

from brasileirao_predictor.data.market_anchor import consensus_anchor


def rows():
    return [
        dict(
            source="synthetic",
            source_event_id="e",
            market="ou2.5",
            bookmaker=book,
            odds_captured_at="2020-01-01T12:00:00+00:00",
            line=2.5,
            selection=selection,
            decimal_odds=price,
        )
        for book, over, under in [("a", 1.9, 1.9), ("b", 2.05, 1.8)]
        for selection, price in [("over", over), ("under", under)]
    ]


def test_reference_excludes_offering_book():
    anchor = consensus_anchor(rows(), market="ou2.5", offered_by="b")
    assert anchor["books"] == ["a"]
    assert anchor["fair_probabilities"] == {"over": 0.5, "under": 0.5}
    assert anchor["best_odds"]["over"] == 2.05


def test_reference_does_not_pool_different_capture_vintages():
    data = rows()
    data[-1]["odds_captured_at"] = "2020-01-01T11:00:00+00:00"
    with pytest.raises(ValueError):
        consensus_anchor(data, market="ou2.5")


def test_reference_rejects_conflicting_duplicate_selection():
    data = rows()
    data.append({**data[0], "decimal_odds": 2.1})
    with pytest.raises(ValueError):
        consensus_anchor(data, market="ou2.5")
