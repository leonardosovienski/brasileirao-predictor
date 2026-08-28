"""Shared, fingerprinted temporal grouping rules for historical evaluation."""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

FallbackPolicy = Literal["group_by_date", "reject"]


@dataclass(frozen=True)
class TemporalGroup:
    key: str
    precision: Literal["kickoff", "date"]
    rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class TemporalPolicy:
    version: str = "temporal-groups/v1"
    fallback: FallbackPolicy = "group_by_date"

    @property
    def fingerprint(self) -> str:
        payload = json.dumps({"version": self.version, "fallback": self.fallback}, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:16]

    def group(self, rows: Iterable[dict[str, Any]]) -> list[TemporalGroup]:
        grouped: dict[tuple[str, Literal["kickoff", "date"]], list[dict[str, Any]]] = {}
        for row in rows:
            kickoff = row.get("kickoff_at")
            precision: Literal["kickoff", "date"]
            if kickoff:
                parsed = datetime.fromisoformat(str(kickoff).replace("Z", "+00:00"))
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise ValueError("kickoff_at must be timezone-aware")
                key = parsed.astimezone(UTC).isoformat()
                precision = "kickoff"
            else:
                if self.fallback == "reject":
                    raise ValueError("kickoff_at missing under reject policy")
                date_value = str(row.get("date") or "")[:10]
                try:
                    datetime.fromisoformat(date_value)
                except ValueError as exc:
                    raise ValueError("row requires ISO date when kickoff_at is missing") from exc
                key, precision = date_value, "date"
            grouped.setdefault((key, precision), []).append(row)
        groups = [TemporalGroup(key, precision, tuple(items)) for (key, precision), items in grouped.items()]
        return sorted(groups, key=lambda group: (group.key, group.precision))


def assert_unique_teams(group: TemporalGroup) -> None:
    seen: set[str] = set()
    for row in group.rows:
        for field in ("home_team", "away_team"):
            team = str(row.get(field) or "")
            if not team:
                raise ValueError(f"temporal group {group.key} has missing {field}")
            if team in seen:
                raise ValueError(f"team {team!r} appears more than once in temporal group {group.key}")
            seen.add(team)
