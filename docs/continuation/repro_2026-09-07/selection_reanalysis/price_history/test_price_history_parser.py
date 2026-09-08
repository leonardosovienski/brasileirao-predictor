"""Synthetic-only regressions; no provider calls or project datasets are read."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from exp001_data_pilot import _latest_at_cutoff

CUTOFF = datetime(2020, 1, 1, 12, tzinfo=UTC)


def _row(at, *, price=2.0, active=True):
    return {"createdAt": f"2020-01-01T{at}Z", "price": price, "active": active}


def _book(timeline):
    return {
        "markets": {"101": {"outcomes": {oid: {"players": {"0": deepcopy(timeline)}} for oid in ("101", "102", "103")}}}
    }


@pytest.mark.parametrize("reverse", [False, True])
def test_latest_inactive_state_does_not_resurrect_older_quote(reverse):
    rows = [_row("11:00:00"), _row("11:59:00", active=False)]
    book = _book(list(reversed(rows)) if reverse else rows)
    assert _latest_at_cutoff(book, CUTOFF) is None


def test_future_reactivation_cannot_undo_suspension_at_cutoff():
    rows = [_row("11:00:00"), _row("11:59:00", active=False), _row("12:01:00")]
    assert _latest_at_cutoff(_book(rows), CUTOFF) is None


def test_future_suspension_does_not_erase_current_quote():
    rows = [_row("11:59:00"), _row("12:01:00", active=False)]
    result = _latest_at_cutoff(_book(rows), CUTOFF)
    assert result is not None
    assert result["home_odds"] == 2.0
    assert result["snapshot_age_minutes"] == 1.0


def test_future_price_is_never_selected():
    rows = [_row("11:59:00"), _row("12:01:00", price=99)]
    result = _latest_at_cutoff(_book(rows), CUTOFF)
    assert result is not None
    assert [result[name] for name in ("home_odds", "draw_odds", "away_odds")] == [2.0] * 3


def test_future_only_has_no_eligible_quote():
    assert _latest_at_cutoff(_book([_row("12:01:00")]), CUTOFF) is None


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("conflict", ["active", "price"])
def test_equal_timestamp_conflict_fails_closed_independent_of_order(reverse, conflict):
    rows = [_row("11:59:00"), _row("11:59:00", active=False) if conflict == "active" else _row("11:59:00", price=3.0)]
    assert _latest_at_cutoff(_book(list(reversed(rows)) if reverse else rows), CUTOFF) is None


def test_equal_timestamp_identical_states_are_accepted():
    result = _latest_at_cutoff(_book([_row("11:59:00"), _row("11:59:00")]), CUTOFF)
    assert result is not None
    assert result["home_odds"] == 2.0


def test_missing_active_flag_is_not_proof_of_an_active_state():
    rows = [_row("11:00:00"), _row("11:59:00")]
    del rows[-1]["active"]
    assert _latest_at_cutoff(_book(rows), CUTOFF) is None


def test_suspension_of_one_leg_rejects_whole_1x2_quote():
    book = _book([_row("11:59:00")])
    book["markets"]["101"]["outcomes"]["102"]["players"]["0"].append(_row("12:00:00", active=False))
    assert _latest_at_cutoff(book, CUTOFF) is None


def test_missing_leg_fails_closed():
    book = _book([_row("11:59:00")])
    del book["markets"]["101"]["outcomes"]["102"]
    assert _latest_at_cutoff(book, CUTOFF) is None


def test_reactivation_before_cutoff_is_accepted():
    rows = [_row("11:00:00"), _row("11:30:00", active=False), _row("12:00:00", price=2.5)]
    result = _latest_at_cutoff(_book(rows), CUTOFF)
    assert result is not None
    assert result["home_odds"] == 2.5
    assert result["snapshot_age_minutes"] == 0.0
