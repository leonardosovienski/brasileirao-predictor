"""Deterministic PIT materializers for Brazilian schedule context."""

import math
from datetime import datetime
from numbers import Integral, Real

from brasileirao_predictor.research.pit_features.contracts import FeatureDeclaration, PITFeatureEvidence

REST = FeatureDeclaration(
    feature_family="rest",
    version="pit-rest/1",
    mechanism_ex_ante="Days since each club's strictly previous kickoff proxy recovery and schedule congestion.",
    required_source_fields=("home_previous_kickoff", "away_previous_kickoff"),
    output_contract=("home_rest_days", "away_rest_days", "rest_days_delta"),
    provenance_policy=(
        "Previous kickoffs must originate from the immutable schedule vintage available before prediction."
    ),
)
TRAVEL = FeatureDeclaration(
    feature_family="travel",
    version="pit-travel/1",
    mechanism_ex_ante="Great-circle distance from the visitor origin to the match venue proxies travel burden.",
    required_source_fields=("origin_lat", "origin_lon", "venue_lat", "venue_lon"),
    output_contract=("away_travel_km",),
    provenance_policy="Coordinates and venue assignment must carry an effective date no later than available_at.",
)
SURFACE = FeatureDeclaration(
    feature_family="surface",
    version="pit-surface/1",
    mechanism_ex_ante=(
        "Pre-declared synthetic versus natural surface may interact with team familiarity before kickoff."
    ),
    required_source_fields=("surface", "home_accustomed", "away_accustomed"),
    output_contract=("synthetic_surface", "surface_familiarity_delta"),
    provenance_policy="Surface registry version must be effective and observable strictly before the fixture kickoff.",
)
COACH = FeatureDeclaration(
    feature_family="coach_tenure",
    version="pit-coach-tenure/1",
    mechanism_ex_ante="Matches completed under the announced coach proxy tactical continuity without future results.",
    required_source_fields=("home_matches", "away_matches", "announced_at"),
    output_contract=("home_coach_matches", "away_coach_matches", "coach_tenure_delta"),
    provenance_policy="Coach announcements and prior-match counts must use only versions published before kickoff.",
)


def _dt(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("context timestamp must be timezone-aware")
    return parsed


def materialize_context(evidence: PITFeatureEvidence) -> dict[str, float | int | bool]:
    payload = evidence.payload
    if evidence.feature_family == "rest":
        evidence.assert_matches(REST)
        home = (evidence.kickoff_at - _dt(payload["home_previous_kickoff"])).total_seconds() / 86400
        away = (evidence.kickoff_at - _dt(payload["away_previous_kickoff"])).total_seconds() / 86400
        if home <= 0 or away <= 0:
            raise ValueError("previous kickoff must be strictly before current kickoff")
        return {"home_rest_days": home, "away_rest_days": away, "rest_days_delta": home - away}
    if evidence.feature_family == "travel":
        evidence.assert_matches(TRAVEL)
        if any(
            isinstance(payload[name], bool) or not isinstance(payload[name], Real)
            for name in TRAVEL.required_source_fields
        ):
            raise ValueError("travel coordinates must be numbers")
        lat1, lon1, lat2, lon2 = (float(payload[name]) for name in TRAVEL.required_source_fields)
        if not all(math.isfinite(value) for value in (lat1, lon1, lat2, lon2)):
            raise ValueError("travel coordinates must be finite")
        if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180):
            raise ValueError("travel coordinates are outside latitude/longitude bounds")
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        a = min(1.0, max(0.0, a))  # Only floating-point roundoff after validating physical bounds.
        return {"away_travel_km": 6371.0088 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))}
    if evidence.feature_family == "surface":
        evidence.assert_matches(SURFACE)
        surface = str(payload["surface"]).casefold()
        if surface not in {"natural", "synthetic"}:
            raise ValueError("surface must be natural or synthetic")
        home, away = payload["home_accustomed"], payload["away_accustomed"]
        if not isinstance(home, bool) or not isinstance(away, bool):
            raise ValueError("surface familiarity must be boolean")
        return {"synthetic_surface": surface == "synthetic", "surface_familiarity_delta": int(home) - int(away)}
    if evidence.feature_family == "coach_tenure":
        evidence.assert_matches(COACH)
        home, away = payload["home_matches"], payload["away_matches"]
        if any(isinstance(value, bool) or not isinstance(value, Integral) for value in (home, away)):
            raise ValueError("coach tenure must use integer counts")
        home, away = int(home), int(away)
        if min(home, away) < 0 or _dt(payload["announced_at"]) > evidence.available_at:
            raise ValueError("coach tenure inputs violate point-in-time constraints")
        return {"home_coach_matches": home, "away_coach_matches": away, "coach_tenure_delta": home - away}
    raise ValueError(f"unsupported contextual feature family: {evidence.feature_family}")
