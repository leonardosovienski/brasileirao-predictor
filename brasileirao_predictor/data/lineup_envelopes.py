"""Immutable, atomic snapshots for new archives; no legacy collector is changed."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "lineup-envelope/2"


def _clock(value):
    if not isinstance(value, str):
        raise ValueError("lineup timestamp must be an aware ISO string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("lineup timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonblank string")
    return value


def validate_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict) or row.get("schema_version") != SCHEMA:
        raise ValueError("unsupported lineup envelope")
    result = dict(row)
    for field in ("source", "source_event_id", "team_id", "parser_version"):
        _text(result.get(field), field)
    if not isinstance(result.get("raw_sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", result["raw_sha256"]) is None:
        raise ValueError("raw_sha256 must identify preserved raw bytes; it does not authenticate them")
    observed, received = _clock(result.get("observed_at")), _clock(result.get("received_at"))
    published = _clock(result["published_at"]) if result.get("published_at") is not None else None
    if observed > received or (published is not None and published > received):
        raise ValueError("invalid lineup clock ordering")
    result.update(
        observed_at=observed.isoformat(),
        received_at=received.isoformat(),
        published_at=published.isoformat() if published else None,
    )
    status, players = result.get("status"), result.get("players")
    if status not in {"COMPLETE", "EMPTY", "REMOVED", "UNAVAILABLE", "INVALID"} or not isinstance(players, list):
        raise ValueError("invalid lineup state")
    if (status == "COMPLETE") != bool(players):
        raise ValueError("only a COMPLETE envelope may contain players")
    seen = set()
    for player in players:
        if not isinstance(player, dict):
            raise ValueError("player must be an object")
        identity = _text(player.get("player_id"), "player_id")
        if identity in seen or player.get("role") not in {"starter", "substitute"}:
            raise ValueError("duplicate player or invalid role")
        seen.add(identity)
    # Stable bytes make retries idempotent, including list-order-only retries.
    result["players"] = sorted(players, key=lambda player: player["player_id"])
    json.dumps(result, allow_nan=False)
    return result


def _bytes(row):
    return (json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def _partition(root, source, event_id):
    identity = json.dumps([_text(source, "source"), _text(event_id, "event_id")], ensure_ascii=False).encode("utf-8")
    return Path(root).resolve() / hashlib.sha256(identity).hexdigest()


def persist_snapshot(root: Path, row: dict[str, Any]) -> Path:
    """Publish one flushed immutable file without replacing another writer's file.

    Interrupted temporary files are not snapshots. Corruption or conflicting
    same-clock revisions are preserved and rejected by readers, never skipped.
    """
    row = validate_snapshot(row)
    payload = _bytes(row)
    folder = _partition(root, row["source"], row["source_event_id"])
    destination = folder / (hashlib.sha256(payload).hexdigest() + ".json")
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / (uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if destination.read_bytes() != payload:
                raise ValueError("corrupt immutable lineup snapshot") from None
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_snapshots(root: Path, *, source: str, event_id: str) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(_partition(root, source, event_id).glob("*.json")):
        try:
            payload = path.read_bytes()
            if path.stem != hashlib.sha256(payload).hexdigest():
                raise ValueError("snapshot digest mismatch")
            row = validate_snapshot(json.loads(payload, object_pairs_hook=_unique_pairs))
            if row["source"] != source or row["source_event_id"] != event_id or _bytes(row) != payload:
                raise ValueError("snapshot identity or canonical encoding mismatch")
        except (ValueError, TypeError, KeyError, UnicodeError) as exc:
            raise ValueError(f"corrupt lineup envelope: {path.name}") from exc
        rows.append(row)
    return sorted(rows, key=lambda row: (row["received_at"], row["team_id"], row["raw_sha256"]))


def snapshot_state_asof(rows, *, event_id: str, asof: str) -> dict[str, set[str]]:
    """Unknown teams are omitted; EMPTY/REMOVED teams have an empty starter set."""
    cutoff, latest = _clock(asof), {}
    sources, conflicts = set(), set()
    for raw in rows:
        row = validate_snapshot(raw)
        if row["source_event_id"] != event_id or _clock(row["received_at"]) > cutoff:
            continue
        sources.add(row["source"])
        if len(sources) > 1:
            raise ValueError("conflicting lineup sources require explicit upstream selection")
        team = row["team_id"]
        if team in latest and row["received_at"] == latest[team]["received_at"] and _bytes(row) != _bytes(latest[team]):
            conflicts.add(team)
        if team not in latest or row["received_at"] > latest[team]["received_at"]:
            latest[team] = row
            conflicts.discard(team)
    if conflicts:
        raise ValueError("conflicting lineup snapshots at the same receipt time")
    return {
        team: {p["player_id"] for p in row["players"] if p["role"] == "starter"}
        for team, row in latest.items()
        if row["status"] not in {"UNAVAILABLE", "INVALID"}
    }
