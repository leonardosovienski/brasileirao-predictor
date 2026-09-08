"""Synthetic checks of economic invariants; no real match data are loaded."""

import math
from copy import deepcopy

import pytest
from economics import (
    Policy,
    evaluate_candidates,
    run_replay,
    select_candidate,
    settle_candidate,
)


def event(identifier=1, **changes):
    value = {
        "id": identifier, "round": 20, "role": "paper_2026_second_turn",
        "kickoff_at": f"2026-08-{identifier:02d}T12:00:00Z",
        "p_1x2": [.55, .20, .25], "p_over25": None, "p_btts": None,
        "odds": {"1x2": [2.0, 4.0, 4.0]}, "home_goals": 1, "away_goals": 0,
        "candidate_frozen2025_hash": "synthetic_frozen_candidate",
    }
    value.update(changes)
    return value


@pytest.mark.parametrize("market,side,index,score", [
    ("1x2", "home", 0, (2, 0)), ("1x2", "draw", 1, (1, 1)), ("1x2", "away", 2, (0, 2)),
    ("ou25", "over", 0, (3, 0)), ("ou25", "under", 1, (2, 0)),
    ("btts", "yes", 0, (1, 1)), ("btts", "no", 1, (1, 0)),
])
def test_known_winning_payouts_include_stake_return_and_extra_cost(market, side, index, score):
    result = settle_candidate({"market": market, "side": side, "side_index": index, "odd": 2.5}, *score)
    assert result["won"] is True
    assert result["gross_profit_units"] == 1.5
    assert result["net_profit_units"] == 1.48


def test_loss_cost_is_charged_too():
    result = settle_candidate({"market": "1x2", "side": "home", "side_index": 0, "odd": 4}, 0, 1)
    assert result["won"] is False
    assert result["net_profit_units"] == -1.02


def test_full_market_required_even_if_available_side_looks_profitable():
    forecast = {"p_1x2": [.55, .2, .25]}
    for quotes in ([2, None, 4], [2, 4], [2, math.nan, 4], [2, math.inf, 4], [2, True, 4]):
        evaluated = evaluate_candidates(forecast, {"1x2": quotes})
        assert evaluated["candidates"] == []
        assert "1x2" in evaluated["rejected_markets"]


def test_odds_must_pass_range_and_market_sum_checks():
    forecast = {"p_1x2": [.55, .2, .25]}
    assert select_candidate(forecast, {"1x2": [2, 4, 4]}) is not None
    assert select_candidate(forecast, {"1x2": [2, 5, 5]}) is None  # Sum below 1.
    assert select_candidate(forecast, {"1x2": [1.1, 3, 3]}) is None  # Sum above 1.3.
    assert select_candidate(forecast, {"1x2": [1.01, 20, 20]}) is None


def test_maximum_net_ev_wins_instead_of_highest_probability():
    forecast = {"p_1x2": [.55, .20, .25], "p_over25": .64, "p_btts": .72}
    odds = {"1x2": [2, 4, 4], "ou25": [1.9, 1.9], "btts": [1.5, 3]}
    chosen = select_candidate(forecast, odds)
    assert chosen["market"] == "ou25"
    assert chosen["side"] == "over"
    assert chosen["predicted_net_ev"] == pytest.approx(.196)


def test_minimum_is_strict_and_maximum_is_inclusive():
    def selected(p):
        return select_candidate({"p_1x2": [p, (1-p)/2, (1-p)/2]}, {"1x2": [2, 4, 4]})
    assert selected(.52) is None
    assert selected(.520001) is not None
    assert selected(.65) is not None
    assert selected(.650001) is None


def test_nonpositive_net_ev_never_selected_even_with_valid_raw_edge():
    assert select_candidate({"p_1x2": [.55, .2, .25]}, {"1x2": [2, 4, 4]}, Policy(cost_per_unit=.20)) is None


def test_ties_have_declared_market_then_side_order():
    forecast = {"p_1x2": [.55, .2, .25], "p_over25": .55, "p_btts": .55}
    odds = {"1x2": [2, 4, 4], "ou25": [2, 2], "btts": [2, 2]}
    assert select_candidate(forecast, odds)["market"] == "1x2"
    tied_sides = select_candidate({"p_1x2": [.37, .37, .26]}, {"1x2": [3, 3, 3]})
    assert tied_sides["side"] == "home"


