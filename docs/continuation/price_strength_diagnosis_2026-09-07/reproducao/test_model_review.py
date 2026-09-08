"""Synthetic demonstrations of structural properties, with no economic replay."""

import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from brasileirao_predictor.research.price_strength.dynamic_xg import (
    DynamicXGConfig,
    Fixture,
    XGObservation,
    _probabilities,
    forecast,
)
from scipy.stats import poisson

CONFIG = DynamicXGConfig()
KICKOFF = datetime(2035, 6, 1, 18, tzinfo=UTC)
DECISION = KICKOFF - timedelta(hours=1)
TARGET = Fixture("target", "Synthetic A", "Synthetic B", KICKOFF)


def histories():
    rows = []
    for i in range(5):
        kickoff = KICKOFF - timedelta(days=7 * (i + 1))
        for role in ("home", "away"):
            rows.append(
                XGObservation(
                    f"{role}-{i}",
                    "Synthetic A" if role == "home" else f"Other home {i}",
                    f"Other away {i}" if role == "home" else "Synthetic B",
                    kickoff,
                    kickoff + timedelta(hours=2),
                    kickoff + timedelta(hours=3),
                    1.5,
                    1.2,
                )
            )
    return rows


def test_attack_change_is_attenuated_by_prior_then_arithmetic_average():
    rows = histories()
    base = forecast(rows, TARGET, DECISION, CONFIG)
    changed = [
        replace(row, home_xg=row.home_xg + 1)
        if row.home_team == TARGET.home_team
        else row
        for row in rows
    ]
    prediction = forecast(changed, TARGET, DECISION, CONFIG)
    weight_sum = math.fsum(
        0.5
        ** ((DECISION - row.kickoff).total_seconds() / 86400 / CONFIG.half_life_days)
        for row in rows
        if row.home_team == TARGET.home_team
    )
    expected_change = 0.5 * weight_sum / (CONFIG.prior_weight + weight_sum)
    assert prediction.lambda_home - base.lambda_home == pytest.approx(expected_change)
    assert 0 < expected_change < 5 / 14


def test_changing_historical_opponent_names_cannot_adjust_schedule_strength():
    rows = histories()
    renamed = [
        replace(row, away_team=f"Different historical opponent {i}")
        if row.home_team == TARGET.home_team
        else replace(row, home_team=f"Different historical opponent {i}")
        for i, row in enumerate(rows)
    ]
    assert forecast(rows, TARGET, DECISION, CONFIG) == forecast(
        renamed, TARGET, DECISION, CONFIG
    )


def test_old_counts_remain_eligible_even_when_weights_have_decayed_to_priors():
    rows = [replace(row, home_xg=5, away_xg=5) for row in histories()]
    distant_kickoff = KICKOFF.replace(year=2135)
    distant_target = replace(TARGET, kickoff=distant_kickoff)
    result = forecast(
        rows, distant_target, distant_kickoff - timedelta(hours=1), CONFIG
    )
    assert result.eligible and result.n_home == result.n_away == 5
    assert result.lambda_home == pytest.approx(CONFIG.prior_home_xg, abs=1e-12)
    assert result.lambda_away == pytest.approx(CONFIG.prior_away_xg, abs=1e-12)


def test_skellam_result_matches_explicit_independent_poisson_grid():
    home, away = 1.7, 0.8
    result = _probabilities(home, away)["1x2"]
    grid = {
        (h, a): float(poisson.pmf(h, home) * poisson.pmf(a, away))
        for h in range(40)
        for a in range(40)
    }
    assert result["home"] == pytest.approx(
        math.fsum(p for (h, a), p in grid.items() if h > a), abs=1e-12
    )
    assert result["draw"] == pytest.approx(
        math.fsum(p for (h, a), p in grid.items() if h == a), abs=1e-12
    )
    assert result["away"] == pytest.approx(
        math.fsum(p for (h, a), p in grid.items() if h < a), abs=1e-12
    )
