import json
import sqlite3
from datetime import UTC, datetime

import pytest

from brasileirao_scripts import backfill_player_comp_stats_from_sofascore as backfill


def inputs(tmp_path, stats):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE sofascore_matches (event_id, competition, season, kickoff_at, home_team, away_team)")
    conn.execute("INSERT INTO sofascore_matches VALUES (1,'synthetic','2024','2024-01-01T00:00:00Z','A','B')")
    payload = {"home": {"players": [{"player": {"name": "P"}, "statistics": stats}]}, "away": {"players": []}}
    (tmp_path / "event_1_lineups.json").write_text(json.dumps(payload), encoding="utf-8")
    return conn


def test_postmatch_player_stats_are_not_backdated_to_kickoff(tmp_path):
    with inputs(tmp_path, {"minutesPlayed": 90, "goals": 1}) as conn:
        before = datetime.now(UTC)
        row = backfill.aggregate(conn, tmp_path)[0]
        assert before <= datetime.fromisoformat(row[-1]) <= datetime.now(UTC)


def test_missing_xg_is_unknown_instead_of_zero(tmp_path):
    with inputs(tmp_path, {"minutesPlayed": 90}) as conn:
        row = backfill.aggregate(conn, tmp_path)[0]
        assert row[9] is None and row[10] is None


@pytest.mark.parametrize("count", [True, 1.9, -1, "2"])
def test_player_counts_are_not_coerced_or_truncated(tmp_path, count):
    with inputs(tmp_path, {"goals": count}) as conn, pytest.raises(ValueError):
        backfill.aggregate(conn, tmp_path)


def test_corrupt_player_file_does_not_silently_shrink_the_aggregate(tmp_path):
    with inputs(tmp_path, {"goals": 1}) as conn:
        (tmp_path / "event_1_lineups.json").write_text("{broken", encoding="utf-8")
        with pytest.raises(ValueError):
            backfill.aggregate(conn, tmp_path)
