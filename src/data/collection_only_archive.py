"""Brasileirão adapter for predictor_core COLLECTION_ONLY archival facts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from typing import Any

from predictor_core.contracts.collection import (
    CollectionArchive,
    LifecycleState,
    ObservationEnvelope,
    aggregate_funnel,
)

# `pythonw.exe` (executavel de toda tarefa agendada) nao tem console: um
# processo de console filho ganharia janela VISIVEL na tela do dono.
# Saida ja e capturada, entao a flag nao esconde nada.
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

RUN_ID = "collection-brasileirao-20260723-core-9d352654"
ARCHIVE_PATH = Path(__file__).resolve().parents[2] / "data" / "collection_only" / "brasileirao_events.jsonl"


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _utc(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(UTC) if parsed.tzinfo else None


def _commit(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        creationflags=_NO_WINDOW,
    ).stdout.strip()


def collect(
    conn: sqlite3.Connection,
    *,
    root: Path,
    archive_path: Path = ARCHIVE_PATH,
    dry_run: bool = False,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Idempotently archive configured Sofascore calendar/result facts only."""
    now = observed_at or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("observed_at deve conter timezone")
    now = now.astimezone(UTC).replace(microsecond=0)
    core_version = version("predictor-core")
    code_commit = _commit(root)
    cutoff = (now - timedelta(days=7)).isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT event_id, competition, season, date, kickoff_at, home_team, away_team, "
        "home_score, away_score FROM sofascore_matches "
        "WHERE kickoff_at IS NOT NULL AND kickoff_at >= ? ORDER BY kickoff_at, event_id",
        (cutoff,),
    ).fetchall()
    archive = CollectionArchive(archive_path)
    current_by_event = {}
    if not dry_run:
        for row in archive.store:
            if row.get("collection_run_id") == RUN_ID:
                current_by_event[row["canonical_event_id"]] = ObservationEnvelope.from_dict(row["envelope"])
    written = 0
    for event_id, competition, season, date, kickoff, home, away, hs, aas in rows:
        scheduled = _utc(kickoff)
        if scheduled is None:
            continue
        snapshot = {
            "event_id": event_id,
            "competition": competition,
            "season": season,
            "date": date,
            "kickoff_at": kickoff,
            "home": home,
            "away": away,
            "home_score": hs,
            "away_score": aas,
        }
        envelope = ObservationEnvelope(
            collection_run_id=RUN_ID,
            project="brasileirao-predictor",
            domain="football",
            canonical_event_id=f"sofascore:{event_id}",
            observed_at=now,
            scheduled_at=scheduled,
            source="sofascore",
            source_record_id=str(event_id),
            provenance_hash=_hash({"source": "sofascore", "event_id": event_id, "snapshot": snapshot}),
            source_snapshot_hash=_hash(snapshot),
            code_commit=code_commit,
            core_version=core_version,
            participants={"home": home, "away": away},
            competition={"name": competition, "season": season},
            created_at=now,
            updated_at=now,
        )
        current = current_by_event.get(envelope.canonical_event_id)
        if current is not None and current.is_terminal:
            continue
        if current is None:
            if not dry_run:
                archive.append(envelope)
                current_by_event[envelope.canonical_event_id] = envelope
            written += 1
            current = envelope
        for state, predecessor in (
            (LifecycleState.VALIDATED, LifecycleState.DISCOVERED),
            (LifecycleState.SNAPSHOT_RECORDED, LifecycleState.VALIDATED),
        ):
            # A retry may resume from EVENT_STARTED or later; never regress the
            # append-only lifecycle to a prior state.
            if current.lifecycle_state != predecessor:
                continue
            next_item = current.transition(state, at=now)
            if not dry_run:
                archive.append(next_item, previous=current)
                current_by_event[envelope.canonical_event_id] = next_item
            written += 1
            current = next_item
        if scheduled <= now and current.lifecycle_state == LifecycleState.SNAPSHOT_RECORDED:
            next_item = current.transition(LifecycleState.EVENT_STARTED, at=now)
            if not dry_run:
                archive.append(next_item, previous=current)
                current_by_event[envelope.canonical_event_id] = next_item
            written += 1
            current = next_item
        if hs is not None and aas is not None and current.lifecycle_state == LifecycleState.EVENT_STARTED:
            result = {
                "home_score": int(hs),
                "away_score": int(aas),
                "status": "official_from_configured_sports_source",
            }
            next_item = current.transition(LifecycleState.OFFICIAL_RESULT_FOUND, at=now, official_result=result)
            if not dry_run:
                archive.append(next_item, previous=current)
                current_by_event[envelope.canonical_event_id] = next_item
            written += 1
            current = next_item
        if current.lifecycle_state == LifecycleState.OFFICIAL_RESULT_FOUND:
            next_item = current.transition(LifecycleState.COMPLETE, at=now, official_result=current.official_result)
            if not dry_run:
                archive.append(next_item, previous=current)
                current_by_event[envelope.canonical_event_id] = next_item
            written += 1
    envelopes = list(current_by_event.values()) if not dry_run else []
    return {
        "collection_only": True,
        "collection_run_id": RUN_ID,
        "dry_run": dry_run,
        "events_seen": len(rows),
        "transitions_written": written,
        "archive": str(archive_path),
        "funnel": aggregate_funnel(envelopes, project="brasileirao-predictor", collection_run_id=RUN_ID)
        if envelopes
        else None,
    }
