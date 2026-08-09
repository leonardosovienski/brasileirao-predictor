from pathlib import Path

import pytest

from src.research.h9_shadow import emit, settle


def prediction():
    return {
        "event_id": "e1",
        "kickoff_at": "2026-08-10T18:00:00+00:00",
        "predicted_at": "2026-08-10T16:30:00+00:00",
        "p_over": 0.55,
    }


def quote(selection="over", odds=1.90, captured="2026-08-10T16:29:00+00:00"):
    return {
        "source_event_id": "e1",
        "bookmaker": "onexbet",
        "market": "ou2.5",
        "selection": selection,
        "decimal_odds": odds,
        "odds_captured_at": captured,
        "retrieved_at": captured,
    }


def test_emission_is_blocked_without_approved_bookmaker(tmp_path: Path):
    result = emit(prediction=prediction(), quotes=[quote()], approved_bookmaker=None, ledger=tmp_path / "h9.jsonl")
    assert result == {"status": "BLOCKED_NO_STABLE_BOOKMAKER", "capital_enabled": False}


def test_emit_and_same_book_settlement_are_idempotent(tmp_path: Path):
    ledger = tmp_path / "h9.jsonl"
    emitted = emit(prediction=prediction(), quotes=[quote(odds=1.90)], approved_bookmaker="onexbet", ledger=ledger)
    assert emitted["status"] == "EMITTED"
    duplicate = emit(prediction=prediction(), quotes=[quote()], approved_bookmaker="onexbet", ledger=ledger)
    assert duplicate["status"] == "ALREADY_EMITTED"
    closed = settle(
        event_id="e1",
        home_goals=2,
        away_goals=1,
        result_published_at="2026-08-10T20:00:00+00:00",
        closing_quotes=[quote(odds=1.80, captured="2026-08-10T17:59:00+00:00")],
        ledger=ledger,
    )
    assert closed["status"] == "SETTLED"
    assert closed["pnl_units"] == pytest.approx(0.9)
    assert closed["clv"] == pytest.approx((1.9 - 1.8) / 1.8)
    assert settle(
        event_id="e1",
        home_goals=2,
        away_goals=1,
        result_published_at="2026-08-10T20:00:00+00:00",
        closing_quotes=[quote(odds=1.8)],
        ledger=ledger,
    )["status"] == "ALREADY_SETTLED"


def test_rejects_early_result_and_other_book_closing(tmp_path: Path):
    ledger = tmp_path / "h9.jsonl"
    emit(prediction=prediction(), quotes=[quote()], approved_bookmaker="onexbet", ledger=ledger)
    with pytest.raises(ValueError, match="not stable"):
        settle(
            event_id="e1",
            home_goals=1,
            away_goals=0,
            result_published_at="2026-08-10T19:00:00+00:00",
            closing_quotes=[quote()],
            ledger=ledger,
        )
