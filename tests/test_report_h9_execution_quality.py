"""report_h9_execution_quality: taxas de disponibilidade e slippage vs melhor
preço, calculadas por JOGO (não por linha bruta) a partir do que
emit_h9_shadow.py já gravou a cada tentativa."""

import json
from pathlib import Path

from scripts.report_h9_execution_quality import report


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_empty_ledger_reports_none_rates(tmp_path):
    out = report(tmp_path / "nao_existe.jsonl")
    assert out["total_raw_evaluations"] == 0
    assert out["total_games"] == 0
    assert out["emission_rate"] is None
    assert out["slippage_vs_best_price"]["n"] == 0


def test_rates_reflect_one_game_each(tmp_path):
    path = tmp_path / "attempts.jsonl"
    _write(
        path,
        [
            {"event_id": "e1", "status": "EMITTED", "slippage_vs_best": 0.0},
            {"event_id": "e2", "status": "EMITTED", "slippage_vs_best": -0.1},
            {"event_id": "e3", "status": "BLOCKED_NO_STABLE_BOOKMAKER"},
            {"event_id": "e4", "status": "NO_EXECUTABLE_QUOTE"},
        ],
    )
    out = report(path)
    assert out["total_raw_evaluations"] == 4
    assert out["total_games"] == 4
    assert out["emission_rate"] == 0.5
    assert out["blocked_no_stable_bookmaker_rate"] == 0.25
    assert out["no_executable_quote_rate"] == 0.25
    assert out["slippage_vs_best_price"]["n"] == 2
    assert out["slippage_vs_best_price"]["mean"] == -0.05
    assert out["slippage_vs_best_price"]["matched_or_beat_best_rate"] == 0.5


def test_non_emitted_rows_never_pollute_slippage_stats(tmp_path):
    path = tmp_path / "attempts.jsonl"
    _write(
        path,
        [
            {"event_id": "e1", "status": "BLOCKED_NO_STABLE_BOOKMAKER"},
            {"event_id": "e2", "status": "NO_EXECUTABLE_QUOTE"},
        ],
    )
    out = report(path)
    assert out["slippage_vs_best_price"] == {"n": 0, "mean": None, "median": None, "matched_or_beat_best_rate": None}


def test_repeated_ticks_of_the_same_game_count_once_as_emitted(tmp_path):
    # o mesmo jogo, avaliado a cada ~15min dentro da janela de decisao: falha
    # duas vezes (sem cotacao ainda), emite na 3a tentativa, depois aparece
    # ALREADY_EMITTED nos ticks seguintes. Isso e' UM jogo emitido, nao 5
    # avaliacoes das quais 40% "falharam" -- diluir a taxa assim mascararia
    # que o jogo emitiu no fim das contas.
    path = tmp_path / "attempts.jsonl"
    _write(
        path,
        [
            {"event_id": "e1", "status": "NO_EXECUTABLE_QUOTE"},
            {"event_id": "e1", "status": "NO_EXECUTABLE_QUOTE"},
            {"event_id": "e1", "status": "EMITTED", "slippage_vs_best": 0.02},
            {"event_id": "e1", "status": "ALREADY_EMITTED"},
            {"event_id": "e1", "status": "ALREADY_EMITTED"},
        ],
    )
    out = report(path)
    assert out["total_raw_evaluations"] == 5
    assert out["total_games"] == 1
    assert out["status_counts"] == {"EMITTED": 1}
    assert out["emission_rate"] == 1.0
    assert out["slippage_vs_best_price"]["n"] == 1


def test_game_that_never_gets_a_quote_counts_its_last_seen_status(tmp_path):
    path = tmp_path / "attempts.jsonl"
    _write(
        path,
        [
            {"event_id": "e1", "status": "BLOCKED_NO_STABLE_BOOKMAKER"},
            {"event_id": "e1", "status": "NO_EXECUTABLE_QUOTE"},
        ],
    )
    out = report(path)
    assert out["total_raw_evaluations"] == 2
    assert out["total_games"] == 1
    assert out["status_counts"] == {"NO_EXECUTABLE_QUOTE": 1}


def test_rows_without_event_id_are_ignored(tmp_path):
    path = tmp_path / "attempts.jsonl"
    _write(path, [{"status": "EMITTED", "slippage_vs_best": 0.0}])
    out = report(path)
    assert out["total_games"] == 0
