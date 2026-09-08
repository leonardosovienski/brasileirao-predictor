"""Goal quotes cannot be selected from another statistic, period or version."""

import copy

import pytest

from brasileirao_predictor.ingest_sofascore import parse_all_odds, parse_ou


def market(name="Match goals", market_id=9, over="4/5", under="1/1"):
    return {
        "marketId": market_id,
        "marketName": name,
        "choiceGroup": "2.5",
        "choices": [
            {"name": "Over", "fractionalValue": over, "initialFractionalValue": "3/4"},
            {"name": "Under", "fractionalValue": under, "initialFractionalValue": "21/20"},
        ],
    }


@pytest.mark.parametrize(
    "name,market_id",
    [
        ("Total corners", 21),
        ("Total cards", 20),
        ("Total goals", 20),
        ("1st half total goals", 9),
        ("2nd half goals", 9),
        ("Home team total goals", 9),
        ("Away team total goals", 9),
        ("Total corners", None),
        ("Corners over/under", None),
    ],
)
def test_other_market_cannot_replace_goal_prices(name, market_id):
    irrelevant = market(name, market_id, "3/1", "1/10")
    assert parse_ou({"markets": [irrelevant, market()]}) == (1.8, 2.0)
    assert parse_ou({"markets": [irrelevant]}) == (None, None)


@pytest.mark.parametrize(
    "field,value",
    [
        ("period", "1st half"),
        ("periodName", "Second half"),
        ("marketPeriod", "extra time"),
        ("periodId", 1),
        ("period", {"id": 1}),
        ("period", "unknown"),
    ],
)
def test_explicit_unrecognized_period_is_not_full_time(field, value):
    other = market()
    other[field] = value
    assert parse_ou({"markets": [other]}) == (None, None)


@pytest.mark.parametrize("period", ["full time", "FT", "match", "90 minutes"])
def test_explicit_full_time_preserved(period):
    full = market()
    full["period"] = period
    assert parse_ou({"markets": [full]}) == (1.8, 2.0)


def test_documented_market_id_without_name_preserved():
    full = market()
    full.pop("marketName")
    assert parse_ou({"markets": [full]}) == (1.8, 2.0)


def test_legacy_goal_name_without_id_preserved():
    full = market("Total goals")
    full.pop("marketId")
    assert parse_ou({"markets": [full]}) == (1.8, 2.0)


def test_opening_and_current_do_not_mix():
    full = market()
    assert parse_ou({"markets": [full]}, initial=True) == (1.75, 2.05)
    assert parse_ou({"markets": [full]}) == (1.8, 2.0)


def test_conflicting_full_time_market_versions_fail_closed_in_any_order():
    first, second = market(), market(over="11/10", under="7/10")
    assert parse_ou({"markets": [first, second]}) == (None, None)
    assert parse_ou({"markets": [second, first]}) == (None, None)


def test_identical_market_duplicates_are_not_conflicts():
    full = market()
    assert parse_ou({"markets": [full, copy.deepcopy(full)]}) == (1.8, 2.0)


def test_duplicate_side_with_conflicting_price_fails_closed():
    full = market()
    full["choices"].append({"name": "Over", "fractionalValue": "11/10"})
    assert parse_ou({"markets": [full]}) == (None, None)


def test_conflicting_group_and_choice_handicap_fails_closed():
    full = market()
    full["choices"][0]["name"] = "Over 3.5"
    assert parse_ou({"markets": [full]}) == (None, None)


@pytest.mark.parametrize("bad", ["nan", "inf", "-1", "0"])
def test_nonfinite_or_nonbettable_quote_cannot_pass(bad):
    full = market()
    full["choices"][0].pop("fractionalValue")
    full["choices"][0]["decimalValue"] = bad
    assert parse_ou({"markets": [full]}) == (None, None)


def test_unrecognized_choice_cannot_contribute_a_goal_side():
    full = market()
    full["choices"][0]["name"] = "Home over"
    assert parse_ou({"markets": [full]}) == (None, None)


def test_normalized_line_table_uses_identical_scope_and_conflict_rules():
    half = market("1st half total goals")
    assert parse_all_odds({"markets": [half]})["ou"] == {}
    full, conflicting = market(), market(over="11/10", under="7/10")
    assert parse_all_odds({"markets": [full, conflicting]})["ou"] == {}
    assert parse_all_odds({"markets": [full]})["ou"] == {2.5: {"Over": 1.8, "Under": 2.0}}
