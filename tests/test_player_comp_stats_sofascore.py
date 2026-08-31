from __future__ import annotations

import json

from brasileirao_scripts import backfill_player_comp_stats_from_sofascore as backfill
from brasileirao_predictor import db


def test_aggregate_and_persist_player_stats_with_provenance(tmp_path) -> None:
    conn = db.connect(":memory:")
    conn.execute(
        "INSERT INTO sofascore_matches "
        "(event_id,competition,season,kickoff_at,home_team,away_team) "
        "VALUES (1,'Serie A 2024','2024','2024-05-01T20:00:00+00:00','Casa','Fora')"
    )
    payload = {
        "home": {
            "players": [
                {
                    "player": {"name": "Atleta", "position": "F"},
                    "position": "F",
                    "statistics": {
                        "minutesPlayed": 90,
                        "goals": 1,
                        "goalAssist": 1,
                        "expectedGoals": 0.7,
                        "expectedAssists": 0.2,
                    },
                }
            ]
        },
        "away": {"players": []},
    }
    (tmp_path / "event_1_lineups.json").write_text(json.dumps(payload), encoding="utf-8")

    rows = backfill.aggregate(conn, tmp_path)
    assert backfill.persist(conn, rows) == 1
    assert conn.execute(
        "SELECT position,minutes,games,goals,assists,xg,xag,source,available_at FROM player_comp_stats"
    ).fetchone() == ("F", 90, 1, 1, 1, 0.7, 0.2, backfill.SOURCE, "2024-05-01T20:00:00+00:00")
