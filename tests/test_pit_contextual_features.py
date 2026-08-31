from datetime import UTC, datetime, timedelta

import pytest

from brasileirao_predictor.research.pit_features import PITFeatureEvidence
from brasileirao_predictor.research.pit_features.contextual import COACH, REST, SURFACE, TRAVEL, materialize_context

KICKOFF = datetime(2026, 8, 28, 22, tzinfo=UTC)


def _evidence(declaration, payload):
    return PITFeatureEvidence(
        event_id="fixture",
        feature_family=declaration.feature_family,
        declaration_version=declaration.version,
        source="versioned-test-source",
        source_record_id="record-v1",
        observed_at=KICKOFF - timedelta(hours=3),
        available_at=KICKOFF - timedelta(hours=2),
        ingested_at=KICKOFF - timedelta(hours=1),
        kickoff_at=KICKOFF,
        payload=payload,
    )


def test_rest_is_strictly_pre_match() -> None:
    result = materialize_context(
        _evidence(
            REST,
            {
                "home_previous_kickoff": (KICKOFF - timedelta(days=4)).isoformat(),
                "away_previous_kickoff": (KICKOFF - timedelta(days=2)).isoformat(),
            },
        )
    )
    assert result["rest_days_delta"] == 2.0


def test_travel_surface_and_coach_materialize_deterministically() -> None:
    travel = materialize_context(
        _evidence(TRAVEL, {"origin_lat": -30.03, "origin_lon": -51.23, "venue_lat": -3.73, "venue_lon": -38.52})
    )
    assert travel["away_travel_km"] > 3000
    surface = materialize_context(
        _evidence(SURFACE, {"surface": "synthetic", "home_accustomed": True, "away_accustomed": False})
    )
    assert surface == {"synthetic_surface": True, "surface_familiarity_delta": 1}
    coach = materialize_context(
        _evidence(COACH, {"home_matches": 10, "away_matches": 2, "announced_at": "2026-07-01T12:00:00Z"})
    )
    assert coach["coach_tenure_delta"] == 8


def test_future_previous_match_fails_closed() -> None:
    evidence = _evidence(
        REST,
        {
            "home_previous_kickoff": KICKOFF.isoformat(),
            "away_previous_kickoff": (KICKOFF - timedelta(days=2)).isoformat(),
        },
    )
    with pytest.raises(ValueError, match="strictly before"):
        materialize_context(evidence)
