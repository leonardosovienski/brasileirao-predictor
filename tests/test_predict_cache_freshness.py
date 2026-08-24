from src import predict


class _Conn:
    def execute(self, _sql):
        return self

    def fetchone(self):
        return (10,)


def _cfg():
    return {
        "database": "ignored.db",
        "elo": {},
        "model": {"calibration_window_years": 4, "goal_half_life_days": 360},
    }


def test_build_recomputes_in_memory_when_cache_hash_is_stale(monkeypatch, capsys):
    conn = _Conn()
    monkeypatch.setattr(predict.db, "connect", lambda _path: conn)
    monkeypatch.setattr(predict.db, "load_elo", lambda _conn: {"stale": 1.0})
    monkeypatch.setattr(
        predict.db,
        "load_params",
        lambda _conn: (0.1, 0.2, 0.3, 0.0, 10, "stale-hash", "2026-01-01T00:00:00+00:00"),
    )
    monkeypatch.setattr("src.cron_update_models.config_hash", lambda _cfg: "fresh-hash")
    monkeypatch.setattr(
        "src.cron_update_models.compute",
        lambda _cfg, _conn: ({"fresh": 2.0}, (1.0, 2.0, 3.0, 4.0), 10),
    )

    built_conn, elo, params = predict.build(_cfg())

    assert built_conn is conn
    assert elo == {"fresh": 2.0}
    assert params == (1.0, 2.0, 3.0, 4.0)
    assert "recalculando em memória" in capsys.readouterr().err


def test_build_uses_cache_only_when_hash_and_match_count_are_current(monkeypatch):
    conn = _Conn()
    monkeypatch.setattr(predict.db, "connect", lambda _path: conn)
    monkeypatch.setattr(predict.db, "load_elo", lambda _conn: {"cached": 1.0})
    monkeypatch.setattr(
        predict.db,
        "load_params",
        lambda _conn: (0.1, 0.2, 0.3, 0.0, 10, "current", "2026-01-01T00:00:00+00:00"),
    )
    monkeypatch.setattr("src.cron_update_models.config_hash", lambda _cfg: "current")

    _built_conn, elo, params = predict.build(_cfg())

    assert elo == {"cached": 1.0}
    assert params == (0.1, 0.2, 0.3, 0.0)
