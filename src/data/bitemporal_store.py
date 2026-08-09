"""Small, fail-closed bitemporal store for prospective football observations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class BitemporalObservation:
    entity_type: str
    entity_id: str
    source: str
    event_at: datetime
    published_at: datetime
    ingested_at: datetime
    payload: dict[str, Any]
    charter_id: str

    def __post_init__(self) -> None:
        for field in ("entity_type", "entity_id", "source", "charter_id"):
            if not getattr(self, field).strip():
                raise ValueError(f"{field} is required")
        for field in ("event_at", "published_at", "ingested_at"):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        if self.ingested_at < self.published_at:
            raise ValueError("ingested_at cannot precede published_at")
        json.dumps(self.payload, allow_nan=False, sort_keys=True)

    @property
    def content_hash(self) -> str:
        encoded = json.dumps(self.payload, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
  entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, source TEXT NOT NULL,
  event_at TEXT NOT NULL, published_at TEXT NOT NULL, ingested_at TEXT NOT NULL,
  payload_json TEXT NOT NULL, content_hash TEXT NOT NULL, charter_id TEXT NOT NULL,
  PRIMARY KEY(entity_type, entity_id, source, published_at, ingested_at, content_hash)
);
CREATE INDEX IF NOT EXISTS observations_asof
ON observations(entity_type, entity_id, published_at, ingested_at);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def append(connection: sqlite3.Connection, observation: BitemporalObservation) -> bool:
    row = asdict(observation)
    cursor = connection.execute(
        "INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?,?,?,?)",
        (
            observation.entity_type,
            observation.entity_id,
            observation.source,
            observation.event_at.isoformat(),
            observation.published_at.isoformat(),
            observation.ingested_at.isoformat(),
            json.dumps(row["payload"], ensure_ascii=False, allow_nan=False, sort_keys=True),
            observation.content_hash,
            observation.charter_id,
        ),
    )
    connection.commit()
    return cursor.rowcount == 1


def as_known_at(connection: sqlite3.Connection, entity_type: str, at: datetime) -> list[dict[str, Any]]:
    """Latest eligible version per entity/source, using both knowledge clocks."""
    instant = _utc(at, "at").isoformat()
    rows = connection.execute(
        """SELECT * FROM (
          SELECT *, ROW_NUMBER() OVER (
            PARTITION BY entity_type, entity_id, source
            ORDER BY published_at DESC, ingested_at DESC, content_hash DESC
          ) AS rank
          FROM observations
          WHERE entity_type = ? AND published_at <= ? AND ingested_at <= ?
        ) WHERE rank = 1 ORDER BY entity_id, source""",
        (entity_type, instant, instant),
    ).fetchall()
    return [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]


def feature_rows_as_known_at(connection: sqlite3.Connection, at: datetime) -> list[dict[str, Any]]:
    """Materialization input; callers receive no observation learned after ``at``."""
    kinds = ("match_observation", "match_result", "odds_snapshot", "lineup")
    return [row for kind in kinds for row in as_known_at(connection, kind, at)]

