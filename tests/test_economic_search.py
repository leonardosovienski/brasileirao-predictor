"""Financial and temporal invariants for the frozen public-data scenario."""

from dataclasses import replace
from datetime import date, timedelta
from fractions import Fraction

import pytest

from brasileirao_predictor.research.price_strength.economic_search import (
    Match,
    arbitrage,
    ledger,
    predict,
    probabilities,
    read_matches,
    select,
)


def fixture(day=date(2020, 1, 1), home="A", away="B", goals=(1, 0)):
    return Match(2020, day, home, away, goals, "H", (2.0, 3.0, 4.0), (2.0, 3.0, 4.0))


@pytest.mark.parametrize("prices", [(3.3, 3.3, 3.3), (2.4, 4.0, 4.0), (1.8, 3.3, 4.2)])
def test_arbitrage_all_outcomes_and_partial_risk(prices):
    result = arbitrage(prices)
    adjusted = [1 + (Fraction(str(o)) - 1) * Fraction(99, 100) for o in prices]
    total_inverse = sum(1 / o for o in adjusted)
    returned = 1 / total_inverse
    assert sum(result["stakes"]) == pytest.approx(1)
    assert result["returns_by_outcome"] == pytest.approx([float(returned)] * 3)
    assert result["net"] == pytest.approx(float(returned - 1 - Fraction(2, 100)))
    assert len(result["partial_fill_cases"]) == 6
    assert all(c["worst_net"] < 0 for c in result["partial_fill_cases"])


def test_poisson_probability_mass_and_symmetry():
    p = probabilities(1.4, 1.4)
    assert sum(p) == pytest.approx(1)
    assert p[0] == pytest.approx(p[2])
    assert probabilities(2, 1)[0] == pytest.approx(probabilities(1, 2)[2])
    with pytest.raises(ValueError):
        probabilities(float("nan"), 1)


def test_forecast_excludes_target_future_and_recent_results_and_all_odds():
    target = fixture()
    history = [replace(target, day=target.day - timedelta(days=10 + i), goals=(i % 3, i % 2)) for i in range(310)]
    expected = predict(history, target)
    assert expected is not None
    forbidden = [replace(target, day=target.day + timedelta(days=i), goals=(20, 0)) for i in range(-6, 5)]
    changed_odds = [replace(m, pinnacle=(30.0, 50.0, 2.0), maximum=(100.0, 80.0, 40.0)) for m in history]
    assert predict(changed_odds + forbidden, replace(target, goals=(0, 30), result="A")) == expected
    assert expected["latest_training_day"] == (target.day - timedelta(days=10)).isoformat()


def test_season_filter_precedes_all_other_fields():
    source = b"Season,Date,Home,Away,HG,AG,Res\n2026,DO_NOT_PARSE,,,,,\n"
    matches, report = read_matches(source)
    assert matches == []
    assert report["excluded_before_field_interpretation"] == 1


def test_duplicate_identity_rejected_and_bad_label_preserved():
    source = b"Season,Date,Home,Away,HG,AG,Res\n2020,01/01/2020,A,B,2,0,A\n"
    matches, _ = read_matches(source)
    assert matches[0].result is None
    with pytest.raises(ValueError, match="duplicate"):
        read_matches(source + b"2020,02/01/2020,A,B,2,0,H\n")


def test_same_day_winnings_cannot_fund_later_fills():
    rows = [
        {
            "key": str(i),
            "date": "2020-01-01",
            "season": 2020,
            "home": str(i),
            "away": "B",
            "pinnacle": (2.0, 3.0, 4.0),
            "prediction": {"model": (0.8, 0.1, 0.1)},
            "result": "H",
        }
        for i in range(101)
    ]
    result = ledger(rows, "model")
    assert sum(r["stake"] for r in result) == 98
    assert sum(r["net"] for r in result) == pytest.approx(98 * 0.98)
    assert result[-1]["cash_after_day"] == pytest.approx(100 + 98 * 0.98)
    assert result[-1]["day_exposure"] == 98
    assert result[-1]["reason"] == "insufficient_unreserved_bankroll"


def test_unsettled_never_becomes_void_or_zero_return():
    rows = [
        {
            "key": "a",
            "date": "2020-01-01",
            "season": 2020,
            "home": "A",
            "away": "B",
            "pinnacle": (2.0, 3.0, 4.0),
            "prediction": {"model": (0.8, 0.1, 0.1)},
            "result": None,
        }
    ]
    result = ledger(rows, "model")[0]
    assert result["status"] == "unsettled"
    assert result["net"] is None and result["return"] is None
    assert result["cash_after_day"] == pytest.approx(98.98)
    assert result["unsettled_stakes"] == 1


def test_normalizing_own_book_does_not_manufacture_edge():
    o = (2.0, 3.0, 4.0)
    s = sum(1 / x for x in o)
    p = (1 / o[0] / s, 1 / o[1] / s, 1 / o[2] / s)
    assert select(p, o) is None
