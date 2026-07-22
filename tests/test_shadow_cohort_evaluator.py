import json
from pathlib import Path

from scripts.evaluate_shadow_cohort import evaluate
from src.data.prospective_shadow import record_hash


def test_legacy_records_do_not_count(tmp_path: Path):
    picks = tmp_path / "picks.jsonl"; results = tmp_path / "results.jsonl"
    picks.write_text(json.dumps({"event_id": 1, "selection": "under", "captured_at": "2026-01-01T10:00:00+00:00"}) + "\n", encoding="utf-8")
    results.write_text(json.dumps({"event_id": 1, "selection": "under", "settled_at": "2026-01-02T10:00:00+00:00", "result": "lost", "settlement_status": "settled"}) + "\n", encoding="utf-8")
    report = evaluate(picks, results)
    assert report["classification"]["LEGACY_INCOMPLETE"] == 1
    assert report["counts"]["eligible"] == 0


def test_valid_prospective_pick_requires_complete_clocks(tmp_path: Path):
    row = {"pick_id":"p1", "trial_id":"h3", "model_version":"m1", "code_commit":"abc", "predicted_at":"2026-01-01T10:00:00+00:00", "kickoff_at":"2026-01-01T12:00:00+00:00", "market":"ou2.5", "selection":"under", "captured_odds":2.0, "odds_captured_at":"2026-01-01T10:01:00+00:00", "bookmaker":"x", "source":"s", "source_event_id":"e1", "canonical_match_id":"c1", "closing_definition_version":"v1", "data_quality_status":"ok"}
    row["provenance_hash"] = record_hash(row)
    picks = tmp_path / "picks.jsonl"; results = tmp_path / "results.jsonl"
    picks.write_text(json.dumps(row) + "\n", encoding="utf-8"); results.write_text("", encoding="utf-8")
    report = evaluate(picks, results)
    assert report["classification"]["PROSPECTIVE_ELIGIBLE"] == 1
    assert report["counts"]["matured"] == 0


def test_complete_test_only_lifecycle_is_rejected_in_production(tmp_path: Path):
    row = {"pick_id":"test-1", "trial_id":"h3", "model_version":"m1", "code_commit":"abc", "predicted_at":"2026-01-01T10:00:00+00:00", "kickoff_at":"2026-01-01T12:00:00+00:00", "market":"ou2.5", "selection":"under", "captured_odds":2.0, "odds_captured_at":"2026-01-01T10:01:00+00:00", "bookmaker":"test", "source":"fixture", "source_event_id":"e1", "canonical_match_id":"c1", "closing_definition_version":"v1", "data_quality_status":"ok", "synthetic":True}
    row["provenance_hash"] = record_hash(row)
    picks = tmp_path / "picks.jsonl"; results = tmp_path / "results.jsonl"
    picks.write_text(json.dumps(row) + "\n", encoding="utf-8"); results.write_text("", encoding="utf-8")
    report = evaluate(picks, results)
    assert report["classification"]["PROSPECTIVE_ELIGIBLE"] == 0
    assert report["rejections"]["non_production_record"] == 1
