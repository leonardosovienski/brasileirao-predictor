"""Isolated storage and reconciliation for secondary historical sources."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from predictor_core.data.contracts import DataUnavailableError

API_FOOTBALL_TEAM_MAP = {
    "America Mineiro": "América Mineiro",
    "Atletico Goianiense": "Atlético Goianiense",
    "Atletico Paranaense": "Athletico",
    "Atletico-MG": "Atlético Mineiro",
    "Avai": "Avaí",
    "Ceara": "Ceará",
    "Criciuma": "Criciúma",
    "Cuiaba": "Cuiabá",
    "Fortaleza EC": "Fortaleza",
    "Gremio": "Grêmio",
    "Goias": "Goiás",
    "RB Bragantino": "Red Bull Bragantino",
    "Sao Paulo": "São Paulo",
    "Vasco DA Gama": "Vasco da Gama",
    "Vitoria": "Vitória",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS shadow_matches (
    source TEXT NOT NULL,
    source_event_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    scheduled_at TEXT NOT NULL,
    match_date TEXT NOT NULL,
    raw_home_team TEXT NOT NULL,
    raw_away_team TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_goals INTEGER,
    away_goals INTEGER,
    status TEXT,
    shadow_only INTEGER NOT NULL CHECK (shadow_only = 1),
    PRIMARY KEY (source, source_event_id),
    UNIQUE (match_date, home_team, away_team)
);
CREATE INDEX IF NOT EXISTS idx_shadow_season ON shadow_matches(season, match_date);
"""


def connect_shadow(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def canonical_team(raw: str, known_teams: set[str]) -> str:
    canonical = API_FOOTBALL_TEAM_MAP.get(raw, raw)
    if canonical not in known_teams:
        raise DataUnavailableError(f"clube da fonte sem mapeamento aprovado: {raw!r}")
    return canonical


def ingest_api_football(conn: sqlite3.Connection, rows: Iterable[dict[str, Any]], *, known_teams: set[str]) -> int:
    values = []
    for row in rows:
        if row.get("source") != "api_football" or row.get("shadow_only") is not True:
            raise ValueError("a expansão aceita apenas registros api_football shadow_only")
        home = canonical_team(row["home_team"], known_teams)
        away = canonical_team(row["away_team"], known_teams)
        if home == away:
            raise DataUnavailableError(f"partida inválida após reconciliação: {home}")
        values.append(
            (
                row["source"],
                row["source_event_id"],
                int(row["season"]),
                row["scheduled_at"],
                row["scheduled_at"][:10],
                row["home_team"],
                row["away_team"],
                home,
                away,
                row.get("home_goals"),
                row.get("away_goals"),
                row.get("status"),
                1,
            )
        )
    conn.executemany(
        """
        INSERT INTO shadow_matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(source, source_event_id) DO UPDATE SET
          season=excluded.season, scheduled_at=excluded.scheduled_at,
          match_date=excluded.match_date, raw_home_team=excluded.raw_home_team,
          raw_away_team=excluded.raw_away_team, home_team=excluded.home_team,
          away_team=excluded.away_team, home_goals=excluded.home_goals,
          away_goals=excluded.away_goals, status=excluded.status
    """,
        values,
    )
    conn.commit()
    return len(values)


def coverage_report(shadow: sqlite3.Connection, production: sqlite3.Connection) -> dict[str, Any]:
    total, scored, first_date, last_date = shadow.execute("""
        SELECT count(*), count(home_goals), min(match_date), max(match_date)
        FROM shadow_matches
    """).fetchone()
    duplicate_rows = production.execute("""
        SELECT date, home_team, away_team, home_score, away_score
        FROM matches
    """).fetchall()
    production_by_key = {(r[0], r[1], r[2]): (r[3], r[4]) for r in duplicate_rows}
    exact_duplicates = score_conflicts = new_matches = 0
    for date, home, away, hg, ag in shadow.execute(
        "SELECT match_date,home_team,away_team,home_goals,away_goals FROM shadow_matches"
    ):
        current = production_by_key.get((date, home, away))
        if current is None:
            new_matches += 1
        elif current == (hg, ag):
            exact_duplicates += 1
        else:
            score_conflicts += 1
    seasons = dict(shadow.execute("SELECT season,count(*) FROM shadow_matches GROUP BY season ORDER BY season"))
    return {
        "total": total,
        "with_score": scored,
        "first_date": first_date,
        "last_date": last_date,
        "by_season": seasons,
        "exact_duplicates": exact_duplicates,
        "score_conflicts": score_conflicts,
        "new_matches": new_matches,
        "promotion_safe": bool(total and scored == total and score_conflicts == 0),
    }
