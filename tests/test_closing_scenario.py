from decimal import Decimal

import pytest

from brasileirao_predictor.research.price_strength.closing_scenario import freeze_choices, label_winner, settle_frozen


def row(fid="a", day="2025-05-01", offer="2.4"):
    return {
        "event_id": fid,
        "date": day,
        "offer": {"home": offer, "draw": "3", "away": "3"},
        "reference": {"home": "2", "draw": "3.2", "away": "4"},
    }


def label(result="H"):
    return {"home_goals": "1" if result == "H" else "0", "away_goals": "1" if result == "A" else "0", "result": result}


def test_price_stage_refuses_outcome_fields():
    with pytest.raises(ValueError, match="must_not_receive_labels"):
        freeze_choices([{**row(), "result": "H"}])


def test_self_odds_do_not_create_edge():
    source = row()
    source["offer"] = dict(source["reference"])
    assert freeze_choices([source])[0]["selection"] is None


@pytest.mark.parametrize("bad", [None, "", "NaN", "Infinity", "1", True, "garbage"])
def test_missing_price_preserves_universe(bad):
    frozen = freeze_choices([row(offer=bad)])
    assert len(frozen) == 1 and frozen[0]["status"] == "ABSTAIN"


def test_win_returns_principal_but_does_not_count_it_as_profit():
    result = settle_frozen(freeze_choices([row()]), {"a": label()})
    assert Decimal(result["prizes_including_principal"]) == Decimal("2.4")
    assert Decimal(result["net_realized_pnl"]) == Decimal("1.38")
    assert Decimal(result["final_cash"]) == Decimal("101.38")


def test_loss_reconciles_stake_and_separate_cost():
    result = settle_frozen(freeze_choices([row()]), {"a": label("A")})
    assert Decimal(result["net_realized_pnl"]) == Decimal("-1.02")
    assert Decimal(result["final_cash"]) == Decimal("98.98")


def test_no_result_keeps_money_locked_and_roi_undefined():
    result = settle_frozen(freeze_choices([row()]), {})
    assert result["unsettled"] == 1 and result["roi_on_stakes"] is None
    assert Decimal(result["final_cash"]) == Decimal("98.98")
    assert Decimal(result["locked_principal"]) == 1
    assert Decimal(result["final_equity_at_cost"]) == Decimal("99.98")


def test_conflicting_score_does_not_become_void_or_loss():
    result = settle_frozen(freeze_choices([row()]), {"a": {**label(), "result": "A"}})
    assert result["unsettled"] == 1 and result["settled"] == 0


def test_cannot_recycle_same_day_winnings_to_fund_second_pick():
    frozen = freeze_choices([row("a"), row("b")])
    result = settle_frozen(frozen, {"a": label(), "b": label()}, bankroll="1.02")
    assert result["conditional_bets"] == 1 and result["abstentions"] == 1


def test_next_day_can_use_previous_days_settled_balance():
    frozen = freeze_choices([row("a"), row("b", day="2025-05-02")])
    result = settle_frozen(frozen, {"a": label(), "b": label()}, bankroll="1.02")
    assert result["conditional_bets"] == 2


def test_dates_order_and_duplicate_identity():
    assert [r["event_id"] for r in freeze_choices([row("b", day="2025-05-02"), row()])] == ["a", "b"]
    with pytest.raises(ValueError, match="duplicate_event"):
        freeze_choices([row(), row()])


def test_protected_years_are_excluded():
    with pytest.raises(ValueError, match="outside_frozen"):
        freeze_choices([row(day="2026-05-01")])


@pytest.mark.parametrize("result", ["H", "D", "A"])
def test_consistent_result_codes(result):
    assert label_winner(label(result)) == {"H": "home", "D": "draw", "A": "away"}[result]
