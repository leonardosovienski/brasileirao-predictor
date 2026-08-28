import json

from src.operational_readiness import assess_operational_readiness


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
    (data / "matches.db").touch()
    snapshots = data / "odds_snapshots"
    snapshots.mkdir()
    (snapshots / "2026-01-01.jsonl").write_text('{"id": 1}\n', encoding="utf-8")
    metrics = data / "collector_metrics"
    metrics.mkdir()
    (metrics / "gate_a1_verdict.json").write_text('{"verdict": "PASS"}', encoding="utf-8")
    report = assess_operational_readiness(tmp_path, env={"ODDSPAPI_KEY": "configured-but-never-returned"})
    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["capital_enabled"] is False
