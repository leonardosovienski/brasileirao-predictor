"""Read-only coverage audit; it never imputes or changes frozen model lineage."""

import sqlite3
from typing import Any


def xg_coverage(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """SELECT COALESCE(season, 'unknown') AS season,
                  COUNT(*) AS played,
                  SUM(CASE WHEN home_xg IS NOT NULL THEN 1 ELSE 0 END) AS home_valid,
                  SUM(CASE WHEN away_xg IS NOT NULL THEN 1 ELSE 0 END) AS away_valid,
                  SUM(CASE WHEN home_xg IS NOT NULL AND away_xg IS NOT NULL THEN 1 ELSE 0 END) AS paired_valid
           FROM sofascore_matches
           WHERE home_score IS NOT NULL AND away_score IS NOT NULL
           GROUP BY COALESCE(season, 'unknown') ORDER BY season"""
    ).fetchall()
    seasons = []
    for season, played, home, away, paired in rows:
        seasons.append(
            {
                "season": str(season),
                "played": int(played),
                "home_xg_valid": int(home or 0),
                "away_xg_valid": int(away or 0),
                "paired_xg_valid": int(paired or 0),
                "paired_coverage": float(paired or 0) / int(played) if played else 0.0,
            }
        )
    played = sum(row["played"] for row in seasons)
    paired = sum(row["paired_xg_valid"] for row in seasons)
    return {
        "schema_version": "xg-missingness-audit/v1",
        "semantics": {
            "observed_xg": "provider xG present for both teams",
            "legacy_xg_model_fallback": "missing provider xG replaced by realized goals in frozen xg_model lineage",
            "feature_builder_policy": "missing xG remains None and is never zero-imputed",
        },
        "seasons": seasons,
        "total": {"played": played, "paired_xg_valid": paired, "paired_coverage": paired / played if played else 0.0},
    }
