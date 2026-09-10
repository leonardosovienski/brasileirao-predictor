"""Synthetic manual books; never access operational ledgers or financial services."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from brasileirao_predictor import bet_log

STAMP = "2024-01-01T12:00:00Z"


@pytest.mark.parametrize("operation", ["settle", "add"])
def test_concurrent_writers_cannot_duplicate_identity(tmp_path, monkeypatch, operation):
    path = tmp_path / "bets.jsonl"
    bet_log.add_bet("A", "B", "ou25", "over", 2, path=path, bet_id="first")
    original_read = bet_log._read
    entered, release = threading.Event(), threading.Event()
    owner = []

    def paused_read(*args, **kwargs):
        rows = original_read(*args, **kwargs)
        if threading.get_ident() == owner[0]:
            entered.set()
            assert release.wait(5), "contending writer did not finish"
        return rows

    def action():
        if operation == "settle":
            return bet_log.settle_bet("A", "B", 3, 0, path=path)
        return bet_log.add_bet("C", "D", "ou25", "over", 2, path=path, bet_id="second")

    def first():
        owner.append(threading.get_ident())
        return action()

    monkeypatch.setattr(bet_log, "_read", paused_read)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(first)
        assert entered.wait(5)
        try:
            with pytest.raises(OSError):
                action()
        finally:
            release.set()
        future.result(timeout=5)
    rows = original_read(path)
    assert len(rows) == 2
    assert len(bet_log.list_bets(path)) == (1 if operation == "settle" else 2)


def test_append_preserves_unterminated_valid_record(tmp_path):
    path = tmp_path / "bets.jsonl"
    bet_log.add_bet("A", "B", "ou25", "over", 2, path=path)
    original = path.read_bytes().rstrip(b"\r\n")
    path.write_bytes(original)
    bet_log.add_bet("C", "D", "ou25", "over", 2, path=path)
    assert path.read_bytes().startswith(original)
    assert len(bet_log.list_bets(path)) == 2


def test_bank_uses_one_snapshot_for_profit_and_exposure(tmp_path, monkeypatch):
    bank, bets = tmp_path / "bank.jsonl", tmp_path / "bets.jsonl"
    bet_log.bank_init(100, 1, path=bank, at=STAMP)
    bet_log.add_bet("A", "B", "ou25", "over", 2, path=bets, logged_at=STAMP)
    snapshot = bet_log._read(bets)
    bet_log.settle_bet("A", "B", 3, 0, path=bets, recorded_at=STAMP)
    settled_snapshot = bet_log._read(bets)
    calls = []

    def changing_read(*args, **kwargs):
        calls.append(1)
        return snapshot if len(calls) == 1 else settled_snapshot

    monkeypatch.setattr(bet_log, "_read", changing_read)
    state = bet_log.bank_state(bank, bets)
    assert state is not None
    assert state["balance"] == 100 and state["open_units"] == 1
    assert len(calls) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"amount": -100},
        {"amount": True},
        {"unit": -1},
        {"unit": float("nan")},
        {"currency": ""},
        {"kind": "typo"},
        {"at": "2024-01-01T12:00:00"},
    ],
)
def test_imported_invalid_bank_record_is_rejected(tmp_path, change):
    bank = tmp_path / "bank.jsonl"
    record = {"kind": "init", "amount": 100, "unit": 1, "currency": "BRL", "at": STAMP, **change}
    bank.write_text(json.dumps(record) + "\n")
    with pytest.raises(ValueError):
        bet_log.bank_state(bank, tmp_path / "bets.jsonl")


def test_bank_duplicate_json_key_is_rejected(tmp_path):
    bank = tmp_path / "bank.jsonl"
    bank.write_text('{"kind":"init","amount":100,"amount":500,"unit":1,"at":"' + STAMP + '"}\n')
    with pytest.raises(ValueError):
        bet_log.bank_state(bank, tmp_path / "bets.jsonl")


@pytest.mark.parametrize("change", [{"period": "3T"}, {"line": 0.5}, {"selection": "anything"}])
def test_invalid_imported_contract_cannot_be_settled(tmp_path, change):
    path = tmp_path / "bets.jsonl"
    record = bet_log.add_bet("A", "B", "ou25", "over", 2, path=path)
    path.write_text(json.dumps({**record, **change}) + "\n")
    original = path.read_bytes()
    with pytest.raises(ValueError):
        bet_log.settle_bet("A", "B", 3, 0, ht=(1, 0), path=path)
    assert path.read_bytes() == original


def test_reversed_team_input_keeps_score_in_recorded_home_order(tmp_path):
    path = tmp_path / "bets.jsonl"
    bet_log.add_bet("A", "B", "ou05_1t", "over", 2, path=path)
    record = bet_log.settle_bet("B", "A", 3, 1, ht=(2, 0), path=path)[0]
    assert record["home"] == "A" and record["away"] == "B"
    assert record["score"] == "1-3" and record["ht"] == "0-2"


@pytest.mark.parametrize("cap", ["NaN", "Infinity", "-1", ""])
def test_invalid_configured_stake_cap_is_rejected(tmp_path, monkeypatch, cap):
    monkeypatch.setenv("BETLOG_MAX_INFO_STAKE", cap)
    with pytest.raises(ValueError):
        bet_log.add_bet("A", "B", "ou15", "over", 2, path=tmp_path / "bets.jsonl")


def test_stable_id_does_not_require_legacy_line_number(tmp_path):
    path = tmp_path / "bets.jsonl"
    bet_log.add_bet("A", "B", "ou25", "over", 2, path=path)
    bet_log.settle_bet("A", "B", 3, 0, path=path)
    rows = bet_log._read(path)
    rows[-1].pop("bet_line_no")
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    assert bet_log.settle_bet("A", "B", 3, 0, path=path) == []


def test_cli_does_not_promote_legacy_market_flag(tmp_path, monkeypatch, capsys):
    path = tmp_path / "bets.jsonl"
    bet_log.add_bet("A", "B", "ou25", "over", 2, path=path)
    bet_log.settle_bet("A", "B", 3, 0, path=path)
    monkeypatch.setenv("BETS_LOG_PATH", str(path))
    monkeypatch.setattr("sys.argv", ["bet_log", "summary"])
    bet_log.main()
    output = capsys.readouterr().out
    assert "CLV comprovado" not in output
    assert "relatos manuais brutos" in output.lower()


def test_failed_append_releases_writer_lock(tmp_path, monkeypatch):
    path = tmp_path / "bets.jsonl"
    original = bet_log._append
    with monkeypatch.context() as patch:

        def fail(*args, **kwargs):
            raise OSError("synthetic write failure")

        patch.setattr(bet_log, "_append", fail)
        with pytest.raises(OSError):
            bet_log.add_bet("A", "B", "ou25", "over", 2, path=path)
    assert bet_log._append is original
    bet_log.add_bet("A", "B", "ou25", "over", 2, path=path)
    assert len(bet_log.list_bets(path)) == 1
