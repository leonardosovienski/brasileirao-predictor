from datetime import UTC, datetime, timedelta

import pytest

from brasileirao_predictor.research.structural_edge import (
    MarketSnapshot,
    StructuralEdgePolicy,
    detect_structural_edges,
    power_probabilities,
)

NOW = datetime(2026, 8, 24, 18, tzinfo=UTC)
KICKOFF = NOW + timedelta(hours=1)


def snapshot(bookmaker: str, odds: dict[str, float], **changes: object) -> MarketSnapshot:
    values = {
        "event_id": "canonical-123",
        "bookmaker": bookmaker,
        "market": "match_odds",
        "line": None,
        "captured_at": NOW - timedelta(seconds=30),
        "kickoff_at": KICKOFF,
        "odds": odds,
        "mapping_version": "teams-v4",
    }
    values.update(changes)
    return MarketSnapshot(**values)  # type: ignore[arg-type]


def test_power_devig_is_normalized() -> None:
    probabilities, exponent, margin = power_probabilities([2.0, 3.4, 4.0])
    assert probabilities.sum() == pytest.approx(1.0)
    assert exponent > 1.0
    assert margin > 0.0


@pytest.mark.parametrize("method", ["shin", "power"])
def test_detector_emits_only_locked_shadow_candidates(method: str) -> None:
    result = detect_structural_edges(
        snapshot("Pinnacle", {"home": 2.0, "draw": 3.4, "away": 4.0}),
        snapshot("Soft BR", {"home": 2.35, "draw": 3.2, "away": 3.7}),
        evaluated_at=NOW,
        policy=StructuralEdgePolicy(devig_method=method),  # type: ignore[arg-type]
    )
    assert sum(result.fair_probabilities.values()) == pytest.approx(1.0)
    assert result.capital_gate == "CAPITAL_GATE: LOCKED"
    assert [alert.selection for alert in result.alerts] == ["home"]
    alert = result.alerts[0]
    assert alert.signal == "PAPER_CANDIDATE"
    assert alert.scientific_state == "SHADOW_ONLY"
    assert alert.economic_evidence_eligible is False
    assert alert.capital_gate == "CAPITAL_GATE: LOCKED"


def test_no_alert_below_frozen_ev_threshold() -> None:
    result = detect_structural_edges(
        snapshot("pinnacle", {"yes": 1.9, "no": 1.9}),
        snapshot("soft", {"yes": 1.91, "no": 1.91}),
        evaluated_at=NOW,
    )
    assert result.alerts == ()


def test_stale_reference_fails_closed() -> None:
    with pytest.raises(ValueError, match="stale"):
        detect_structural_edges(
            snapshot("pinnacle", {"yes": 1.9, "no": 1.9}, captured_at=NOW - timedelta(seconds=301)),
            snapshot("soft", {"yes": 2.1, "no": 1.8}),
            evaluated_at=NOW,
        )


@pytest.mark.parametrize("field,value", [("event_id", "other"), ("line", 2.5), ("mapping_version", "teams-v3")])
def test_identity_mismatch_fails_closed(field: str, value: object) -> None:
    with pytest.raises(ValueError, match="must match exactly"):
        detect_structural_edges(
            snapshot("pinnacle", {"yes": 1.9, "no": 1.9}),
            snapshot("soft", {"yes": 2.1, "no": 1.8}, **{field: value}),
            evaluated_at=NOW,
        )


def test_naive_timestamp_and_post_kickoff_are_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        snapshot("pinnacle", {"yes": 1.9, "no": 1.9}, captured_at=datetime(2026, 8, 24, 17))
    with pytest.raises(ValueError, match="pre-kickoff"):
        detect_structural_edges(
            snapshot("pinnacle", {"yes": 1.9, "no": 1.9}),
            snapshot("soft", {"yes": 2.1, "no": 1.8}),
            evaluated_at=KICKOFF,
        )


def test_invalid_odds_and_selection_mismatch_are_rejected() -> None:
    with pytest.raises(ValueError, match="finite and > 1"):
        snapshot("pinnacle", {"yes": 1.0, "no": 1.9})
    with pytest.raises(ValueError, match="must match exactly"):
        detect_structural_edges(
            snapshot("pinnacle", {"yes": 1.9, "no": 1.9}),
            snapshot("soft", {"over": 2.1, "under": 1.8}),
            evaluated_at=NOW,
        )
