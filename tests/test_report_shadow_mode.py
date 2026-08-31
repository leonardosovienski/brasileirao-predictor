from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_reporter():
    spec = importlib.util.spec_from_file_location(
        "shadow_report_test", ROOT / "brasileirao_scripts" / "report_shadow_mode.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def pick(event_id: int = 1, selection: str = "under", captured_at: str = "2026-07-10T10:00:00+00:00") -> dict:
    return {
        "event_id": event_id,
        "selection": selection,
        "captured_at": captured_at,
        "date": "2026-07-12",
        "market": "ou2.5",
        "odd": 2.0,
        "edge": 0.05,
        "model_prob": 0.55,
    }


def result(event_id: int = 1, selection: str = "under", won: int = 1) -> dict:
    return {
        "event_id": event_id,
        "selection": selection,
        "settled_at": "2026-07-12T23:00:00+00:00",
        "won": won,
        "pnl": 1.0 if won else -1.0,
        "clv": 0.04,
    }


def test_empty_ledger_is_insufficient(tmp_path: Path) -> None:
    reporter = load_reporter()
    report = reporter.build_report(tmp_path / "picks.jsonl", tmp_path / "results.jsonl")
    assert report["classification"] == "DADOS INSUFICIENTES"
    assert report["counts"] == {
        "pick_records": 0,
        "unique_picks": 0,
        "matured": 0,
        "open": 0,
        "result_records": 0,
    }


def test_open_pick_is_reported_without_metrics(tmp_path: Path) -> None:
    reporter = load_reporter()
    picks, results = tmp_path / "picks.jsonl", tmp_path / "results.jsonl"
    write_jsonl(picks, [pick()])
    report = reporter.build_report(picks, results)
    assert report["counts"]["open"] == 1 and report["metrics"]["roi_gross"] is None


def test_matured_pick_computes_clv_roi_rps_and_calibration(tmp_path: Path) -> None:
    reporter = load_reporter()
    picks, results = tmp_path / "picks.jsonl", tmp_path / "results.jsonl"
    write_jsonl(picks, [pick()])
    write_jsonl(results, [result()])
    report = reporter.build_report(picks, results)
    assert report["counts"]["matured"] == 1
    assert report["metrics"]["roi_gross"] == 1.0 and report["metrics"]["clv_mean"] == 0.04
    assert report["metrics"]["rps_binary"] == report["metrics"]["brier"]
    assert report["calibration"][0]["count"] == 1


def test_duplicates_and_invalid_temporal_order_are_excluded(tmp_path: Path) -> None:
    reporter = load_reporter()
    picks, results = tmp_path / "picks.jsonl", tmp_path / "results.jsonl"
    write_jsonl(picks, [pick(), pick(), pick(2, captured_at="2026-07-13T10:00:00+00:00")])
    write_jsonl(results, [result(), result()])
    report = reporter.build_report(picks, results)
    assert report["exclusions"]["duplicate_pick"] == 1
    assert report["exclusions"]["duplicate_result"] == 1
    assert report["exclusions"]["capture_after_event_date"] == 1
    assert report["counts"]["matured"] == 1


def test_missing_closing_and_turn_are_explicitly_unavailable(tmp_path: Path) -> None:
    reporter = load_reporter()
    picks, results = tmp_path / "picks.jsonl", tmp_path / "results.jsonl"
    write_jsonl(picks, [pick()])
    write_jsonl(results, [result()])
    report = reporter.build_report(picks, results)
    assert report["capturability"]["close_odds_available"] == 0
    assert report["segments"]["capture_turn"].startswith("NÃO DISPONÍVEL")
    assert report["schema_version"] == "shadow-report/v2"
    assert any("legados" in item for item in report["limitations"])


def test_enriched_ledger_proves_temporality_odds_turn_and_costs(tmp_path: Path) -> None:
    reporter = load_reporter()
    picks, results = tmp_path / "picks.jsonl", tmp_path / "results.jsonl"
    enriched_pick = {
        **pick(),
        "predicted_at": "2026-07-10T10:00:00+00:00",
        "kickoff_at": "2026-07-12T20:00:00+00:00",
        "capture_turn": "morning",
        "odds_open": 1.9,
        "odds_captured": 2.0,
        "odds_source": "sofascore",
    }
    enriched_result = {
        **result(),
        "odds_close": 2.1,
        "costs": {"status": "not_applicable_shadow_no_execution", "amount_units": 0.0},
    }
    write_jsonl(picks, [enriched_pick])
    write_jsonl(results, [enriched_result])
    report = reporter.build_report(picks, results)
    assert report["temporal_validation"] == {"valid_pre_event_timestamp": 1}
    assert report["capturability"]["exact_pre_event_timestamps"] == 1
    assert report["capturability"]["open_odds_available"] == 1
    assert report["capturability"]["close_odds_available"] == 1
    assert report["segments"]["capture_turn"]["morning"]["matured"] == 1
    assert report["metrics"]["roi_costs"] == report["metrics"]["roi_gross"]
    assert report["limitations"] == []


def test_json_is_deterministic_and_report_is_read_only(tmp_path: Path, monkeypatch, capsys) -> None:
    reporter = load_reporter()
    data = tmp_path / "data"
    data.mkdir()
    picks, results = data / "sombra_picks.jsonl", data / "sombra_results.jsonl"
    write_jsonl(picks, [pick()])
    write_jsonl(results, [result()])
    before = picks.read_bytes(), results.read_bytes()
    monkeypatch.setattr(reporter, "ROOT", tmp_path)
    assert reporter.main(["--json"]) == 0
    first = capsys.readouterr().out
    assert reporter.main(["--json"]) == 0
    second = capsys.readouterr().out
    assert first == second and before == (picks.read_bytes(), results.read_bytes())
