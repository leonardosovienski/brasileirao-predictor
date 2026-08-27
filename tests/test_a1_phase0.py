from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.a1_phase0 import (
    Phase0Ledger,
    clv_required_sample_size,
    conservative_reference,
    phase0_report,
    policy_fingerprint,
)


def _row(book: str, selection: str, odds: float) -> dict[str, object]:
    return {
        "event_id": "event-1",
        "bookmaker": book,
        "market": "ou2.5",
        "line": 2.5,
        "selection": selection,
        "odds": odds,
        "status": "active",
        "captured_at": "2026-08-27T20:00:00Z",
    }


def test_fingerprint_changes_with_policy_or_code(tmp_path: Path) -> None:
    policy = tmp_path / "policy.json"
    code = tmp_path / "code.py"
    policy.write_text('{"policy_id":"a1"}', encoding="utf-8")
    code.write_text("x=1\n", encoding="utf-8")
    first = policy_fingerprint(policy, [code])["fingerprint"]
    code.write_text("x=2\n", encoding="utf-8")
    assert policy_fingerprint(policy, [code])["fingerprint"] != first


def test_phase0_ledger_is_append_only_and_rejects_labels(tmp_path: Path) -> None:
    ledger = Phase0Ledger(tmp_path / "observations.jsonl", "abc")
    ledger.append({"requests": 1, "latency_ms": 20})
    ledger.append({"requests": 2, "availability": True})
    assert ledger.verify() is True
    with pytest.raises(ValueError, match="closing_odds"):
        ledger.append({"nested": {"closing_odds": 1.9}})


def test_phase0_ledger_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "observations.jsonl"
    ledger = Phase0Ledger(path, "abc")
    ledger.append({"requests": 1})
    path.write_text(path.read_text(encoding="utf-8").replace('"requests": 1', '"requests": 9'), encoding="utf-8")
    assert ledger.verify() is False


def test_conservative_reference_uses_complete_pairs_and_multiple_devigs() -> None:
    result = conservative_reference(
        [_row("pinnacle", "over", 1.9), _row("pinnacle", "under", 2.0), _row("pinnacle", "over", 1.8)],
        {"pinnacle"},
    )
    assert result is not None
    assert result["complete_reference_pairs"] == 1
    assert result["p_range"]["over"][0] <= result["p_range"]["over"][1]
    assert "not a confidence interval" in result["method"]


def test_reference_never_pairs_different_events() -> None:
    over = _row("pinnacle", "over", 1.9)
    under = _row("pinnacle", "under", 2.0)
    under["event_id"] = "event-2"
    assert conservative_reference([over, under], {"pinnacle"}) is None


def test_report_contains_no_outcome_metrics() -> None:
    policy = {"reference_books": ["pinnacle"], "soft_books": ["soft"], "threshold_frozen": False}
    report = phase0_report([_row("pinnacle", "over", 1.9), _row("pinnacle", "under", 2.0)], policy)
    assert report["contains_outcomes"] is False
    assert {"roi", "clv", "pnl"}.isdisjoint(report)


def test_clv_power_is_derived_not_magic_number() -> None:
    assert clv_required_sample_size(0.10, 0.02) == 197
    assert clv_required_sample_size(0.10, 0.02, design_effect=2) == 393
    with pytest.raises(ValueError):
        clv_required_sample_size(0, 0.02)


def test_policy_is_label_free_and_capital_locked() -> None:
    root = Path(__file__).resolve().parent.parent
    policy = json.loads((root / "contracts" / "a1-ou25-phase0-policy.json").read_text(encoding="utf-8"))
    assert policy["scientific_state"] == "OPERATIONAL_CALIBRATION_NO_LABELS"
    assert policy["threshold_frozen"] is False
    assert policy["capital_enabled"] is False
    assert policy["kelly_enabled"] is False


def test_each_fingerprint_uses_an_independent_append_only_ledger(tmp_path: Path) -> None:
    first = Phase0Ledger(tmp_path / "observations-first.jsonl", "first")
    second = Phase0Ledger(tmp_path / "observations-second.jsonl", "second")
    first.append({"requests": 1})
    second.append({"requests": 2})
    assert first.verify() is True
    assert second.verify() is True
