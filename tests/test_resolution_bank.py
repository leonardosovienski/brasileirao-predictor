import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from brasileirao_predictor import bet_log as book


def test_bank_snapshot_locks_both_books(tmp_path, monkeypatch):
    bank, bets = tmp_path / "bank.jsonl", tmp_path / "bets.jsonl"
    book.bank_init(100, 1, path=bank, at="2024-01-01T00:00:00Z")
    original = book._read_bank
    entered, release = threading.Event(), threading.Event()
    owner = []

    def paused(path):
        rows = original(path)
        if threading.get_ident() == owner[0]:
            entered.set()
            assert release.wait(5)
        return rows

    def read():
        owner.append(threading.get_ident())
        return book.bank_state(bank, bets)

    monkeypatch.setattr(book, "_read_bank", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(read)
        assert entered.wait(5)
        try:
            with pytest.raises(OSError):
                book.bank_flow("deposit", 20, path=bank, at="2024-01-01T01:00:00Z")
        finally:
            release.set()
        state = future.result(timeout=5)
        assert state is not None and state["balance"] == 100


def test_old_stake_is_not_revalued_by_new_unit(tmp_path):
    bank, bets = tmp_path / "bank.jsonl", tmp_path / "bets.jsonl"
    book.bank_init(100, 1, path=bank, at="2024-01-01T00:00:00Z")
    book.add_bet("A", "B", "ou25", "over", 2, path=bets, logged_at="2024-01-01T01:00:00Z")
    book.bank_init(200, 10, path=bank, at="2024-01-02T00:00:00Z")
    state = book.bank_state(bank, bets)
    assert state is not None and state["open_money"] == 1
    book.settle_bet("A", "B", 3, 0, path=bets, recorded_at="2024-01-02T02:00:00Z")
    state = book.bank_state(bank, bets)
    assert state is not None and state["profit_money"] == 1


def test_currency_change_requires_reconciliation_for_old_open_stake(tmp_path):
    bank, bets = tmp_path / "bank.jsonl", tmp_path / "bets.jsonl"
    book.bank_init(100, 1, currency="BRL", path=bank, at="2024-01-01T00:00:00Z")
    book.add_bet("A", "B", "ou25", "over", 2, path=bets, logged_at="2024-01-01T01:00:00Z")
    book.bank_init(100, 1, currency="USD", path=bank, at="2024-01-02T00:00:00Z")
    state = book.bank_state(bank, bets)
    assert state is not None
    assert state["available_money"] is None
    assert state["valuation_status"] == "PENDING_RECONCILIATION"


def test_flow_requires_initial_bank_and_monotonic_clock(tmp_path):
    bank = tmp_path / "bank.jsonl"
    with pytest.raises(ValueError):
        book.bank_flow("deposit", 10, path=bank, at="2024-01-01T00:00:00Z")
    book.bank_init(100, 1, path=bank, at="2024-01-02T00:00:00Z")
    before = bank.read_bytes()
    with pytest.raises(ValueError):
        book.bank_flow("deposit", 10, path=bank, at="2024-01-01T00:00:00Z")
    assert bank.read_bytes() == before


def test_drawdown_accounts_for_time_of_contribution(tmp_path):
    bank, bets = tmp_path / "bank.jsonl", tmp_path / "bets.jsonl"
    book.bank_init(100, 10, path=bank, at="2024-01-01T00:00:00Z")
    book.add_bet("A", "B", "ou25", "over", 2, path=bets, logged_at="2024-01-01T01:00:00Z")
    book.settle_bet("A", "B", 0, 0, path=bets, recorded_at="2024-01-01T02:00:00Z")
    book.bank_flow("deposit", 1000, path=bank, at="2024-01-01T03:00:00Z")
    state = book.bank_state(bank, bets)
    assert state is not None
    assert state["max_drawdown_pct"] == pytest.approx(0.1)
    assert state["balance"] == 1090
