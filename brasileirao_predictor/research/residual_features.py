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
    if any("schema_version" in row for row in rows):
        # Explicit successor archive; do not flatten away empty/removed states
        # or silently mix legacy rows with complete envelopes.
        from brasileirao_predictor.data.lineup_envelopes import snapshot_state_asof

        return snapshot_state_asof(rows, event_id=event_id, asof=asof)
    cutoff = _utc(asof)
    vintages: dict[str, tuple[datetime, str, list[dict[str, Any]]]] = {}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if str(row.get("source_event_id")) != str(event_id):
            continue
        try:
            received = _utc(str(row["ingested_at"]))
            published = _utc(str(row["published_at"])) if row.get("published_at") else None
        except (KeyError, TypeError, ValueError):
            continue
        if received <= cutoff and (published is None or published <= received):
            grouped[(str(row.get("team_id")), str(row.get("content_hash")))].append(row)
    for (team_id, content_hash), items in grouped.items():
        received = max(_utc(str(item["ingested_at"])) for item in items)
        if team_id in vintages and received == vintages[team_id][0] and content_hash != vintages[team_id][1]:
            raise ValueError("conflicting lineup vintages at the same receipt time")
        if team_id not in vintages or received > vintages[team_id][0]:
            vintages[team_id] = (received, content_hash, items)
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
