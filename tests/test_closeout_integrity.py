"""Regressions use only synthetic journals, prices and caller declarations."""

import json
from datetime import timedelta

import pytest
from test_prediction_protocol import NOW, candidate

from brasileirao_predictor import bet_log
from brasileirao_predictor.data.pit_backfill import choose_closing, connect_curated, curate_odds
from brasileirao_predictor.prediction_protocol import assess_prediction_readiness


@pytest.mark.parametrize("score", [True, 1.9, "1.9", float("inf")])
def test_score_cannot_be_truncated_or_boolean(tmp_path, score):
    path = tmp_path / "bets.jsonl"
    bet_log.add_bet("A", "B", "ou15", "over", 2, path=path)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        bet_log.settle_bet("A", "B", score, 0, path=path)
    assert path.read_bytes() == before


@pytest.mark.parametrize("ht", [(True, 0), (0.9, 0), (0,), (0, 0, 0)])
def test_half_time_requires_two_integer_counts(tmp_path, ht):
    path = tmp_path / "bets.jsonl"
    bet_log.add_bet("A", "B", "ou05_1t", "over", 2, path=path)
    with pytest.raises(ValueError):
        bet_log.settle_bet("A", "B", 2, 0, ht=ht, path=path)
    assert len(path.read_text().splitlines()) == 1


def journal(tmp_path):
    path = tmp_path / "bets.jsonl"
    bet_log.add_bet("A", "B", "ou15", "over", 2, path=path, bet_id="one")
    bet_log.settle_bet("A", "B", 2, 0, path=path)
    return path, [json.loads(line) for line in path.read_text().splitlines()]


def test_summary_rejects_duplicate_settlement(tmp_path):
    path, rows = journal(tmp_path)
    path.write_text("\n".join(json.dumps(row) for row in [*rows, rows[-1]]) + "\n")
    with pytest.raises(ValueError):
        bet_log.summary(path)


def test_summary_rejects_orphan_and_changed_amount(tmp_path):
    path, rows = journal(tmp_path)
    for change in ({"bet_id": "missing"}, {"stake": 100}, {"profit": 100}):
        path.write_text("\n".join(json.dumps(row) for row in [rows[0], {**rows[1], **change}]) + "\n")
        with pytest.raises(ValueError):
            bet_log.summary(path)


def test_imported_duplicate_bet_id_is_rejected(tmp_path):
    path, rows = journal(tmp_path)
    path.write_text("\n".join(json.dumps(row) for row in [rows[0], rows[0]]) + "\n")
    with pytest.raises(ValueError):
        bet_log.list_bets(path)


@pytest.mark.parametrize("raw", ['{"kind":"bet","stake":NaN}', '{"kind":"bet","kind":"settlement"}'])
def test_malformed_json_journal_refused(tmp_path, raw):
    path = tmp_path / "bets.jsonl"
    path.write_text(raw + "\n")
    with pytest.raises(ValueError):
        bet_log._read(path)


def quote(**changes):
    return {
        "source": "synthetic",
        "source_match_id": "event1",
        "canonical_match_id": "match1",
        "bookmaker": "A",
        "market": "ou2.5",
        "selection": "over",
        "line": 2.5,
        "period": "FT",
        "status": "ACTIVE",
        "raw_odds": 2.0,
        "captured_at": "2024-05-01T18:00:00Z",
        **changes,
    }


def closing(rows):
    return choose_closing(rows, kickoff_at="2024-05-01T20:00:00Z", bookmaker="A", market="ou2.5", selection="over")


@pytest.mark.parametrize("changes", [{"raw_odds": None}, {"status": "SUSPENDED"}, {"status": "UNKNOWN"}])
def test_last_unusable_state_must_not_resurrect_price(changes):
    assert closing([quote(), quote(captured_at="2024-05-01T19:00:00Z", **changes)]) is None


def test_closing_conflicting_latest_tie_abstains():
    assert closing([quote(), quote(raw_odds=2.2)]) is None


@pytest.mark.parametrize(
    "changes", [{"source_match_id": "event2"}, {"source": "other"}, {"line": 3.5}, {"period": "1H"}]
)
def test_closing_cannot_mix_event_source_or_contract(changes):
    with pytest.raises(ValueError):
        closing([quote(), quote(captured_at="2024-05-01T19:00:00Z", **changes)])


@pytest.mark.parametrize("field", ["observed_at", "published_at"])
def test_curated_clock_cannot_follow_receipt(tmp_path, field):
    conn = connect_curated(tmp_path / "curated.db")
    row = (
        quote(
            kickoff_at="2024-05-01T20:00:00Z",
            available_at="2024-05-01T17:00:00Z",
            observed_at="2024-05-01T17:00:00Z",
            **{field: "2024-05-01T19:00:00Z"},
        )
        if field != "observed_at"
        else quote(
            kickoff_at="2024-05-01T20:00:00Z", available_at="2024-05-01T17:00:00Z", observed_at="2024-05-01T19:00:00Z"
        )
    )
    try:
        with pytest.raises(ValueError):
            curate_odds(conn, row, canonical_match_id="match1", batch_id="test")
        assert conn.execute("select count(*) from curated_odds").fetchone()[0] == 0
    finally:
        conn.close()


@pytest.mark.parametrize(
    "changes",
    [
        {"capital_enabled": "false"},
        {"lineup_confirmed": 1},
        {"event_id": "   "},
        {"current_season_matches_available": True, "current_season_matches_included": True},
        {"current_score": (True, 0)},
    ],
)
def test_readiness_rejects_coerced_or_blank_input(changes):
    with pytest.raises(ValueError):
        assess_prediction_readiness(candidate(**changes))


def test_declarations_do_not_certify_prospective_evidence():
    report = assess_prediction_readiness(candidate())
    assert report.ready
    assert not report.pre_match_evidence_eligible
    assert report.designation == "CONTRACT_PRE_MATCH"


@pytest.mark.parametrize(
    "changes",
    [
        {"historical_data_cutoff": NOW - timedelta(days=2)},
        {"latest_training_result_available_at": NOW - timedelta(days=2)},
        {"lineup_confirmed": True, "lineup_captured_at": None},
        {
            "prediction_kind": "LIVE",
            "kickoff_at": NOW - timedelta(minutes=10),
            "live_observed_at": NOW - timedelta(minutes=20),
            "observed_minute": 5,
            "current_score": (0, 0),
        },
    ],
)
def test_inconsistent_chronology_blocks_contract(changes):
    assert not assess_prediction_readiness(candidate(**changes)).ready
