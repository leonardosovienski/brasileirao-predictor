import sqlite3

import pytest

from brasileirao_scripts import init_compose_data as init


def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("SPORTS_DB_PATH", str(tmp_path / "sports.db"))
    monkeypatch.setenv("MARKET_DB_PATH", str(tmp_path / "market.db"))
    monkeypatch.setattr(init, "load_config", lambda: {})

    def unexpected(*args, **kwargs):
        raise AssertionError("existing storage must be refused before db.connect")

    monkeypatch.setattr(init.db, "connect", unexpected)


def test_initializer_cannot_reset_an_existing_volume(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    sports = tmp_path / "sports.db"
    sports.write_bytes(b"synthetic-original-data")
    with pytest.raises(FileExistsError):
        init.main()
    assert sports.read_bytes() == b"synthetic-original-data"
    assert not (tmp_path / "market.db").exists()


def test_initializer_requires_distinct_databases(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv("MARKET_DB_PATH", str(tmp_path / "sports.db"))
    with pytest.raises(ValueError, match="distinct"):
        init.main()
    assert not (tmp_path / "sports.db").exists()


def test_initializer_creates_only_new_demo_storage(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SPORTS_DB_PATH", str(tmp_path / "sports.db"))
    monkeypatch.setenv("MARKET_DB_PATH", str(tmp_path / "market.db"))
    monkeypatch.setattr(
        init, "load_config", lambda: {"elo": {}, "model": {"calibration_window_years": 3, "goal_half_life_days": 365}}
    )
    assert init.main() == 0
    assert "DEMO_PARAMETERS_ONLY" in capsys.readouterr().out
    for name in ("sports.db", "market.db"):
        with sqlite3.connect(tmp_path / name) as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 0
