import json

from src.data.lineup_archive import persist_lineups


def test_lineup_archive_is_append_only_and_idempotent_by_vintage(tmp_path):
    path = tmp_path / "lineups.jsonl"
    base = {
        "source_event_id": "1",
        "player_id": "2",
        "role": "starter",
        "content_hash": "a" * 64,
    }
    assert persist_lineups(path, [base]) == 1
    assert persist_lineups(path, [base]) == 0
    revised = {**base, "content_hash": "b" * 64, "role": "substitute"}
    assert persist_lineups(path, [revised]) == 1
    assert len([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]) == 2
