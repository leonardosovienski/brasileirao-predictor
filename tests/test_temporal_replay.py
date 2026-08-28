from src.research.temporal_replay import build_temporal_manifest


def test_temporal_replay_manifest_is_fingerprinted_and_batched() -> None:
    rows = [
        {"date": "2025-05-01", "home_team": "a", "away_team": "b"},
        {"date": "2025-05-01", "home_team": "c", "away_team": "d"},
        {
            "kickoff_at": "2025-05-02T21:00:00-03:00",
            "home_team": "e",
            "away_team": "f",
        },
    ]
    manifest = build_temporal_manifest(rows)
    assert manifest["row_count"] == 3
    assert manifest["group_count"] == 2
    assert len(manifest["source_sha256"]) == 64
    assert len(manifest["temporal_policy"]["fingerprint"]) == 16
    assert [group["precision"] for group in manifest["groups"]] == ["date", "kickoff"]


def test_temporal_replay_rejects_team_twice_in_same_batch() -> None:
    rows = [
        {"date": "2025-05-01", "home_team": "a", "away_team": "b"},
        {"date": "2025-05-01", "home_team": "a", "away_team": "c"},
    ]
    try:
        build_temporal_manifest(rows)
    except ValueError as exc:
        assert "appears more than once" in str(exc)
    else:
        raise AssertionError("duplicate team in a temporal batch must fail closed")
