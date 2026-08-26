from __future__ import annotations

import pytest

from scripts import research_residual_diagnostics as d


def test_losses_are_zero_for_certain_correct_prediction() -> None:
    assert d._losses([0.0, 0.0, 1.0], 2) == pytest.approx((0.0, 0.0, 0.0))


def test_confidence_bins_have_frozen_boundaries() -> None:
    assert [d._confidence_bin(value) for value in (0.39, 0.40, 0.50, 0.60)] == [
        "lt_40",
        "40_50",
        "50_60",
        "ge_60",
    ]


def test_market_home_bins_have_frozen_boundaries() -> None:
    assert [d._market_home_bin(value) for value in (0.34, 0.35, 0.45, 0.55)] == [
        "lt_35",
        "35_45",
        "45_55",
        "ge_55",
    ]
