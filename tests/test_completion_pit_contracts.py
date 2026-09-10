import hashlib
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from brasileirao_predictor.data.bitemporal_store import BitemporalObservation, append, as_known_at, connect
from brasileirao_predictor.data.pit_backfill import cluster_bootstrap_mean, evaluation_view, quality_gate
from brasileirao_predictor.market_pricer import over_under


def test_charter_is_part_of_observation_identity(tmp_path):
    at = datetime(2020, 1, 1, tzinfo=UTC)
    first = BitemporalObservation("lineup", "one", "synthetic", at, at, at, {"v": 1}, "alpha")
    conn = connect(tmp_path / "pit.sqlite")
    assert append(conn, first)
    assert append(conn, replace(first, charter_id="beta"))
    with pytest.raises(ValueError, match="charter"):
        as_known_at(conn, "lineup", at)
    assert len(as_known_at(conn, "lineup", at, charter_id="alpha")) == 1
    conn.close()


def test_same_payload_changed_event_clock_is_a_conflict(tmp_path):
    at = datetime(2020, 1, 2, tzinfo=UTC)
    obs = BitemporalObservation("lineup", "one", "synthetic", at, at, at, {}, "alpha")
    conn = connect(tmp_path / "pit.sqlite")
    assert append(conn, obs)
    assert append(conn, replace(obs, event_at=at.replace(day=1)))
    with pytest.raises(ValueError, match="conflicting"):
        as_known_at(conn, "lineup", at)
    conn.close()


def test_legacy_schema_is_refused_without_modifying_its_bytes(tmp_path):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE observations(entity_type TEXT PRIMARY KEY, charter_id TEXT)")
        conn.execute("INSERT INTO observations VALUES ('lineup','old')")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="legacy observation schema"):
        connect(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_sql_decision_uses_utc_not_lexical_offset():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE curated_matches(kickoff_at TEXT, ingested_at TEXT, canonical_match_id TEXT)")
    conn.execute("INSERT INTO curated_matches VALUES ('2020-01-01T13:00:00+00:00','2020-01-01T10:00:00+00:00','x')")
    assert len(evaluation_view(conn, predicted_at="2020-01-01T09:00:00-03:00")) == 1
    conn.close()


def test_club_concentration_uses_club_appearances_denominator():
    result = quality_gate([{"pit_valid": True, "matured": True, "clubs": ["A", "B"], "cluster": 1}])
    assert result["club_hhi"] == 0.5


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), True])
def test_bootstrap_rejects_nonfinite_and_boolean_results(value):
    with pytest.raises(ValueError):
        cluster_bootstrap_mean([{"cluster": 1, "pnl": value}], "pnl")


@pytest.mark.parametrize("line", [float("nan"), float("inf"), True, 2.25])
def test_ou_rejects_unimplemented_line_contract(line):
    with pytest.raises(ValueError):
        over_under([[1.0]], line)