def test_invalid_probabilities_are_not_repaired_or_used():
    for probabilities in ([.8, .8, .8], [math.nan, .2, .3], [-.1, .5, .6], [True, 0, 0]):
        assert select_candidate({"p_1x2": probabilities}, {"1x2": [2, 4, 4]}) is None


def test_selection_invariant_to_results_and_roles():
    original = event()
    altered = event(home_goals=0, away_goals=8, role="test_2026_first_turn", round=1)
    first = run_replay([original])["decisions"][0]
    second = run_replay([altered])["decisions"][0]
    assert first["candidate"] == second["candidate"]
    assert first["settlement"]["won"] is True
    assert second["settlement"]["won"] is False


def test_pending_result_preserves_candidate_without_fake_loss_or_roi_denominator():
    report = run_replay([event(), event(2, home_goals=None, away_goals=None)])
    assert report["overall"]["selected_bets"] == 2
    assert report["overall"]["settled_bets"] == 1
    assert report["overall"]["unsettled_bets"] == 1
    assert report["overall"]["net_roi"] == pytest.approx(.98)


def test_missing_prices_keep_event_in_coverage_but_do_not_invent_bet():
    report = run_replay([event(odds={})])
    summary = report["overall"]
    assert summary["events"] == 1
    assert summary["no_eligible_bet"] == 1
    assert summary["stake_units"] == 0
    assert summary["net_roi"] is None
    assert summary["curve"] == [{"event_id": None, "cumulative_net_units": 0.0, "drawdown_units": 0.0}]


def test_equity_curve_and_drawdown_include_initial_zero_and_true_date_order():
    # An earlier round postponed behind a later round must follow kickoff order.
    loss_first = event(1, round=21, home_goals=0, away_goals=1)
    win_second = event(2, round=20)
    loss_third = event(3, round=22, home_goals=0, away_goals=1)
    report = run_replay([loss_third, win_second, loss_first])
    summary = report["overall"]
    assert [d["id"] for d in report["decisions"]] == [1, 2, 3]
    assert summary["net_profit_units"] == pytest.approx(-1.06)
    assert summary["max_drawdown_units"] == pytest.approx(1.06)
    assert summary["curve"][1]["drawdown_units"] == pytest.approx(1.02)
    assert summary["net_roi"] == pytest.approx(-1.06 / 3)


def test_role_and_round_totals_reconcile_without_double_betting():
    a = event(1, role="test", round=19, p_over25=.64, odds={"1x2": [2, 4, 4], "ou25": [1.9, 1.9]})
    b = event(2, role="paper", round=20)
    report = run_replay([a, b])
    assert report["decisions"][0]["eligible_sides"] == 2
    assert report["overall"]["settled_bets"] == 2
    assert sum(row["settled_bets"] for row in report["by_role"].values()) == 2
    assert sum(row["net_profit_units"] for row in report["by_round"].values()) == pytest.approx(report["overall"]["net_profit_units"])


def test_inputs_not_mutated():
    inputs = [event()]
    before = deepcopy(inputs)
    run_replay(inputs)
    assert inputs == before


@pytest.mark.parametrize("changes", [
    {"home_goals": 1, "away_goals": None}, {"home_goals": -1}, {"home_goals": 1.5},
    {"home_goals": True}, {"home_goals": math.nan}, {"round": 39}, {"round": True},
    {"kickoff_at": "2026-08-01T12:00:00"}, {"role": None},
])
def test_invalid_event_data_fail_loudly(changes):
    with pytest.raises(ValueError):
        run_replay([event(**changes)])


def test_duplicate_ids_and_mixed_dates_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        run_replay([event(), event()])
    with pytest.raises(ValueError, match="Mixed"):
        run_replay([event(), event(2, kickoff_at=None)])


def test_timezone_normalization_precedes_chronological_accounting():
    early = event(2, kickoff_at="2026-08-01T10:00:00-03:00")
    late = event(1, kickoff_at="2026-08-01T14:00:00Z")
    assert [r["id"] for r in run_replay([late, early])["decisions"]] == [2, 1]
