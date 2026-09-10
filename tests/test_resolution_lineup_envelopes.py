from concurrent.futures import ThreadPoolExecutor

import pytest

from brasileirao_predictor.research.residual_features import lineup_state_asof


def envelope(**updates):
    return {
        "schema_version": "lineup-envelope/2",
        "source": "synthetic",
        "source_event_id": "event-1",
        "team_id": "team-1",
        "observed_at": "2024-01-01T10:00:00Z",
        "received_at": "2024-01-01T10:00:01Z",
        "published_at": None,
        "status": "COMPLETE",
        "raw_sha256": "a" * 64,
        "parser_version": "synthetic/1",
        "players": [{"player_id": "p1", "role": "starter"}],
        **updates,
    }


def test_envelope_is_consumed_without_flattening_away_empty_state():
    old = envelope()
    empty = envelope(status="EMPTY", players=[], received_at="2024-01-01T11:00:00Z", raw_sha256="b" * 64)
    assert lineup_state_asof([old, empty], event_id="event-1", asof="2024-01-01T10:30:00Z") == {"team-1": {"p1"}}
    assert lineup_state_asof([old, empty], event_id="event-1", asof="2024-01-01T11:30:00Z") == {"team-1": set()}


def test_same_receipt_conflict_cannot_choose_a_lineup():
    with pytest.raises(ValueError, match="conflict"):
        lineup_state_asof(
            [envelope(), envelope(status="REMOVED", players=[])], event_id="event-1", asof="2024-01-01T12:00:00Z"
        )


def test_later_snapshot_resolves_old_conflict_independent_of_input_order():
    old, conflict = envelope(), envelope(status="REMOVED", players=[])
    newer = envelope(received_at="2024-01-01T11:00:00Z")
    for rows in ([old, conflict, newer], [newer, conflict, old]):
        assert lineup_state_asof(rows, event_id="event-1", asof="2024-01-01T12:00:00Z") == {"team-1": {"p1"}}


@pytest.mark.parametrize("status", ["INVALID", "UNAVAILABLE"])
def test_unknown_lineup_is_not_an_empty_lineup(status):
    rows = [envelope(), envelope(status=status, players=[], received_at="2024-01-01T11:00:00Z")]
    assert lineup_state_asof(rows, event_id="event-1", asof="2024-01-01T12:00:00Z") == {}


def test_atomic_envelopes_preserve_empty_and_concurrent_writes(tmp_path):
    from brasileirao_predictor.data.lineup_envelopes import persist_snapshot, read_snapshots

    rows = [envelope(received_at=f"2024-01-01T10:{i:02d}:01Z") for i in range(12)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda row: persist_snapshot(tmp_path, row), rows * 2))
    assert len(read_snapshots(tmp_path, source="synthetic", event_id="event-1")) == 12
    empty = envelope(status="EMPTY", players=[], received_at="2024-01-01T11:00:00Z")
    persist_snapshot(tmp_path, empty)
    read = read_snapshots(tmp_path, source="synthetic", event_id="event-1")
    assert lineup_state_asof(read, event_id="event-1", asof="2024-01-01T12:00:00Z") == {"team-1": set()}


def test_corrupt_envelope_fails_closed(tmp_path):
    from brasileirao_predictor.data.lineup_envelopes import persist_snapshot, read_snapshots

    path = persist_snapshot(tmp_path, envelope())
    path.write_text('{"broken":', encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt"):
        read_snapshots(tmp_path, source="synthetic", event_id="event-1")


@pytest.mark.parametrize(
    "updates", [{"received_at": "2024-01-01T09:00:00Z"}, {"status": "EMPTY"}, {"raw_sha256": "bad"}]
)
def test_invalid_envelope_is_rejected_before_writing(tmp_path, updates):
    from brasileirao_predictor.data.lineup_envelopes import persist_snapshot

    with pytest.raises(ValueError):
        persist_snapshot(tmp_path, envelope(**updates))
    assert list(tmp_path.iterdir()) == []
