"""record_h9_closing_snapshots: só bate na API perto de um apito, escreve no
mesmo market_observations.jsonl, e não mascara indisponibilidade da fonte."""

from datetime import UTC, datetime, timedelta

import pytest
from predictor_core.data.contracts import DataUnavailableError

from brasileirao_predictor import db
from brasileirao_scripts import record_h9_closing_snapshots as job

KICKOFF = datetime(2027, 3, 1, 19, 0, tzinfo=UTC)


@pytest.fixture
def dbpath(tmp_path):
    path = tmp_path / "t.db"
    conn = db.connect(str(path))
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, kickoff_at) "
        "VALUES (1, 'T', '2027', ?, 'Casa', 'Fora', ?)",
        (KICKOFF.date().isoformat(), KICKOFF.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    return path


def _cfg(dbpath):
    return {"database": str(dbpath)}


def test_no_upcoming_kickoff_skips_api_call(dbpath, monkeypatch, tmp_path):
    monkeypatch.setattr(job, "load_config", lambda: _cfg(dbpath))

    class _BoomProvider:
        def __init__(self, *a, **k):
            raise AssertionError("nao deveria instanciar o provider fora da janela")

    monkeypatch.setattr(job, "TheOddsApiProvider", _BoomProvider)
    result = job.run(now=KICKOFF - timedelta(hours=6), db_path=dbpath, market_obs_path=tmp_path / "mo.jsonl")
    assert result == {"status": "NO_KICKOFF_WINDOW", "rows_written": 0}


def test_writes_quotes_when_kickoff_is_imminent(dbpath, monkeypatch, tmp_path):
    monkeypatch.setattr(job, "load_config", lambda: _cfg(dbpath))

    class _Provider:
        def __init__(self, *a, **k):
            pass

        def fetch_markets(self, *, markets, retrieved_at=None):
            assert markets == ("totals",)
            return [
                {
                    "source_event_id": "e1",
                    "bookmaker": "williamhill",
                    "market": "ou2.5",
                    "selection": "over",
                    "decimal_odds": 1.9,
                    "odds_captured_at": (KICKOFF - timedelta(minutes=10)).isoformat(timespec="seconds"),
                    "retrieved_at": retrieved_at.isoformat(timespec="seconds"),
                    "canonical_match_id": "the_odds_api:e1",
                    "home_team": "Casa",
                    "away_team": "Fora",
                    "kickoff_at": KICKOFF.isoformat(timespec="seconds"),
                }
            ]

    monkeypatch.setattr(job, "TheOddsApiProvider", _Provider)
    market_obs_path = tmp_path / "mo.jsonl"
    result = job.run(now=KICKOFF - timedelta(minutes=30), db_path=dbpath, market_obs_path=market_obs_path)
    assert result == {"status": "OK", "rows_written": 1}
    assert market_obs_path.exists()


def test_source_unavailable_is_reported_not_swallowed(dbpath, monkeypatch, tmp_path):
    monkeypatch.setattr(job, "load_config", lambda: _cfg(dbpath))

    class _BrokenProvider:
        def __init__(self, *a, **k):
            pass

        def fetch_markets(self, *, markets, retrieved_at=None):
            raise DataUnavailableError("The Odds API indisponivel")

    monkeypatch.setattr(job, "TheOddsApiProvider", _BrokenProvider)
    result = job.run(now=KICKOFF - timedelta(minutes=30), db_path=dbpath, market_obs_path=tmp_path / "mo.jsonl")
    assert result["status"] == "SOURCE_UNAVAILABLE"
    assert result["rows_written"] == 0
