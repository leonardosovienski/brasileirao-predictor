"""Captura point-in-time e append-only de um evento do SofaScore.

O envelope preserva status, relógios, odds, escalação e estatísticas. Odds só
entram no ledger pré-jogo quando o evento ainda não começou e captured_at é
estritamente anterior ao kickoff.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ingest_sofascore import parse_odds, parse_ou, parse_statistics  # noqa: E402
from src.sofascore import Sofascore  # noqa: E402

DEFAULT_LEDGER = ROOT / "data" / "research" / "sofascore_event_captures.jsonl"
DEFAULT_DB = ROOT / "data" / "matches.db"


def _iso(timestamp: int | float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _players(lineups: dict) -> list[dict]:
    rows = []
    for team in ("home", "away"):
        side = lineups.get(team) or {}
        for item in side.get("players", []) or []:
            player = item.get("player") or {}
            rows.append(
                {
                    "team": team,
                    "player_id": str(player.get("id")) if player.get("id") is not None else None,
                    "player_name": player.get("name"),
                    "position": player.get("position"),
                    "role": "substitute" if item.get("substitute") else "starter",
                }
            )
    return rows


Clock = Callable[[], datetime]


def build_capture(event_id: int, captured_at: datetime, client: Sofascore) -> dict:
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("captured_at must be timezone-aware")
    event_payload = client._get(f"event/{event_id}", cache=False) or {}
    event = event_payload.get("event", event_payload)
    lineups = client.event_lineups(event_id) or {}
    odds = client.event_odds(event_id, finished=False) or {}
    statistics = client.event_statistics(event_id) or {}
    kickoff_at = _iso(event.get("startTimestamp"))
    captured = captured_at.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    status = event.get("status") or {}
    kickoff_dt = datetime.fromisoformat(kickoff_at.replace("Z", "+00:00")) if kickoff_at else None
    pre_match = bool(
        status.get("type") == "notstarted" and kickoff_dt is not None and captured_at.astimezone(UTC) < kickoff_dt
    )
    home, draw, away = parse_odds(odds)
    over, under = parse_ou(odds, 2.5)
    payload = {
        "schema_version": "sofascore-event-capture/1",
        "captured_at": captured,
        "kickoff_at": kickoff_at,
        "event_id": str(event_id),
        "source": "sofascore",
        "point_in_time": True,
        "pre_match": pre_match,
        "status": status,
        "home": (event.get("homeTeam") or {}).get("name"),
        "away": (event.get("awayTeam") or {}).get("name"),
        "score": [
            (event.get("homeScore") or {}).get("current"),
            (event.get("awayScore") or {}).get("current"),
        ],
        "time": event.get("time") or {},
        "lineup": {
            "confirmed": bool(lineups.get("confirmed")),
            "designation": "confirmed" if lineups.get("confirmed") else "probable",
            "players": _players(lineups),
        },
        "odds": {
            "source": "sofascore",
            "is_live": not pre_match,
            "1x2": {"home": home, "draw": draw, "away": away},
            "ou2.5": {"over": over, "under": under},
        },
        "statistics": parse_statistics(statistics).get("ALL", {}),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["content_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def append_capture(path: Path, payload: dict) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    identity = (payload.get("event_id"), payload.get("captured_at"), payload.get("content_hash"))
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                existing = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (existing.get("event_id"), existing.get("captured_at"), existing.get("content_hash")) == identity:
                return False
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return True


def persist_pre_match_odds(db_path: Path, payload: dict) -> int:
    if not payload["pre_match"]:
        return 0
    odds = payload["odds"]
    values = [
        ("1x2", "home", odds["1x2"]["home"]),
        ("1x2", "draw", odds["1x2"]["draw"]),
        ("1x2", "away", odds["1x2"]["away"]),
        ("ou2.5", "over", odds["ou2.5"]["over"]),
        ("ou2.5", "under", odds["ou2.5"]["under"]),
    ]
    rows = [
        (int(payload["event_id"]), payload["captured_at"], market, selection, odd, 1)
        for market, selection, odd in values
        if odd is not None and odd > 1
    ]
    connection = sqlite3.connect(db_path)
    try:
        before = connection.total_changes
        connection.executemany(
            "INSERT OR IGNORE INTO odds_snapshots "
            "(event_id,captured_at,market,selection,odd,pre_match) VALUES (?,?,?,?,?,?)",
            rows,
        )
        connection.commit()
        return connection.total_changes - before
    finally:
        connection.close()


def emit_run_record(record: dict, log_path: Path | None) -> None:
    rendered = json.dumps(record, ensure_ascii=False)
    print(rendered, flush=True)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def wait_until_confirmed(
    event_id: int,
    client: Sofascore,
    *,
    now: Clock = lambda: datetime.now(UTC),
    poll_seconds: int = 120,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    while True:
        event_payload = client._get(f"event/{event_id}", cache=False) or {}
        event = event_payload.get("event", event_payload)
        kickoff = event.get("startTimestamp")
        current = now()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("clock must return timezone-aware datetimes")
        if kickoff is None or current.timestamp() >= float(kickoff):
            return False
        lineups = client.event_lineups(event_id) or {}
        if lineups.get("confirmed"):
            return True
        sleep(max(15, poll_seconds))


def main(*, now: Clock = lambda: datetime.now(UTC)) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_id", nargs="+", type=int)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--wait-confirmed",
        action="store_true",
        help="poll until the lineup is confirmed; exit at kickoff without a post-kickoff capture",
    )
    parser.add_argument("--poll-seconds", type=int, default=120)
    parser.add_argument("--run-log", type=Path)
    args = parser.parse_args()
    client = Sofascore(rate_limit=0.2, cache_dir=None)
    for event_id in args.event_id:
        if args.wait_confirmed and not wait_until_confirmed(event_id, client, now=now, poll_seconds=args.poll_seconds):
            emit_run_record({"event_id": str(event_id), "status": "KICKOFF_REACHED_NO_CAPTURE"}, args.run_log)
            continue
        payload = build_capture(event_id, now(), client)
        appended = append_capture(args.ledger, payload)
        if not appended:
            written = 0
        else:
            written = persist_pre_match_odds(args.db, payload)
        emit_run_record(
            {
                "event_id": payload["event_id"],
                "captured_at": payload["captured_at"],
                "pre_match": payload["pre_match"],
                "lineup": payload["lineup"]["designation"],
                "capture_appended": appended,
                "odds_rows_written": written,
                "content_hash": payload["content_hash"],
            },
            args.run_log,
        )


if __name__ == "__main__":
    main()
