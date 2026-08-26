import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from paper_ledger import PaperLedger

CAPTURED = datetime(2026, 8, 20, 17, 0, tzinfo=UTC)
KICKOFF = CAPTURED + timedelta(hours=2)


def register(ledger, stake=1.0, captured=CAPTURED):
    return ledger.registrar_aposta("event-1", "1X2", "home", "soft-book", 2.1, captured, KICKOFF, stake)


def test_flat_stake_and_timezone_are_required(tmp_path):
    ledger = PaperLedger(tmp_path / "ledger.jsonl")

    with pytest.raises(ValueError, match="stake flat"):
        register(ledger, stake=2.0)
    with pytest.raises(ValueError, match="timezone"):
        register(ledger, captured=CAPTURED.replace(tzinfo=None))


def test_updates_preserve_append_only_hash_chain(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = PaperLedger(path)
    register(ledger)
    ledger.registrar_fechamento("event-1", "1X2", "home", 2.0)
    ledger.liquidar("event-1", "1X2", "home", True)

    lines = path.read_text().splitlines()
    assert len(lines) == 3
    raw = [json.loads(line) for line in lines]
    assert [record["type"] for record in raw] == ["bet", "update", "update"]
    assert raw[1]["hash_prev"] == hashlib.sha256(lines[0].encode()).hexdigest()[:16]
    assert ledger._load()[0]["ret"] == pytest.approx(1.1)


def test_closing_and_settlement_require_valid_state(tmp_path):
    ledger = PaperLedger(tmp_path / "ledger.jsonl")
    register(ledger)

    with pytest.raises(ValueError, match="closing_odd"):
        ledger.registrar_fechamento("event-1", "1X2", "home", 1.0)
    with pytest.raises(ValueError, match="closing_odd"):
        ledger.liquidar("event-1", "1X2", "home", True)

    ledger.registrar_fechamento("event-1", "1X2", "home", 2.0)
    ledger.liquidar("event-1", "1X2", "home", True)
    with pytest.raises(ValueError, match="já liquidada"):
        ledger.liquidar("event-1", "1X2", "home", True)
