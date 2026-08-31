"""Append-only persistence for point-in-time lineup observations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def persist_lineups(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            seen.add((row.get("source_event_id"), row.get("player_id"), row.get("role"), row.get("content_hash")))
    written = 0
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            key = (row.get("source_event_id"), row.get("player_id"), row.get("role"), row.get("content_hash"))
            if None in key or key in seen:
                continue
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            seen.add(key)
            written += 1
    return written
