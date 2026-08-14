"""report_h9_execution_quality: taxas de disponibilidade e slippage vs melhor
preço, calculadas só a partir do que emit_h9_shadow.py já gravou."""

import json
from pathlib import Path

from scripts.report_h9_execution_quality import report


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_empty_ledger_reports_none_rates(tmp_path):
    out = report(tmp_path / "nao_existe.jsonl")
    assert out["total_evaluations"] == 0
    assert out["emission_rate"] is None
    assert out["slippage_vs_best_price"]["n"] == 0


def test_rates_reflect_status_mix(tmp_path):
    path = tmp_path / "attempts.jsonl"
    _write(
        path,
        [
            {"status": "EMITTED", "slippage_vs_best": 0.0},
            {"status": "EMITTED", "slippage_vs_best": -0.1},
            {"status": "BLOCKED_NO_STABLE_BOOKMAKER"},
            {"status": "NO_EXECUTABLE_QUOTE"},
        ],
    )
    out = report(path)
    assert out["total_evaluations"] == 4
    assert out["emission_rate"] == 0.5
    assert out["blocked_no_stable_bookmaker_rate"] == 0.25
    assert out["no_executable_quote_rate"] == 0.25
    assert out["slippage_vs_best_price"]["n"] == 2
    assert out["slippage_vs_best_price"]["mean"] == -0.05
    assert out["slippage_vs_best_price"]["matched_or_beat_best_rate"] == 0.5


def test_non_emitted_rows_never_pollute_slippage_stats(tmp_path):
    path = tmp_path / "attempts.jsonl"
    _write(path, [{"status": "BLOCKED_NO_STABLE_BOOKMAKER"}, {"status": "NO_EXECUTABLE_QUOTE"}])
    out = report(path)
    assert out["slippage_vs_best_price"] == {"n": 0, "mean": None, "median": None, "matched_or_beat_best_rate": None}
