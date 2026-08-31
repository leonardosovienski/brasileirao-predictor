import json
import sqlite3
from datetime import UTC, datetime

from brasileirao_predictor.operational_readiness import assess_operational_readiness


def _catalogs(data):
    (data / "team_aliases.json").write_text(
        json.dumps({"mapping_version": "v1", "aliases": {"Home FC": "home"}}), encoding="utf-8"
    )
    (data / "teams_brasileirao.json").write_text(json.dumps({"teams": {"Home": {"slug": "home"}}}), encoding="utf-8")


def test_readiness_fails_closed_and_never_enables_capital(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    _catalogs(data)
    report = assess_operational_readiness(tmp_path, env={})
    assert report["status"] == "BLOCKED"
    assert "oddspapi_credential" in report["blockers"]
    assert report["capital_enabled"] is False
    assert report["secrets_exposed"] is False


def test_all_local_evidence_reaches_human_review_only(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    _catalogs(data)
    with sqlite3.connect(data / "odds_operational.db") as connection:
        connection.execute("CREATE TABLE odds_event_versions (id INTEGER)")
        connection.execute("CREATE TABLE odds_snapshot_facts (id INTEGER)")
    snapshots = data / "odds_snapshots"
    snapshots.mkdir()
    (snapshots / "2026-01-01.jsonl").write_text('{"id": 1}\n', encoding="utf-8")
    metrics = data / "collector_metrics"
    metrics.mkdir()
    (metrics / "gate_a1_verdict.json").write_text('{"verdict": "PASS"}', encoding="utf-8")
    state = data / "collector_state"
    state.mkdir()
    now = datetime(2026, 8, 28, 12, tzinfo=UTC)
    for name in ("collector", "discovery", "metrics"):
        (state / f"{name}_heartbeat.json").write_text(
            json.dumps({"checked_at": now.isoformat(), "status": "PASS"}), encoding="utf-8"
        )
    report = assess_operational_readiness(tmp_path, env={"ODDSPAPI_KEY": "configured-but-never-returned"}, now=now)
    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["capital_enabled"] is False


def test_stale_heartbeat_blocks_readiness(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    _catalogs(data)
    state = data / "collector_state"
    state.mkdir()
    (state / "collector_heartbeat.json").write_text(
        json.dumps({"checked_at": "2026-08-01T00:00:00+00:00"}), encoding="utf-8"
    )
    report = assess_operational_readiness(tmp_path, now=datetime(2026, 8, 28, tzinfo=UTC))
    assert report["checks"]["collector_heartbeat"]["status"] == "BLOCKED"
