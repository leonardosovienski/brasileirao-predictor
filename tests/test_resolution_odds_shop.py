"""The diagnostic price display must not manufacture freshness or approval."""

import copy
from datetime import UTC, datetime, timedelta

import pytest

from brasileirao_scripts import odds_shop as shop


def event():
    return {
        "home_team": "Home",
        "away_team": "Away",
        "commence_time": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "bookmakers": [
            {
                "key": "book",
                "title": "Book",
                "last_update": datetime.now(UTC).isoformat(),
                "markets": [
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "price": 2.5, "point": 2.5},
                            {"name": "Under", "price": 1.8, "point": 2.5},
                        ],
                    }
                ],
            }
        ],
    }


@pytest.mark.parametrize("clock", [None, "invalid", "2026-01-01T00:00:00", "2099-01-01T00:00:00+00:00"])
def test_unknown_invalid_or_future_clock_is_not_fresh(clock):
    assert shop._stale({"last_update": clock}, 900) is True


@pytest.mark.parametrize("price", [float("nan"), float("inf"), True, 0.9])
def test_bad_prices_cannot_become_consensus(price):
    sample = event()
    sample["bookmakers"][0]["markets"][0]["outcomes"][0]["price"] = price
    assert shop.consensus(sample, "totals", point=2.5, max_stale_s=900) == {}


def test_duplicate_books_do_not_manufacture_consensus_strength():
    sample = event()
    sample["bookmakers"] *= 4
    result = shop.consensus(sample, "totals", point=2.5, max_stale_s=900)
    assert result == {} or result["Over"]["n_books"] == 1


def test_incomplete_market_is_excluded():
    sample = event()
    sample["bookmakers"][0]["markets"][0]["outcomes"][1]["name"] = "Over"
    assert shop.consensus(sample, "totals", point=2.5, max_stale_s=900) == {}


def test_diagnostic_output_does_not_call_unproven_window_validated(monkeypatch, capsys):
    sample = event()
    for index in range(1, 4):
        book = copy.deepcopy(sample["bookmakers"][0])
        book["key"] = f"book{index}"
        sample["bookmakers"].append(book)
    monkeypatch.setattr(
        shop, "model_probs_for", lambda *args: {"home": 0.5, "draw": 0.2, "away": 0.3, "over25": 0.5, "under25": 0.5}
    )
    shop.analyze([sample], None, 0.03, max_stale_s=900)
    shop._footer(0.03)
    output = capsys.readouterr().out
    assert "JANELA VALIDADA" not in output
    assert "bet_log add" not in output
    assert "zona confiavel" not in output


@pytest.mark.parametrize("clock", [None, "bad", "2026-01-01T00:00:00"])
def test_missing_kickoff_cannot_be_treated_as_future(clock):
    assert shop._started({"commence_time": clock}) is True
