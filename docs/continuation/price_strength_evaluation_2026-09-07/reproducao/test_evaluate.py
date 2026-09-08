"""Synthetic arithmetic checks before the frozen historical run."""

import math
from copy import deepcopy

import pytest
from evaluate import ARMS, MARKETS, accounting, losses, paired_bootstrap


def test_losses_known_multiclass_and_binary_values():
    probabilities = {
        "1x2": {"home": 0.5, "draw": 0.25, "away": 0.25},
        "ou25": {"over": 0.6, "under": 0.4},
        "btts": {"yes": 0.7, "no": 0.3},
    }
    actual = losses(probabilities, {"home_goals": 2, "away_goals": 1})
    assert actual["1x2"]["brier"] == pytest.approx(0.375)
    assert actual["ou25"]["brier"] == pytest.approx(0.16)
    assert actual["btts"]["brier"] == pytest.approx(0.09)
    assert actual["1x2"]["log_loss"] == pytest.approx(-math.log(0.5))


def test_flat_accounting_includes_cost_and_initial_zero_for_drawdown():
    rows = [
        {"bets": {"arm": None}},
        {
            "bets": {
                "arm": {
                    "settlement": {
                        "won": False,
                        "net_profit_units": -1.02,
                        "gross_profit_units": -1,
                    }
                }
            }
        },
        {
            "bets": {
                "arm": {
                    "settlement": {
                        "won": True,
                        "net_profit_units": 1.48,
                        "gross_profit_units": 1.5,
                    }
                }
            }
        },
    ]
    result = accounting(rows, "arm")
    assert result["fixtures"] == 3 and result["bets"] == 2
    assert result["net_roi"] == pytest.approx(0.23)
    assert result["net_profit_units"] == pytest.approx(0.46)
    assert result["net_profit_per_fixture"] == pytest.approx(0.46 / 3)
    assert result["max_drawdown_units"] == pytest.approx(1.02)


def test_weekly_bootstrap_keeps_no_bet_fixtures_and_pairs_arms():
    rows = []
    for kickoff in (
        "2025-01-06T18:00:00+00:00",
        "2025-01-07T18:00:00+00:00",
        "2025-01-13T18:00:00+00:00",
        "2025-01-14T18:00:00+00:00",
    ):
        rows.append(
            {
                "kickoff": kickoff,
                "scores": {
                    arm: {market: {"brier": 0.2, "log_loss": 0.6} for market in MARKETS}
                    for arm in ARMS
                },
                "bets": dict.fromkeys(ARMS),
            }
        )
    for row in (rows[0], rows[2]):
        row["bets"][ARMS[0]] = {"settlement": {"net_profit_units": 1.0}}
    result = paired_bootstrap(rows, replicates=25, seed=17)
    economic = result["economics"][ARMS[0]][ARMS[2]]
    assert economic["delta_profit_per_fixture"] == pytest.approx(0.5)
    assert economic["ci95_weekly_descriptive"] == pytest.approx([0.5, 0.5])
    metric = result["probabilistic"][ARMS[0]][ARMS[2]]["1x2"]["brier"]
    assert metric["mean_delta"] == 0 and metric["ci95_weekly_descriptive"] == [0, 0]
    copied = deepcopy(rows)
    copied.reverse()
    assert paired_bootstrap(copied, replicates=25, seed=17) == result
