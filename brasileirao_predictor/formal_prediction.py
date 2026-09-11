"""Bind caller-declared readiness to canonical teams and an exact event/quote."""

from datetime import UTC, datetime

from .prediction_protocol import PredictionReadinessInput, assess_prediction_readiness


def prepare_context(context: dict, home: str, away: str, match_date: str, resolver) -> dict:
    if set(context) != {"readiness", "quote"}:
        raise ValueError("formal context requires readiness and explicit quote (or null)")
    candidate = PredictionReadinessInput.model_validate(context["readiness"])
    identities = [resolver.resolve(name) for name in (home, away)]
    if any(item.canonical is None for item in identities):
        raise ValueError("formal prediction requires resolved canonical teams")
    if (identities[0].canonical, identities[1].canonical) != (candidate.home, candidate.away):
        raise ValueError("readiness teams differ from resolved prediction teams")
    if candidate.kickoff_at.astimezone(UTC).date().isoformat() != match_date:
        raise ValueError("match_date differs from formal UTC kickoff date")
    report = assess_prediction_readiness(candidate)
    if not report.ready:
        raise ValueError("formal readiness blocked: " + ",".join(item.code for item in report.blockers))
    quote = context["quote"]
    if quote is not None:
        if set(quote) != {"quote_id", "event_id", "captured_at", "market"}:
            raise ValueError("formal quote requires exact quote/event identity and capture time")
        if not isinstance(quote["quote_id"], str) or not quote["quote_id"].strip():
            raise ValueError("quote_id is required")
        if quote["event_id"] != candidate.event_id:
            raise ValueError("quote belongs to another event")
        captured = datetime.fromisoformat(quote["captured_at"].replace("Z", "+00:00"))
        if captured.tzinfo is None or captured.utcoffset() is None or captured > candidate.predicted_at:
            raise ValueError("quote capture must be aware and no later than prediction")
        if candidate.odds_captured_at != captured:
            raise ValueError("quote capture differs from readiness declaration")
    elif candidate.odds_captured_at is not None:
        raise ValueError("readiness declares odds without an exact quote")
    return {
        "schema_version": "formal-prediction-context/1",
        "event_id": candidate.event_id,
        "home_id": candidate.home,
        "away_id": candidate.away,
        "mapping_version": resolver.mapping_version,
        "readiness": candidate.model_dump(mode="json"),
        "assessment": report.model_dump(mode="json"),
        "quote": quote,
    }
