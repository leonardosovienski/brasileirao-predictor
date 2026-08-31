"""Agrega os caches de lineup Sofascore em player_comp_stats.

O agregado de uma temporada recebe ``available_at`` igual ao último kickoff
incluído. Consumidores point-in-time só podem usá-lo depois desse instante.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from brasileirao_predictor import db
from brasileirao_predictor.ingest import ROOT, load_config

SOURCE = "sofascore_lineups_cache/v1"


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def aggregate(conn: sqlite3.Connection, cache_dir: Path) -> list[tuple[Any, ...]]:
    events = {
        int(row[0]): row[1:]
        for row in conn.execute(
            "SELECT event_id,competition,season,kickoff_at,home_team,away_team "
            "FROM sofascore_matches WHERE event_id IS NOT NULL"
        )
    }
    totals: dict[tuple[str, str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "positions": Counter(),
            "minutes": 0,
            "games": 0,
            "goals": 0,
            "assists": 0,
            "xg": 0.0,
            "xag": 0.0,
            "available_at": "",
        }
    )
    for path in sorted(cache_dir.glob("event_*_lineups.json")):
        try:
            event_id = int(path.name.split("_", 2)[1])
            competition, season, kickoff, home, away = events[event_id]
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (KeyError, ValueError, json.JSONDecodeError):
            continue
        for side, team in (("home", home), ("away", away)):
            for item in (payload.get(side) or {}).get("players", []):
                player = (item.get("player") or {}).get("name")
                stats = item.get("statistics") or {}
                if not player or not team or not competition or not season or not stats:
                    continue
                key = (str(player), str(team), str(competition), str(season))
                out = totals[key]
                position = item.get("position") or (item.get("player") or {}).get("position")
                if position:
                    out["positions"][str(position)] += 1
                out["minutes"] += int(_number(stats.get("minutesPlayed")))
                out["games"] += 1
                out["goals"] += int(_number(stats.get("goals")))
                out["assists"] += int(_number(stats.get("goalAssist")))
                out["xg"] += _number(stats.get("expectedGoals"))
                out["xag"] += _number(stats.get("expectedAssists"))
                out["available_at"] = max(out["available_at"], str(kickoff or ""))
    rows = []
    for key, values in sorted(totals.items()):
        position = values["positions"].most_common(1)[0][0] if values["positions"] else None
        rows.append(
            (
                *key,
                position,
                values["minutes"],
                values["games"],
                values["goals"],
                values["assists"],
                round(values["xg"], 6),
                round(values["xag"], 6),
                SOURCE,
                values["available_at"] or None,
            )
        )
    return rows


def persist(conn: sqlite3.Connection, rows: list[tuple[Any, ...]]) -> int:
    conn.executemany(
        """
        INSERT INTO player_comp_stats
          (player,team,competition,season,position,minutes,games,goals,assists,xg,xag,source,available_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(player,team,competition,season) DO UPDATE SET
          position=excluded.position, minutes=excluded.minutes, games=excluded.games,
          goals=excluded.goals, assists=excluded.assists, xg=excluded.xg, xag=excluded.xag,
          source=excluded.source, available_at=excluded.available_at
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    cfg = load_config()
    cache_dir = args.cache_dir or ROOT / cfg["sofascore"]["cache_dir"]
    conn = db.connect(str(ROOT / cfg["database"]))
    try:
        rows = aggregate(conn, cache_dir)
        count = persist(conn, rows)
    finally:
        conn.close()
    print(f"PLAYER_COMP_STATS_BACKFILLED rows={count} source={SOURCE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
