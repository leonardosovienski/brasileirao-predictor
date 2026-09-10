from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from brasileirao_predictor.research.structural_edge import (
    MarketSnapshot,
    StructuralEdgePolicy,
    detect_structural_edges,
    power_probabilities,
)

NOW = datetime(2020, 1, 1, 12, tzinfo=UTC)


def snapshot(book, **changes):
    base = MarketSnapshot(
        "synthetic",
        book,
        "match_odds",
        None,
        NOW - timedelta(seconds=1),
        NOW + timedelta(hours=1),
        {"home": 2.0, "draw": 3.4, "away": 4.0},
        "synthetic-v1",
    )
    return replace(base, **changes)


def test_stale_offer_cannot_be_compared_with_fresh_reference():
    with pytest.raises(ValueError, match="stale"):
        detect_structural_edges(
            snapshot("pinnacle"), snapshot("soft", captured_at=NOW - timedelta(seconds=301)), evaluated_at=NOW
        )


@pytest.mark.parametrize(
    "changes",
    [
        dict(devig_method="typo"),
        dict(max_reference_staleness_seconds=float("nan")),
        dict(max_reference_staleness_seconds=True),
        dict(reference_book=" "),
    ],
)
def test_invalid_policy_is_not_silently_interpreted(changes: dict[str, Any]):
    with pytest.raises(ValueError):
        StructuralEdgePolicy(**changes)


def test_snapshot_does_not_change_when_callers_mutate_original_odds():
    odds = {"home": 2.0, "draw": 3.4, "away": 4.0}
    value = snapshot("pinnacle", odds=odds)
    odds["home"] = float("nan")
    assert value.odds["home"] == 2.0
    with pytest.raises(TypeError):
        cast(Any, value.odds)["home"] = 0.0


def test_power_devig_brackets_valid_high_margin_prices():
    probabilities, exponent, margin = power_probabilities([1.0001, 1.0001])
    assert probabilities.tolist() == pytest.approx([0.5, 0.5])
    assert exponent > 20 and margin > 0


def test_nonfinite_market_line_is_rejected():
    with pytest.raises(ValueError):
        snapshot("pinnacle", line=float("nan"))
