"""Agrega os caches de lineup Sofascore em player_comp_stats.

O cache sem recibo histórico só se torna conhecido nesta materialização.
``available_at`` registra a conclusão da leitura local, nunca o kickoff do jogo.
Campos ausentes permanecem desconhecidos; não se executa migração retrospectiva.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from brasileirao_predictor import db
from brasileirao_predictor.ingest import ROOT, load_config

SOURCE = "sofascore_lineups_cache/v2_observed_on_materialization"


def _number(value: Any, *, count: bool = False) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("player statistics must be explicit nonnegative numbers")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError("player statistics must be finite") from exc
    if not math.isfinite(number) or number < 0 or (count and (not isinstance(value, int))):
        raise ValueError("invalid player statistic or non-integer count")
    return value if count else number


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
        }
    )
    for path in sorted(cache_dir.glob("event_*_lineups.json")):
        try:
            event_id = int(path.name.split("_", 2)[1])
            competition, season, _kickoff, home, away = events[event_id]
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"unresolved or corrupt player cache: {path.name}") from exc
        if not isinstance(payload, dict):
            raise ValueError("player cache must be an object")
        for side, team in (("home", home), ("away", away)):
            side_data = payload.get(side)
            if not isinstance(side_data, dict) or not isinstance(side_data.get("players"), list):
                raise ValueError("both lineup sides require explicit player arrays")
            seen = set()
            for item in side_data["players"]:
                player = (item.get("player") or {}).get("name")
                stats = item.get("statistics") or {}
                if not player or not team or not competition or not season or not stats:
                    continue
                if player in seen:
                    raise ValueError("duplicate player identity in the same event and side")
                seen.add(player)
                key = (str(player), str(team), str(competition), str(season))
                out = totals[key]
                position = item.get("position") or (item.get("player") or {}).get("position")
                if position:
                    out["positions"][str(position)] += 1
                out["games"] += 1
                for target, field, count in (
                    ("minutes", "minutesPlayed", True),
                    ("goals", "goals", True),
                    ("assists", "goalAssist", True),
                    ("xg", "expectedGoals", False),
                    ("xag", "expectedAssists", False),
                ):
                    value = _number(stats.get(field), count=count)
                    out[target] = None if value is None or out[target] is None else out[target] + value
                    if out[target] is not None and not math.isfinite(float(out[target])):
                        raise ValueError("nonfinite aggregate player statistic")
    observed_on_materialization = datetime.now(UTC).isoformat()
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
                round(values["xg"], 6) if values["xg"] is not None else None,
                round(values["xag"], 6) if values["xag"] is not None else None,
                SOURCE,
                observed_on_materialization,
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
