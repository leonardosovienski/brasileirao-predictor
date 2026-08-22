from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from scripts.capture_sofascore_event import (
    append_capture,
    build_capture,
    persist_pre_match_odds,
    wait_until_confirmed,
)


class FakeSofascore:
    def __init__(self, *, kickoff: int, status: str = "notstarted", confirmed: bool = False):
        self.kickoff = kickoff
        self.status = status
        self.confirmed = confirmed

    def _get(self, path, cache=False):
        assert cache is False
        return {
            "event": {
                "id": 123,
                "startTimestamp": self.kickoff,
                "status": {"type": self.status},
                "homeTeam": {"name": "Casa"},
                "awayTeam": {"name": "Fora"},
            }
        }

    def event_lineups(self, event_id):
        return {"confirmed": self.confirmed, "home": {"players": []}, "away": {"players": []}}

    def event_odds(self, event_id, finished=False):
        return {"markets": []}

    def event_statistics(self, event_id):
        return {}


def test_build_capture_uses_aware_clock_and_strict_pre_match_boundary():
    kickoff = int(datetime(2026, 8, 22, 21, 30, tzinfo=UTC).timestamp())
    client = FakeSofascore(kickoff=kickoff)
    before = build_capture(123, datetime(2026, 8, 22, 21, 29, 59, tzinfo=UTC), client)
    at_kickoff = build_capture(123, datetime(2026, 8, 22, 21, 30, tzinfo=UTC), client)
    assert before["pre_match"] is True
    assert before["lineup"] == {"confirmed": False, "designation": "probable", "players": []}
    assert at_kickoff["pre_match"] is False


def test_build_capture_rejects_naive_timestamp():
    client = FakeSofascore(kickoff=1)
    with pytest.raises(ValueError, match="timezone-aware"):
        build_capture(123, datetime(2026, 8, 22), client)


def test_append_capture_is_append_only_and_deduplicates(tmp_path):
    path = tmp_path / "captures.jsonl"
    payload = {"event_id": "123", "captured_at": "2026-08-22T20:00:00Z", "content_hash": "abc"}
    assert append_capture(path, payload) is True
    original = path.read_bytes()
    assert append_capture(path, payload) is False
    assert path.read_bytes() == original
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_post_kickoff_capture_never_enters_pre_match_odds(tmp_path):
    db = tmp_path / "matches.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE odds_snapshots(event_id INTEGER,captured_at TEXT,market TEXT,"
        "selection TEXT,odd REAL,pre_match INTEGER,PRIMARY KEY(event_id,market,selection,captured_at))"
    )
    con.close()
    payload = {
        "event_id": "123",
        "captured_at": "2026-08-22T21:30:00Z",
        "pre_match": False,
        "odds": {"1x2": {"home": 2.0, "draw": 3.0, "away": 4.0}, "ou2.5": {"over": 1.9, "under": 1.9}},
    }
    assert persist_pre_match_odds(db, payload) == 0
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM odds_snapshots").fetchone()[0] == 0
    con.close()


def test_wait_until_confirmed_has_injectable_clock_and_sleep():
    kickoff = int(datetime(2026, 8, 22, 21, 30, tzinfo=UTC).timestamp())
    client = FakeSofascore(kickoff=kickoff, confirmed=True)
    assert wait_until_confirmed(
        123,
        client,
        now=lambda: datetime(2026, 8, 22, 21, 0, tzinfo=UTC),
        sleep=lambda _: pytest.fail("must not sleep when already confirmed"),
    )


def test_wait_until_confirmed_refuses_at_kickoff_without_fetching_lineup():
    kickoff = int(datetime(2026, 8, 22, 21, 30, tzinfo=UTC).timestamp())
    client = FakeSofascore(kickoff=kickoff, confirmed=True)
    assert not wait_until_confirmed(
        123,
        client,
        now=lambda: datetime(2026, 8, 22, 21, 30, tzinfo=UTC),
        sleep=lambda _: None,
    )
