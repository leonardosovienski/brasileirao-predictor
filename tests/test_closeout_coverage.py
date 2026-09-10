"""Report a single synthetic event universe, including an empty database."""

import sqlite3

import pytest

from brasileirao_predictor import check_coverage


@pytest.mark.parametrize("empty", [True, False])
def test_coverage_uses_event_intersections_and_handles_empty_universe(tmp_path, monkeypatch, capsys, empty):
    path = tmp_path / "coverage.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE sofascore_matches(event_id INTEGER, competition TEXT,
            odds_home REAL, odds_draw REAL, odds_away REAL);
        CREATE TABLE match_statistics(event_id INTEGER);
        CREATE TABLE odds_lines(event_id INTEGER, market TEXT);
    """)
    if not empty:
        conn.execute("INSERT INTO sofascore_matches VALUES(1,'synthetic',2,3,4)")
    for event_id in (1, 2, 3):
        conn.execute("INSERT INTO match_statistics VALUES(?)", (event_id,))
        conn.execute("INSERT INTO odds_lines VALUES(?,'cards')", (event_id,))
    conn.commit()
    conn.close()
    monkeypatch.setattr(check_coverage, "load_config", lambda: {"database": str(path)})
    check_coverage.main()
    output = capsys.readouterr().out
    if empty:
        assert "N/A" in output
    else:
        assert "100.0%" in output
    assert "300.0%" not in output
    assert "inf" not in output.lower()
