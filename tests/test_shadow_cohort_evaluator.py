import json
from pathlib import Path

from scripts.evaluate_shadow_cohort import compute_verdict, evaluate
from src.data.prospective_shadow import record_hash


def _matured_pick(pick_id: str, match_id: str, clv: float, pnl: float) -> dict:
    return {
        "pick_id": pick_id,
        "canonical_match_id": match_id,
        "source_event_id": match_id,
        "clv": clv,
        "pnl": pnl,
    }


def test_legacy_records_do_not_count(tmp_path: Path):
    picks = tmp_path / "picks.jsonl"
    results = tmp_path / "results.jsonl"
    picks.write_text(
        json.dumps({"event_id": 1, "selection": "under", "captured_at": "2026-01-01T10:00:00+00:00"}) + "\n",
        encoding="utf-8",
    )
    results.write_text(
        json.dumps(
            {
                "event_id": 1,
                "selection": "under",
                "settled_at": "2026-01-02T10:00:00+00:00",
                "result": "lost",
                "settlement_status": "settled",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = evaluate(picks, results)
    assert report["classification"]["LEGACY_INCOMPLETE"] == 1
    assert report["counts"]["eligible"] == 0


def test_valid_prospective_pick_requires_complete_clocks(tmp_path: Path):
    row = {
        "pick_id": "p1",
        "trial_id": "h3",
        "model_version": "m1",
        "code_commit": "abc",
        "predicted_at": "2026-01-01T10:00:00+00:00",
        "kickoff_at": "2026-01-01T12:00:00+00:00",
        "market": "ou2.5",
        "selection": "under",
        "captured_odds": 2.0,
        "odds_captured_at": "2026-01-01T10:01:00+00:00",
        "bookmaker": "x",
        "source": "s",
        "source_event_id": "e1",
        "canonical_match_id": "c1",
        "closing_definition_version": "v1",
        "data_quality_status": "ok",
    }
    row["provenance_hash"] = record_hash(row)
    picks = tmp_path / "picks.jsonl"
    results = tmp_path / "results.jsonl"
    picks.write_text(json.dumps(row) + "\n", encoding="utf-8")
    results.write_text("", encoding="utf-8")
    report = evaluate(picks, results)
    assert report["classification"]["PROSPECTIVE_ELIGIBLE"] == 1
    assert report["counts"]["matured"] == 0


def test_complete_test_only_lifecycle_is_rejected_in_production(tmp_path: Path):
    row = {
        "pick_id": "test-1",
        "trial_id": "h3",
        "model_version": "m1",
        "code_commit": "abc",
        "predicted_at": "2026-01-01T10:00:00+00:00",
        "kickoff_at": "2026-01-01T12:00:00+00:00",
        "market": "ou2.5",
        "selection": "under",
        "captured_odds": 2.0,
        "odds_captured_at": "2026-01-01T10:01:00+00:00",
        "bookmaker": "test",
        "source": "fixture",
        "source_event_id": "e1",
        "canonical_match_id": "c1",
        "closing_definition_version": "v1",
        "data_quality_status": "ok",
        "synthetic": True,
    }
    row["provenance_hash"] = record_hash(row)
    picks = tmp_path / "picks.jsonl"
    results = tmp_path / "results.jsonl"
    picks.write_text(json.dumps(row) + "\n", encoding="utf-8")
    results.write_text("", encoding="utf-8")
    report = evaluate(picks, results)
    assert report["classification"]["PROSPECTIVE_ELIGIBLE"] == 0
    assert report["rejections"]["non_production_record"] == 1


def test_verdict_inconclusive_below_min_sample():
    matured = [_matured_pick("p1", "m1", clv=0.05, pnl=0.5)]
    verdict = compute_verdict(matured, min_sample=100)
    assert verdict["verdict"] == "INCONCLUSIVE"
    assert verdict["capital_enabled"] is False
    assert verdict["clv_ci95"] is None


def test_verdict_go_when_clv_and_roi_clear_criteria():
    matured = [_matured_pick(f"p{i}", f"m{i}", clv=0.05, pnl=0.5) for i in range(10)]
    verdict = compute_verdict(matured, min_sample=10)
    assert verdict["verdict"] == "GO"
    assert verdict["capital_enabled"] is True
    assert verdict["clv_ci95"][0] > 0
    assert verdict["roi_ci95"][0] > -0.02


def test_verdict_no_go_when_clv_negative():
    matured = [_matured_pick(f"p{i}", f"m{i}", clv=-0.06, pnl=-1.0) for i in range(10)]
    verdict = compute_verdict(matured, min_sample=10)
    assert verdict["verdict"] == "NO_GO"
    assert verdict["capital_enabled"] is False


def test_verdict_clusters_by_game_not_by_pick():
    # 1 jogo com 9 picks levemente positivos + 1 jogo com 1 pick muito negativo:
    # sem cluster por jogo, a media simples pareceria positiva; com cluster
    # por jogo, o segundo jogo pesa igual ao primeiro (1 cluster vs 1 cluster).
    matured = [_matured_pick(f"p{i}", "m1", clv=0.01, pnl=0.05) for i in range(9)]
    matured.append(_matured_pick("p10", "m2", clv=-0.5, pnl=-1.0))
    verdict = compute_verdict(matured, min_sample=10)
    assert verdict["verdict"] == "NO_GO"


def test_evaluate_wires_verdict_into_report(tmp_path: Path):
    row = {
        "pick_id": "p1",
        "trial_id": "h3",
        "model_version": "m1",
        "code_commit": "abc",
        "predicted_at": "2026-01-01T10:00:00+00:00",
        "kickoff_at": "2026-01-01T12:00:00+00:00",
        "market": "ou2.5",
        "selection": "under",
        "captured_odds": 2.0,
        "odds_captured_at": "2026-01-01T10:01:00+00:00",
        "bookmaker": "x",
        "source": "s",
        "source_event_id": "e1",
        "canonical_match_id": "c1",
        "closing_definition_version": "v1",
        "data_quality_status": "ok",
    }
    row["provenance_hash"] = record_hash(row)
    result = {
        "pick_id": "p1",
        "source_event_id": "e1",
        "selection": "under",
        "result": "won",
        "settled_at": "2026-01-01T14:00:00+00:00",
        "settlement_status": "settled",
        "closing_odds": 1.8,
        "closing_captured_at": "2026-01-01T11:59:00+00:00",
        "closing_definition_version": "v1",
        "clv": 0.05,
        "pnl": 1.0,
    }
    result["provenance_hash"] = record_hash(result)
    picks = tmp_path / "picks.jsonl"
    results = tmp_path / "results.jsonl"
    picks.write_text(json.dumps(row) + "\n", encoding="utf-8")
    results.write_text(json.dumps(result) + "\n", encoding="utf-8")
    report = evaluate(picks, results, min_sample=1)
    assert report["counts"]["matured"] == 1
    assert report["verdict"] == "GO"
    assert report["capital_enabled"] is True
    assert report["verdict_detail"]["clv_ci95"] == [0.05, 0.05]
