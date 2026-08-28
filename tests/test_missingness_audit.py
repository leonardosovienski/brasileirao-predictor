import sqlite3

from src.data.missingness_audit import xg_coverage


def test_xg_coverage_separates_paired_observation_from_legacy_fallback():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE sofascore_matches "
        "(season TEXT, home_score INTEGER, away_score INTEGER, home_xg REAL, away_xg REAL)"
    )
    conn.executemany(
        "INSERT INTO sofascore_matches VALUES (?,?,?,?,?)",
        [
            ("2025", 1, 0, 1.2, 0.7),
            ("2025", 2, 2, 1.4, None),
            ("2026", 0, 0, None, None),
            ("2026", None, None, 1.0, 1.0),
        ],
    )
    report = xg_coverage(conn)
    assert report["total"] == {"played": 3, "paired_xg_valid": 1, "paired_coverage": 1 / 3}
    assert report["seasons"][0]["paired_coverage"] == 0.5
    assert "realized goals" in report["semantics"]["legacy_xg_model_fallback"]
