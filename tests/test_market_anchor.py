import pytest

from src.data.market_anchor import consensus_anchor, persist_market_observations, remove_overround


def test_remove_overround_returns_complete_distribution():
    fair = remove_overround({"over": 1.90, "under": 1.90})
    assert fair == pytest.approx({"over": 0.5, "under": 0.5})


def test_remove_overround_rejects_incomplete_or_invalid_market():
    with pytest.raises(ValueError, match="incompleto"):
        remove_overround({"over": 1.9})
    with pytest.raises(ValueError, match="invalida"):
        remove_overround({"over": 1.0, "under": 2.0})


def test_consensus_uses_complete_books_and_best_executable_price():
    rows = [
        {
            "market": "ou2.5",
            "bookmaker": "a",
            "odds_captured_at": "t",
            "line": 2.5,
            "selection": "over",
            "decimal_odds": 1.90,
        },
        {
            "market": "ou2.5",
            "bookmaker": "a",
            "odds_captured_at": "t",
            "line": 2.5,
            "selection": "under",
            "decimal_odds": 1.90,
        },
        {
            "market": "ou2.5",
            "bookmaker": "b",
            "odds_captured_at": "t",
            "line": 2.5,
            "selection": "over",
            "decimal_odds": 2.05,
        },
        {
            "market": "ou2.5",
            "bookmaker": "b",
            "odds_captured_at": "t",
            "line": 2.5,
            "selection": "under",
            "decimal_odds": 1.80,
        },
        {
            "market": "ou2.5",
            "bookmaker": "incomplete",
            "odds_captured_at": "t",
            "line": 2.5,
            "selection": "over",
            "decimal_odds": 9.0,
        },
    ]
    anchor = consensus_anchor(rows, market="ou2.5")
    assert anchor["books"] == ["a", "b"]
    assert anchor["best_odds"] == {"over": 2.05, "under": 1.90}
    assert sum(anchor["fair_probabilities"].values()) == pytest.approx(1.0)
    assert anchor["method"] == "median-proportional-devig/v1"


def test_research_persistence_marks_collection_only(tmp_path):
    path = tmp_path / "market.jsonl"
    row = {
        "source": "the_odds_api",
        "source_event_id": "e",
        "canonical_match_id": "the_odds_api:e",
        "bookmaker": "book",
        "market": "ou2.5",
        "selection": "over",
        "line": 2.5,
        "decimal_odds": 1.95,
        "odds_captured_at": "2026-08-10T10:00:00+00:00",
    }
    assert persist_market_observations(path, [row]) == 1
    assert '"scientific_state": "COLLECTION_ONLY"' in path.read_text(encoding="utf-8")
