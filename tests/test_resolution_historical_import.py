"""A research backfill must never destroy an existing database or admit bad prices."""

import csv
import sqlite3

import pytest

from brasileirao_scripts import import_ou25_historical_backfill as importer


def fixture(tmp_path, changes=None):
    database = tmp_path / "matches.db"
    with sqlite3.connect(database) as conn:
        conn.execute(
            "CREATE TABLE matches(event_id INTEGER,date TEXT,home_team TEXT,away_team TEXT,home_score INTEGER)"
        )
        conn.execute("INSERT INTO matches VALUES(123,'2022-05-01','Home','Away',1)")
    source = tmp_path / "raw.csv"
    row = dict(
        Season="2022",
        Date="01/05/2022",
        Home="Home",
        Away="Away",
        **{
            "AvgOver2.5": "2.1",
            "AvgUnder2.5": "1.9",
            "HighOver2.5": "2.2",
            "HighUnder2.5": "2.0",
            "NumBookmakers2.5": "3",
        },
    )
    row.update(changes or {})
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return source, database


def test_existing_output_is_rejected_without_touching_bytes(tmp_path):
    source, database = fixture(tmp_path)
    before = database.read_bytes()
    with pytest.raises(FileExistsError):
        importer.import_backfill(source, database, database)
    assert database.read_bytes() == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("AvgOver2.5", "inf"),
        ("AvgUnder2.5", "1"),
        ("HighOver2.5", "nan"),
        ("NumBookmakers2.5", "3.5"),
        ("NumBookmakers2.5", "-2"),
    ],
)
def test_bad_price_or_count_is_quarantined(tmp_path, field, value):
    source, database = fixture(tmp_path, {field: value})
    output = tmp_path / "research.sqlite"
    report = importer.import_backfill(source, database, output)
    assert report["imported"] == 0
    assert report["missing_price"] == 1
    with sqlite3.connect(output) as conn:
        assert conn.execute("SELECT count(*) FROM ou25_historical_backfill").fetchone()[0] == 0
        assert conn.execute("SELECT reason FROM unmatched_rows").fetchone()[0] == "invalid_price_or_bookmaker_count"


def test_failed_import_does_not_publish_partial_database(tmp_path):
    source, database = fixture(tmp_path, {"Date": "invalid"})
    output = tmp_path / "research.sqlite"
    with pytest.raises(ValueError):
        importer.import_backfill(source, database, output)
    assert not output.exists()


def test_valid_import_preserves_raw_and_keeps_economics_disabled(tmp_path):
    source, database = fixture(tmp_path)
    before = source.read_bytes(), database.read_bytes()
    report = importer.import_backfill(source, database, tmp_path / "research.sqlite")
    assert report["imported"] == 1
    assert report["capital_enabled"] is False
    assert report["clv_eligible"] is False
    assert before == (source.read_bytes(), database.read_bytes())
