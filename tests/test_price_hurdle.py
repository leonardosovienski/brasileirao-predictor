"""Economic regression fixtures; all fabricated and independent of cohorts."""

from copy import deepcopy

import pytest

from brasileirao_predictor.research.price_strength.price_hurdle import (
    aggregate_price_hurdle,
    audit_legacy_2025,
    break_even_decimal,
)


def _row(**extra):
    return {
        "event_id": "synthetic",
        "date": "2025-04-01",
        "kickoff": "2025-04-01T20:00:00+00:00",
        "tournament": "Brasileirão Série A",
        "home": "synthetic-home",
        "away": "synthetic-away",
        "odds": {"1x2": [2.0, 3.0, 4.0]},
        **extra,
    }


def test_break_even_matches_two_branch_cash_flow_with_commission():
    p, cost, commission = 0.4, 0.02, 0.05
    odd = break_even_decimal(p, cost_per_unit=cost, commission_on_profit=commission)
    win_net = (odd - 1) * (1 - commission) - cost
    loss_net = -1 - cost
    assert p * win_net + (1 - p) * loss_net == pytest.approx(0, abs=1e-12)
    assert odd == pytest.approx(2.631578947368421)


@pytest.mark.parametrize("odds,sign", [([2, 3, 4], "positive"), ([3, 3, 3], "zero"), ([4, 4, 4], "negative")])
def test_own_price_identity_preserves_sign_and_never_claims_execution(odds, sign):
    result = aggregate_price_hurdle(odds)
    assert result["margin_sign"] == sign
    for side, probability in result["probabilities"].items():
        assert probability * result["aggregate_odds"][side] - 1 == pytest.approx(result["own_price_gross_ev"])
        assert probability * result["break_even_odds_scenario"][side] - 1 - 0.02 == pytest.approx(0, abs=1e-12)
    assert result["executable"] is False


def test_exact_hurdle_separates_embedded_margin_from_additional_cost():
    result = aggregate_price_hurdle([2, 3, 4])
    assert result["overround_sum"] == pytest.approx(13 / 12)
    assert result["relative_price_uplift_to_break_even"] == pytest.approx(0.105)
    assert result["break_even_odds_scenario"]["home"] == pytest.approx(2.21)


@pytest.mark.parametrize(
    "odds",
    [None, [2, 3], [2, 3, 4, 5], [True, 3, 4], [1, 3, 4], [float("nan"), 3, 4], [float("inf"), 3, 4], [10**1000, 3, 4]],
)
def test_invalid_prices_do_not_enter_numeric_coverage(odds):
    report = audit_legacy_2025([_row(odds={"1x2": odds})])
    assert report["summary"]["universe_matches"] == 1
    assert report["summary"]["numeric_complete_vectors"] == 0
    assert report["summary"]["abstentions"] == 1
    assert report["summary"]["opportunities"] is None
    assert report["abstention_portfolio"]["roi_on_stakes"] is None


@pytest.mark.parametrize(
    "p,c,r", [(0, 0.02, 0), (1.1, 0.02, 0), (True, 0.02, 0), (0.4, -1, 0), (0.4, float("nan"), 0), (0.4, 0.02, 1)]
)
def test_invalid_probability_and_cost_fail_closed(p, c, r):
    with pytest.raises(ValueError):
        break_even_decimal(p, cost_per_unit=c, commission_on_profit=r)


def test_future_rows_are_excluded_before_outcomes_or_odds_are_used():
    future = {"date": "2026-04-01", "result": object(), "odds": object()}
    report = audit_legacy_2025([future, _row(result=object())])
    assert report["summary"]["universe_matches"] == 1
    assert report["labels_accessed"] is False


def test_results_do_not_affect_any_output_and_inputs_are_unchanged():
    first = _row(result={"home": 7, "away": 0})
    original = deepcopy(first)
    report = audit_legacy_2025([first])
    second = _row(result={"home": 0, "away": 7})
    assert report == audit_legacy_2025([second])
    assert first == original
    assert report["summary"]["executable_price_pairs"] == 0
    assert report["summary"]["opportunities"] is None
    assert report["abstention_portfolio"]["total_business_net_result"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        {"event_id": True},
        {"home": "synthetic-away"},
        {"kickoff": "2026-04-01T20:00:00+00:00"},
        {"kickoff": "2025-04-02T20:00:00+00:00"},
        {"kickoff": "2025-04-01T20:00:00"},
        {"bookmaker": "new-schema"},
        {"tournament": "other-league"},
    ],
)
def test_identity_time_and_schema_conflicts_abort(mutation):
    with pytest.raises(ValueError):
        audit_legacy_2025([_row(**mutation)])


def test_duplicate_event_is_not_an_independent_observation():
    with pytest.raises(ValueError, match="duplicate_event_identity"):
        audit_legacy_2025([_row(), _row()])


def test_sensitivity_holds_universe_and_prices_fixed():
    report = audit_legacy_2025([_row(), _row(event_id="missing", odds=None)])
    scenarios = report["summary"]["relative_price_uplift_scenarios"]
    assert scenarios["0.0"]["n"] == scenarios["0.05"]["n"] == 1
    assert scenarios["0.05"]["median"] - scenarios["0.0"]["median"] == pytest.approx(13 / 12 * 0.05)
    assert report["summary"]["universe_matches"] == 2
    assert report["summary"]["abstentions"] == 2
