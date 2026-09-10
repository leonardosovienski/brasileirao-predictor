"""Only synthetic probabilities, coordinates and declared timestamps; no evaluation."""

from datetime import timedelta

import pytest
from test_pit_contextual_features import KICKOFF, _evidence
from test_pit_features_scaffold import evidence

from brasileirao_predictor.research.economic_decision import decide_shadow
from brasileirao_predictor.research.market_residual import ResidualPrediction
from brasileirao_predictor.research.pit_features.contextual import COACH, SURFACE, TRAVEL, materialize_context


@pytest.mark.parametrize(
    "changes",
    [
        {"best_odds": float("nan")},
        {"best_odds": float("inf")},
        {"kelly_fraction": -1},
        {"kelly_fraction": 2},
        {"maximum_stake_units": -1},
        {"maximum_stake_units": float("nan")},
    ],
)
def test_shadow_policy_rejects_nonfinite_or_negative_stake(changes):
    with pytest.raises(ValueError):
        decide_shadow(ResidualPrediction(0.65, 0.58, 0.72, 0.5, 0.6), **{"best_odds": 2.0, **changes})


@pytest.mark.parametrize(
    "prediction",
    [
        ResidualPrediction(float("nan"), 0.6, 0.7, 0.5, 0),
        ResidualPrediction(0.65, 0.9, 0.7, 0.5, 0),
        ResidualPrediction(1.1, 1.0, 1.2, 0.5, 0),
    ],
)
def test_shadow_probability_requires_ordered_finite_bounds(prediction):
    with pytest.raises(ValueError):
        decide_shadow(prediction, best_odds=2.0)


@pytest.mark.parametrize(
    "payload",
    [
        {"origin_lat": 91, "origin_lon": 0, "venue_lat": 0, "venue_lon": 0},
        {"origin_lat": 0, "origin_lon": 181, "venue_lat": 0, "venue_lon": 0},
    ],
)
def test_coordinates_require_physical_bounds(payload):
    with pytest.raises(ValueError):
        materialize_context(_evidence(TRAVEL, payload))


def test_surface_false_string_is_not_true():
    with pytest.raises(ValueError):
        materialize_context(
            _evidence(SURFACE, {"surface": "natural", "home_accustomed": "false", "away_accustomed": False})
        )


@pytest.mark.parametrize(
    "changes",
    [{"home_matches": 1.9}, {"away_matches": True}, {"announced_at": (KICKOFF - timedelta(minutes=30)).isoformat()}],
)
def test_coach_counts_and_publication_must_match_vintage(changes):
    with pytest.raises(ValueError):
        materialize_context(
            _evidence(COACH, {"home_matches": 10, "away_matches": 2, "announced_at": "2026-07-01T12:00:00Z", **changes})
        )


def test_pre_match_evidence_cannot_be_received_after_kickoff():
    with pytest.raises(ValueError):
        evidence(ingested_at=KICKOFF + timedelta(days=1))
