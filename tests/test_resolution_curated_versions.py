"""Synthetic SQLite revisions: never migrate or inspect a real historical store."""

import sqlite3
from pathlib import Path

import pytest

from brasileirao_predictor.data.pit_backfill import (
    choose_closing,
    connect_curated,
    curate_match,
    curate_odds,
    evaluation_view,
)


def quote(**changes):
    return {
        "source": "synthetic",
        "source_match_id": "m",
        "kickoff_at": "2020-01-02T20:00:00Z",
        "observed_at": "2020-01-02T18:00:00Z",
        "available_at": "2020-01-02T18:00:00Z",
        "captured_at": "2020-01-02T18:00:01Z",
        "bookmaker": "A",
        "market": "ou2.5",
        "selection": "over",
        "line": 2.5,
        "period": "FT",
        "status": "ACTIVE",
        "raw_odds": 2.1,
        **changes,
    }


def close(rows):
    return choose_closing(rows, kickoff_at="2020-01-02T20:00:00Z", bookmaker="A", market="ou2.5", selection="over")


def records(conn):
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute("SELECT * FROM curated_odds")]


def test_curated_roundtrip_keeps_market_contract(tmp_path: Path) -> None:
    with connect_curated(tmp_path / "new.db") as conn:
        curate_odds(conn, quote(), canonical_match_id="canonical", batch_id="b1")
        row = records(conn)[0]
        assert (row["status"], row["period"], row["line"]) == ("ACTIVE", "FT", 2.5)
        closing = close([row])
        assert closing is not None and closing["raw_odds"] == 2.1


def test_curated_tied_conflicts_are_preserved_and_cannot_be_selected(tmp_path: Path) -> None:
    with connect_curated(tmp_path / "new.db") as conn:
        for odds in (2.1, 2.2):
            curate_odds(conn, quote(raw_odds=odds), canonical_match_id="canonical", batch_id="b1")
        rows = records(conn)
        assert len(rows) == 2
        assert close(rows) is None


def test_curated_suspension_survives_roundtrip_and_prevents_resurrection(tmp_path: Path) -> None:
    with connect_curated(tmp_path / "new.db") as conn:
        curate_odds(conn, quote(), canonical_match_id="canonical", batch_id="b1")
        curate_odds(
            conn,
            quote(status="SUSPENDED", raw_odds=None, captured_at="2020-01-02T19:00:00Z"),
            canonical_match_id="canonical",
            batch_id="b2",
        )
        assert len(records(conn)) == 2
        assert close(records(conn)) is None


def test_curated_exact_retry_is_idempotent(tmp_path: Path) -> None:
    with connect_curated(tmp_path / "new.db") as conn:
        for _ in range(2):
            curate_odds(conn, quote(), canonical_match_id="canonical", batch_id="b1")
        assert len(records(conn)) == 1


def test_curated_does_not_implicitly_mutate_old_schema(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE curated_matches (legacy TEXT)")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="schema"):
        connect_curated(path)
    assert path.read_bytes() == before


def match(**changes):
    return {
        "source": "synthetic",
        "source_match_id": "m",
        "canonical_match_id": "canonical",
        "kickoff_at": "2020-02-02T20:00:00Z",
        "home_team": "A",
        "away_team": "B",
        **changes,
    }


def put_match(conn, at, **changes):
    return curate_match(conn, match(**changes), aliases={}, known={"A", "B", "C"}, batch_id="b", ingested_at=at)


def test_match_revision_does_not_erase_earlier_as_of_state(tmp_path: Path) -> None:
    with connect_curated(tmp_path / "new.db") as conn:
        put_match(conn, "2020-01-01T00:00:00Z")
        put_match(conn, "2020-01-03T00:00:00Z", kickoff_at="2020-02-03T20:00:00Z")
        assert conn.execute("SELECT COUNT(*) FROM curated_matches").fetchone()[0] == 2
        earlier = evaluation_view(conn, predicted_at="2020-01-02T00:00:00Z")
        later = evaluation_view(conn, predicted_at="2020-01-04T00:00:00Z")
        assert earlier[0]["kickoff_at"] == "2020-02-02T20:00:00+00:00"
        assert later[0]["kickoff_at"] == "2020-02-03T20:00:00+00:00"


def test_match_conflicting_revision_at_same_receipt_is_not_arbitrated(tmp_path: Path) -> None:
    with connect_curated(tmp_path / "new.db") as conn:
        put_match(conn, "2020-01-01T00:00:00Z")
        put_match(conn, "2020-01-01T00:00:00Z", away_team="C")
        with pytest.raises(ValueError, match="conflit"):
            evaluation_view(conn, predicted_at="2020-01-02T00:00:00Z")


def test_cancelled_latest_match_does_not_resurrect_scheduled_version(tmp_path: Path) -> None:
    with connect_curated(tmp_path / "new.db") as conn:
        put_match(conn, "2020-01-01T00:00:00Z", match_status="SCHEDULED")
        put_match(conn, "2020-01-03T00:00:00Z", match_status="CANCELLED")
        assert evaluation_view(conn, predicted_at="2020-01-04T00:00:00Z") == []


@pytest.mark.parametrize("field", ["observed_at", "available_at", "published_at"])
def test_closing_rejects_future_information_even_for_direct_rows(field: str) -> None:
    with pytest.raises(ValueError, match="captur"):
        close([quote(**{field: "2020-01-02T19:00:00Z"})])
