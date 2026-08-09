from datetime import UTC, datetime

import pytest

from src.data.bitemporal_store import BitemporalObservation, append, as_known_at, connect


def dt(hour: int) -> datetime:
    return datetime(2026, 8, 9, hour, tzinfo=UTC)


def observation(*, published: int, ingested: int, goals: int) -> BitemporalObservation:
    return BitemporalObservation(
        entity_type="match_result",
        entity_id="123",
        source="api_football",
        event_at=dt(10),
        published_at=dt(published),
        ingested_at=dt(ingested),
        payload={"home_goals": goals},
        charter_id="brasileirao-api-football-fixtures-v1",
    )


def test_as_known_at_never_sees_a_result_published_later(tmp_path):
    connection = connect(tmp_path / "pit.db")
    assert append(connection, observation(published=11, ingested=12, goals=1))
    assert as_known_at(connection, "match_result", dt(10)) == []
    assert as_known_at(connection, "match_result", dt(11)) == []
    assert as_known_at(connection, "match_result", dt(12))[0]["payload"]["home_goals"] == 1


def test_latest_version_and_idempotency(tmp_path):
    connection = connect(tmp_path / "pit.db")
    first = observation(published=11, ingested=12, goals=1)
    assert append(connection, first)
    assert not append(connection, first)
    assert append(connection, observation(published=12, ingested=13, goals=2))
    assert as_known_at(connection, "match_result", dt(13))[0]["payload"]["home_goals"] == 2


def test_rejects_impossible_ingestion_clock():
    with pytest.raises(ValueError, match="ingested_at"):
        observation(published=12, ingested=11, goals=1)

