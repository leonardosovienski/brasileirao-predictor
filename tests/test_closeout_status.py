import sqlite3

from brasileirao_predictor import status


def test_status_opens_read_only_and_closes_connection(monkeypatch):
    class Tracked(sqlite3.Connection):
        closed = False

        def close(self):
            self.closed = True
            super().close()

    conn = sqlite3.connect(":memory:", factory=Tracked)
    conn.execute("CREATE TABLE matches(date TEXT, home_score INTEGER)")

    def connect(path, **kwargs):
        assert kwargs.get("read_only") is True
        return conn

    monkeypatch.setattr(status, "load_config", lambda: {"database": "synthetic.db"})
    monkeypatch.setattr(status.db, "connect", connect)
    monkeypatch.setattr(status.db, "load_elo", lambda conn: None)
    monkeypatch.setattr(status.db, "load_params", lambda conn: None)
    monkeypatch.setattr(status, "emit_event", lambda *args, **kwargs: None)
    try:
        status.run()
        assert conn.closed
    finally:
        conn.close()
