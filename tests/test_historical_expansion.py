import sqlite3

import pytest
from predictor_core.data.contracts import DataUnavailableError

from brasileirao_predictor.data.historical_expansion import (
    canonical_team,
    connect_shadow,
    coverage_report,
    ingest_api_football,
)


def _row(event="1", home="Sao Paulo", away="Flamengo", hg=2, ag=1):
    return {
        "source": "api_football",
        "source_event_id": event,
        "season": 2024,
        "scheduled_at": "2024-05-01T20:00:00+00:00",
        "home_team": home,
        "away_team": away,
        "home_goals": hg,
        "away_goals": ag,
        "status": "FT",
        "shadow_only": True,
    }


def test_reconciles_observed_alias_and_ingest_is_idempotent(tmp_path):
    conn = connect_shadow(tmp_path / "shadow.db")
    known = {"São Paulo", "Flamengo"}
    assert ingest_api_football(conn, [_row()], known_teams=known) == 1
    assert ingest_api_football(conn, [_row()], known_teams=known) == 1
    assert conn.execute("select raw_home_team,home_team,count(*) from shadow_matches").fetchone() == (
        "Sao Paulo",
        "São Paulo",
        1,
    )


def test_unknown_team_fails_closed():
    with pytest.raises(DataUnavailableError, match="sem mapeamento"):
        canonical_team("Inventado FC", {"Flamengo"})


def test_report_detects_duplicates_new_rows_and_score_conflicts(tmp_path):
    shadow = connect_shadow(tmp_path / "shadow.db")
    known = {"São Paulo", "Flamengo", "Bahia"}
    ingest_api_football(
        shadow,
        [
            _row("1"),
            {**_row("2", "Bahia", "Flamengo", 0, 0), "scheduled_at": "2024-05-02T20:00:00+00:00"},
        ],
        known_teams=known,
    )
    production = sqlite3.connect(":memory:")
    production.execute("create table matches(date,home_team,away_team,home_score,away_score)")
    production.execute("insert into matches values('2024-05-01','São Paulo','Flamengo',2,0)")
    report = coverage_report(shadow, production)
    assert report["score_conflicts"] == 1
    assert report["new_matches"] == 1
    assert report["promotion_safe"] is False
