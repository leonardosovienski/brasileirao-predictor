"""Point-in-time rule for match results: when a final score may be used as information.

A result exists only after the match ends. The project rule (qualification contract,
FROZEN_PARAMETERS temporal_contract) is conservative: a result is available at
``kickoff + RESULT_LATENCY`` (180 min = 90 + half-time + stoppage + delays + publication).
Without a kickoff time, the whole UTC date is assumed and the result is available at the
next day's 03:00 UTC (worst case: kickoff 23:59 UTC).

Every walk-forward fit must use ``result_available_at(...) < horizon``; ``kickoff < horizon``
lets a match that is still being played leak its final score (BR-F004).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

RESULT_LATENCY = timedelta(minutes=180)
DATE_ONLY_AVAILABILITY = timedelta(days=1, hours=3)


def aware_utc(value: datetime) -> datetime:
    """Normalize an aware datetime to UTC; a naive one is refused, never guessed."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must carry an explicit timezone")
    return value.astimezone(UTC)


def result_available_at(kickoff: datetime | None, match_date: str | date | None = None) -> datetime:
    """Earliest instant the final score of a match may be used as information."""
    if kickoff is not None:
        return aware_utc(kickoff) + RESULT_LATENCY
    if match_date is None:
        raise ValueError("a match without kickoff needs its UTC date")
    day = match_date if isinstance(match_date, date) else date.fromisoformat(str(match_date)[:10])
    return datetime(day.year, day.month, day.day, tzinfo=UTC) + DATE_ONLY_AVAILABILITY


def observation_available_at(observation: dict) -> datetime:
    """Availability of a prequential observation (``kickoff`` aware; ``has_real_kickoff`` optional).

    Observations built from a date without time carry ``has_real_kickoff = False`` and a
    midnight kickoff; their availability is the conservative date-only rule.
    """
    if observation.get("has_real_kickoff", True):
        return result_available_at(observation["kickoff"])
    return result_available_at(None, aware_utc(observation["kickoff"]).date())


__all__ = ["DATE_ONLY_AVAILABILITY", "RESULT_LATENCY", "aware_utc", "observation_available_at", "result_available_at"]
