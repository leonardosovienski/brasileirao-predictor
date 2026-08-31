from brasileirao_scripts.research_ou25_annual_2021_2026 import _annual_baseline, _valid_price_pair


def _row(pair=(2.0, 2.0), actual=True):
    return {
        "event_id": "1",
        "kickoff_at": "2026-01-01T00:00:00Z",
        "season": "2026",
        "p_over": 0.6,
        "actual_over": actual,
        "offered_odds_ou25": pair,
        "closing_odds_ou25": (1.8, 2.2),
    }


def test_price_quality_gate_rejects_placeholder_pair():
    assert not _valid_price_pair((51.0, 1.002))
    assert _valid_price_pair((2.0, 1.9))


def test_annual_baseline_settles_one_unit_and_devigged_clv():
    picks, metrics = _annual_baseline([_row()], "2026", 7)
    assert len(picks) == 1
    assert picks[0]["side"] == "over"
    assert picks[0]["profit"] == 1.0
    assert picks[0]["clv"] == 2.0 * (1 / 1.8) / (1 / 1.8 + 1 / 2.2) - 1
    assert metrics["profit_units"] == 1.0


def test_annual_baseline_drops_invalid_prices():
    picks, metrics = _annual_baseline([_row((51.0, 1.002))], "2026", 7)
    assert picks == []
    assert metrics["n"] == 0
