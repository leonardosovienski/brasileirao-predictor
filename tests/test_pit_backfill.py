import pytest

from src.data.pit_backfill import (
    CLOSING_DEFINITION_VERSION,
    choose_closing,
    connect_curated,
    curate_match,
    curate_odds,
    evaluation_view,
    pit_eligible,
    preserve_raw,
    quality_gate,
    register_raw,
    resolve_entity,
    verify_raw,
    walk_forward_splits,
)


def _match(**extra):
    row = {
        "source": "fixture",
        "source_match_id": "m1",
        "kickoff_at": "2024-05-01T20:00:00+00:00",
        "home_team": "Sao Paulo",
        "away_team": "Flamengo",
        "home_goals": 2,
        "away_goals": 1,
    }
    row.update(extra)
    return row


def test_raw_is_write_once_hashable_and_tamper_detected(tmp_path):
    raw = tmp_path / "raw" / "batch.json"
    manifest = preserve_raw(
        b'{"id":1}',
        raw,
        source="fixture",
        source_version="v1",
        retrieved_at="2024-01-01T00:00:00Z",
        license="test",
        parser_version="p1",
        row_count=1,
        temporal_coverage="2024",
    )
    verify_raw(raw, manifest)
    with pytest.raises(FileExistsError):
        preserve_raw(
            b"changed",
            raw,
            source="fixture",
            source_version="v1",
            retrieved_at="2024-01-01T00:00:00Z",
            license="test",
            parser_version="p1",
            row_count=1,
            temporal_coverage="2024",
        )
    raw.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash raw"):
        verify_raw(raw, manifest)


def test_curated_store_has_provenance_and_never_touches_live(tmp_path):
    conn = connect_curated(tmp_path / "curated.db")
    raw = tmp_path / "raw.json"
    manifest = preserve_raw(
        "{}",
        raw,
        source="fixture",
        source_version="v1",
        retrieved_at="2024-01-01T00:00:00Z",
        license="test",
        parser_version="p1",
        row_count=1,
        temporal_coverage="2024",
    )
    register_raw(conn, manifest)
    cid = curate_match(
        conn,
        _match(),
        aliases={"Sao Paulo": "São Paulo"},
        known={"São Paulo", "Flamengo"},
        batch_id="b1",
        ingested_at="2024-04-01T00:00:00Z",
    )
    assert cid.startswith("2024-05-01T20:00:00")
    row = conn.execute("select mapping_status,provenance_hash from curated_matches").fetchone()
    assert row[0] == "RULE_BASED" and len(row[1]) == 64
    assert conn.execute("select count(*) from raw_files").fetchone()[0] == 1


def test_entity_resolution_rejects_ambiguous_case():
    assert resolve_entity("x", "CLUBE", {}, {"Clube", "clube"}) == (None, "AMBIGUOUS")
    assert resolve_entity("x", "Unknown", {}, {"Clube"}) == (None, "REJECTED")


def test_closing_requires_valid_pre_kickoff_quote_and_versions_definition():
    rows = [
        {
            "bookmaker": "A",
            "market": "ou2.5",
            "selection": "over",
            "raw_odds": 2.0,
            "captured_at": "2024-04-30T20:00:00Z",
        },
        {
            "bookmaker": "A",
            "market": "ou2.5",
            "selection": "over",
            "raw_odds": 2.1,
            "captured_at": "2024-05-01T19:00:00Z",
        },
        {
            "bookmaker": "A",
            "market": "ou2.5",
            "selection": "over",
            "raw_odds": 9.0,
            "captured_at": "2024-05-01T21:00:00Z",
        },
    ]
    close = choose_closing(rows, kickoff_at="2024-05-01T20:00:00Z", bookmaker="A", market="ou2.5", selection="over")
    assert close["raw_odds"] == 2.1
    assert close["closing_definition_version"] == CLOSING_DEFINITION_VERSION


def test_curated_odds_rejects_future_capture_and_preserves_all_clocks(tmp_path):
    conn = connect_curated(tmp_path / "odds.db")
    row = {
        "source": "fixture",
        "source_match_id": "m1",
        "kickoff_at": "2024-05-01T20:00:00Z",
        "observed_at": "2024-05-01T10:00:00Z",
        "available_at": "2024-05-01T10:01:00Z",
        "captured_at": "2024-05-01T10:02:00Z",
        "bookmaker": "A",
        "market": "ou2.5",
        "selection": "over",
        "raw_odds": 2.0,
    }
    curate_odds(conn, row, canonical_match_id="cid", batch_id="b1")
    assert conn.execute("select count(*) from curated_odds").fetchone()[0] == 1
    with pytest.raises(ValueError, match="pré-evento"):
        curate_odds(
            conn,
            {**row, "source_match_id": "m2", "captured_at": "2024-05-01T21:00:00Z"},
            canonical_match_id="cid",
            batch_id="b1",
        )


def test_pit_rejects_future_and_evaluation_view_is_temporal(tmp_path):
    assert pit_eligible(
        available_at="2024-05-01T10:00:00Z",
        predicted_at="2024-05-01T11:00:00Z",
        kickoff_at="2024-05-01T20:00:00Z",
    )
    assert not pit_eligible(
        available_at="2024-05-01T21:00:00Z",
        predicted_at="2024-05-01T11:00:00Z",
        kickoff_at="2024-05-01T20:00:00Z",
    )
    conn = connect_curated(tmp_path / "eval.db")
    curate_match(
        conn,
        _match(source_match_id="past"),
        aliases={"Sao Paulo": "São Paulo"},
        known={"São Paulo", "Flamengo"},
        batch_id="b1",
        ingested_at="2024-04-01T00:00:00Z",
    )
    curate_match(
        conn,
        _match(source_match_id="future", kickoff_at="2024-06-01T20:00:00Z"),
        aliases={"Sao Paulo": "São Paulo"},
        known={"São Paulo", "Flamengo"},
        batch_id="b1",
        ingested_at="2024-04-02T00:00:00Z",
    )
    assert [r["source_match_id"] for r in evaluation_view(conn, predicted_at="2024-05-15T00:00:00Z")] == ["future"]


def test_walk_forward_holdout_and_cluster_gate_never_enable_capital():
    rows = [{"kickoff_at": f"2024-0{month}-15T12:00:00Z", "id": month} for month in (1, 2, 3, 4)]
    split = walk_forward_splits(
        rows,
        development_end="2024-02-01T00:00:00Z",
        validation_end="2024-03-01T00:00:00Z",
        test_end="2024-05-01T00:00:00Z",
    )
    assert [r["id"] for r in split["development"]] == [1]
    assert [r["id"] for r in split["validation"]] == [2]
    assert [r["id"] for r in split["test"]] == [3, 4]
    observations = [
        {
            "pit_valid": True,
            "matured": True,
            "cluster": "r1",
            "clubs": ("A", "B"),
            "pnl": 1.0,
            "clv": 0.1,
            "brier": 0.2,
        },
        {
            "pit_valid": True,
            "matured": False,
            "cluster": "r1",
            "clubs": ("A", "B"),
            "pnl": 1.0,
            "clv": 0.1,
            "brier": 0.2,
        },
    ]
    gate = quality_gate(observations, min_matured=2)
    assert gate["status"] == "INSUFFICIENT_SAMPLE"
    assert gate["capital_enabled"] is False
    assert gate["clusters"] == 1
