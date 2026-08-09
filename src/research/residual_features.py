"""Point-in-time feature extraction for market-residual research."""

from __future__ import annotations

import math
import statistics as st
from collections import defaultdict
from datetime import datetime
from typing import Any

FEATURE_NAMES = (
    "book_dispersion",
    "book_count_log",
    "hours_to_kickoff_log",
    "lineup_completeness",
    "starter_change_share",
    "xg_form_delta",
    "rest_days_delta",
)


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def lineup_state_asof(rows: list[dict[str, Any]], *, event_id: str, asof: str) -> dict[str, set[str]]:
    cutoff = _utc(asof)
    vintages: dict[str, tuple[datetime, str, list[dict[str, Any]]]] = {}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if str(row.get("source_event_id")) != str(event_id):
            continue
        published = _utc(str(row["published_at"]))
        if published <= cutoff:
            grouped[(str(row.get("team_id")), str(row.get("content_hash")))].append(row)
    for (team_id, content_hash), items in grouped.items():
        published = max(_utc(str(item["published_at"])) for item in items)
        if team_id not in vintages or published > vintages[team_id][0]:
            vintages[team_id] = (published, content_hash, items)
    return {
        team_id: {str(item["player_id"]) for item in items if item.get("role") == "starter"}
        for team_id, (_, _, items) in vintages.items()
    }


def build_residual_features(
    *,
    book_probabilities: list[float],
    captured_at: str,
    kickoff_at: str,
    current_starters: set[str] | None = None,
    expected_starters: set[str] | None = None,
    xg_form_delta: float = 0.0,
    rest_days_delta: float = 0.0,
) -> list[float]:
    if len(book_probabilities) < 1 or any(not 0 < p < 1 for p in book_probabilities):
        raise ValueError("book probabilities are invalid")
    hours = (_utc(kickoff_at) - _utc(captured_at)).total_seconds() / 3600.0
    if hours <= 0:
        raise ValueError("features must be observed before kickoff")
    current, expected = current_starters or set(), expected_starters or set()
    lineup_completeness = min(1.0, len(current) / 11.0)
    starter_change_share = len(current.symmetric_difference(expected)) / 22.0 if expected else 0.0
    return [
        st.pstdev(book_probabilities),
        math.log1p(len(book_probabilities)),
        math.log1p(hours),
        lineup_completeness,
        starter_change_share,
        float(xg_form_delta),
        float(rest_days_delta),
    ]
