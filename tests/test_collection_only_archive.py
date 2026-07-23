from datetime import datetime, timezone
from pathlib import Path

from src import db
from src.data.collection_only_archive import collect


def _fixture(conn):
    conn.execute("INSERT INTO sofascore_matches (event_id, competition, season, date, kickoff_at, home_team, away_team, home_score, away_score) VALUES (7, 'Brasileirão', '2026', '2026-07-20', '2026-07-20T20:00:00+00:00', 'Casa', 'Fora', 2, 1)")
    conn.commit()


def test_collection_only_dry_run_has_no_archive_write(tmp_path: Path):
    conn = db.connect(str(tmp_path / "m.db")); _fixture(conn)
    result = collect(conn, root=Path.cwd(), archive_path=tmp_path / "archive.jsonl", dry_run=True, observed_at=datetime(2026,7,21,tzinfo=timezone.utc))
    assert result["transitions_written"] > 0
    assert not (tmp_path / "archive.jsonl").exists()


def test_collection_only_is_idempotent_and_never_uses_shadow_state(tmp_path: Path):
    conn = db.connect(str(tmp_path / "m.db")); _fixture(conn); archive = tmp_path / "archive.jsonl"
    first = collect(conn, root=Path.cwd(), archive_path=archive, observed_at=datetime(2026,7,21,tzinfo=timezone.utc))
    second = collect(conn, root=Path.cwd(), archive_path=archive, observed_at=datetime(2026,7,21,tzinfo=timezone.utc))
    assert first["funnel"]["complete"] == 1
    assert second["transitions_written"] == 0
    assert "PROSPECTIVE_ELIGIBLE" not in archive.read_text(encoding="utf-8")


def test_retry_resumes_event_started_without_lifecycle_regression(tmp_path: Path):
    conn = db.connect(str(tmp_path / "m.db"))
    conn.execute("INSERT INTO sofascore_matches (event_id, competition, season, date, kickoff_at, home_team, away_team) VALUES (8, 'Brasileirão', '2026', '2026-07-20', '2026-07-20T20:00:00+00:00', 'Casa', 'Fora')")
    conn.commit(); archive = tmp_path / "archive.jsonl"; now = datetime(2026, 7, 21, tzinfo=timezone.utc)
    collect(conn, root=Path.cwd(), archive_path=archive, observed_at=now)
    result = collect(conn, root=Path.cwd(), archive_path=archive, observed_at=now)
    assert result["transitions_written"] == 0
