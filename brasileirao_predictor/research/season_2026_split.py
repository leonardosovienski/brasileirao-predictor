"""Round-based research split and paper-only eligibility.

This module never reads match results, forecasts, odds or account credentials.
The caller supplies only metadata and gate decisions obtained without future
information. ``PAPER_SIGNAL`` is a simulated signal, never an execution order.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

DECISION_LEAD_HOURS = 1

ROLES = frozenset({"train", "calibration", "test_exploratory", "paper_betting", "out_of_scope"})


def role_for(season: int, round_number: int | None) -> str:
    """Assign the user-approved role using the official round, never its date.

    Delayed games retain their original round. A round is unnecessary for
    2021--2025, whose full seasons have fixed roles. Missing or invalid 2026
    rounds fail closed instead of guessing from kickoff or row position.
    """
    if type(season) is not int:
        raise TypeError("season must be an integer year")
    if 2021 <= season <= 2024:
        return "train"
    if season == 2025:
        return "calibration"
    if season != 2026:
        return "out_of_scope"
    if type(round_number) is not int or not 1 <= round_number <= 38:
        raise ValueError("2026 requires an official integer round from 1 to 38")
    return "test_exploratory" if round_number <= 19 else "paper_betting"


def _aware_utc(value: datetime | str, field: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO timestamp with timezone") from exc
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a datetime or ISO timestamp")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return value.astimezone(UTC)


def eligibility_for_paper(
    role: str,
    kickoff_at: datetime | str | None,
    freeze_at: datetime | str,
    model_frozen: bool,
    price_available: bool,
    criterion_passed: bool,
) -> str:
    """Classify a paper opportunity relative to the supplied freeze timestamp.

    Precedence: non-paper role, unknown kickoff, historical replay, missing
    gate, simulated signal. The decision is exactly one hour before kickoff.
    Decisions at or before the freeze cannot acquire a prospective label
    retrospectively, even when kickoff is later and all gates are true.

    The caller must supply the actual recorded protocol freeze timestamp.
    It must attest that ``price_available`` means a valid price observed no
    later than kickoff minus one hour, that ``model_frozen`` means its frozen
    timestamp is no later than that decision, and that the criterion uses
    only information available then. This function does not certify
    point-in-time provenance or current-time executability.
    An absent candidate or failed economic criterion must set its gate false.
    """
    if not isinstance(role, str) or role not in ROLES:
        raise ValueError("unknown research role")
    for field, value in (
        ("model_frozen", model_frozen),
        ("price_available", price_available),
        ("criterion_passed", criterion_passed),
    ):
        if type(value) is not bool:
            raise TypeError(f"{field} must be an explicit boolean")
    if role != "paper_betting":
        return "OUT_OF_SCOPE"

    freeze = _aware_utc(freeze_at, "freeze_at")
    if kickoff_at is None:
        return "PENDING_KICKOFF"
    kickoff = _aware_utc(kickoff_at, "kickoff_at")
    decision = kickoff - timedelta(hours=DECISION_LEAD_HOURS)
    if decision <= freeze:
        return "REPLAY_ONLY"
    if not (model_frozen and price_available and criterion_passed):
        return "NO_BET"
    return "PAPER_SIGNAL"
