import json
import math

import pytest

from brasileirao_predictor import bet_log


@pytest.mark.parametrize(
    "changes",
    [
        {"odds": math.nan},
        {"odds": math.inf},
        {"stake": math.nan},
        {"stake": True},
        {"selection": "unknown"},
        {"model_prob": 1.3},
    ],
)
def test_invalid_bet_cannot_enter_journal(tmp_path, changes):
    args = {"home": "A", "away": "B", "market": "ou15", "selection": "over", "odds": 2.0, **changes}
    with pytest.raises(ValueError):
        bet_log.add_bet(**args, path=tmp_path / "bets.jsonl")
    assert not (tmp_path / "bets.jsonl").exists()


def test_stable_bet_id_survives_line_reordering_in_list_and_bank(tmp_path):
    bets, bank = tmp_path / "bets.jsonl", tmp_path / "bank.jsonl"
    bet_log.bank_init(100, 1, path=bank, at="2024-01-01T00:00:00Z")
    bet_log.add_bet("A", "B", "ou15", "over", 2, path=bets, bet_id="settled", logged_at="2024-01-02T00:00:00Z")
    bet_log.settle_bet("A", "B", 2, 0, path=bets, recorded_at="2024-01-03T00:00:00Z")
    old_rows = bets.read_text(encoding="utf-8")
    extra = {
        "kind": "bet",
        "bet_id": "still-open",
        "home": "C",
        "away": "D",
        "market": "ou15",
        "selection": "over",
        "stake": 3,
        "odds": 2,
        "logged_at": "2024-01-02T00:00:00Z",
    }
    bets.write_text(json.dumps(extra) + "\n" + old_rows, encoding="utf-8")
    by_id = {row["bet_id"]: row for row in bet_log.list_bets(bets)}
    assert by_id["settled"]["result"] is not None
    assert by_id["still-open"]["result"] is None
    state = bet_log.bank_state(bank, bets)
    assert state is not None and state["open_units"] == 3


def test_duplicate_bet_id_is_rejected_before_append(tmp_path):
    path = tmp_path / "bets.jsonl"
    bet_log.add_bet("A", "B", "ou15", "over", 2, path=path, bet_id="same")
    with pytest.raises(ValueError, match="bet_id"):
        bet_log.add_bet("C", "D", "ou15", "under", 2, path=path, bet_id="same")
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_invalid_half_time_each_side_rejected_before_any_settlement(tmp_path):
    path = tmp_path / "bets.jsonl"
    bet_log.add_bet("A", "B", "ou05_2t", "over", 2, path=path)
    with pytest.raises(ValueError):
        bet_log.settle_bet("A", "B", 0, 2, ht=(1, 0), path=path)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1
