"""Hostile synthetic states only; no provider or existing fixture data opened."""

from __future__ import annotations

import copy
import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest


SPEC = importlib.util.spec_from_file_location("price_replay", Path(__file__).with_name("price_discovery_replay.py"))
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)
NOW = datetime(2026, 2, 1, 12, tzinfo=UTC)
KICKOFF = NOW + timedelta(hours=1)


def state(at=NOW, *, price=3.0, active=True):
    return {"createdAt": at.isoformat(), "price": price, "active": active}


def book(rows=None):
    rows = rows if rows is not None else [state()]
    return {"markets": {"101": {"outcomes": {oid: {"players": {"0": copy.deepcopy(rows)}} for oid in replay.OUTCOME_IDS}}}}


def timeline(target_book, side="101"):
    return target_book["markets"]["101"]["outcomes"][side]["players"]["0"]


@pytest.mark.parametrize("reverse", [False, True])
def test_latest_suspension_never_resurrects_older_quote(reverse):
    rows = [state(NOW - timedelta(minutes=1)), state(active=False), state(NOW + timedelta(seconds=1), price=4)]
    snapshot = replay.market_snapshot(book(list(reversed(rows)) if reverse else rows), NOW, KICKOFF)
    assert not snapshot["eligible"]
    assert "INACTIVE_STATE" in snapshot["reasons"][0]


@pytest.mark.parametrize("mutate", ["active_false", "active_missing", "price_conflict"])
@pytest.mark.parametrize("reverse", [False, True])
def test_equal_time_conflicts_and_missing_active_reject(mutate, reverse):
    first, second = state(), state()
    if mutate == "active_false":
        second["active"] = False
    elif mutate == "active_missing":
        del second["active"]
    else:
        second["price"] = 4.0
    snapshot = replay.market_snapshot(book([second, first] if reverse else [first, second]), NOW, KICKOFF)
    assert not snapshot["eligible"]
    assert all("CONFLICTING_STATE" in reason for reason in snapshot["reasons"])


def test_future_states_ignored_identical_ties_and_reactivation_accepted():
    rows = [state(NOW - timedelta(minutes=1), active=False), state(), state(), state(NOW + timedelta(seconds=1), price=20, active=False)]
    snapshot = replay.market_snapshot(book(rows), NOW, KICKOFF)
    assert snapshot["eligible"]
    assert snapshot["odds"] == [3.0] * 3
    assert snapshot["q"] == pytest.approx([1 / 3] * 3)


def test_untimestamped_current_global_status_does_not_leak_post_match_state():
    quoted = book()
    quoted.update(bookmakerIsActive=False, suspended=True, status="closed")
    assert replay.market_snapshot(quoted, NOW, KICKOFF)["eligible"]


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), 1.0, 20.01, None])
def test_invalid_latest_price_cannot_fall_back_to_older_valid_price(bad):
    snapshot = replay.market_snapshot(book([state(NOW - timedelta(seconds=1)), state(price=bad)]), NOW, KICKOFF)
    assert not snapshot["eligible"]


def test_price_age_inclusive_boundary_and_oldest_leg_guard():
    boundary = book([state(NOW - timedelta(hours=6))])
    assert replay.market_snapshot(boundary, NOW, KICKOFF)["eligible"]
    timeline(boundary, "102")[0]["createdAt"] = (NOW - timedelta(hours=6, seconds=1)).isoformat()
    assert not replay.market_snapshot(boundary, NOW, KICKOFF)["eligible"]


def test_missing_leg_invalid_timestamp_missing_active_and_booksum_reject():
    missing = book()
    del missing["markets"]["101"]["outcomes"]["102"]
    assert not replay.market_snapshot(missing, NOW, KICKOFF)["eligible"]
    malformed = book()
    timeline(malformed)[0]["createdAt"] = "2026-02-01T12:00:00"
    assert not replay.market_snapshot(malformed, NOW, KICKOFF)["eligible"]
    inactive_unknown = book()
    del timeline(inactive_unknown)[0]["active"]
    assert not replay.market_snapshot(inactive_unknown, NOW, KICKOFF)["eligible"]
    assert not replay.market_snapshot(book([state(price=2)]), NOW, KICKOFF)["eligible"]
    assert not replay.market_snapshot(book([state(price=4)]), NOW, KICKOFF)["eligible"]
    assert not replay.market_snapshot(book(), KICKOFF, KICKOFF)["eligible"]


def synthetic_input():
    selection, histories = [], {}
    first = datetime(2026, 1, 3, 20, tzinfo=UTC)
    for i in range(30):
        fixture_id = str(i)
        kickoff = first + timedelta(days=i * 4)
        selection.append({"fixture_id": fixture_id, "kickoff_at": kickoff.isoformat(), "home": "A", "away": "B", "status": "Finished"})
        q6 = np.array([0.45, 0.30, 0.25])
        momentum = np.array([0.005 + i * 0.0001, -0.003, -0.002 - i * 0.0001])
        q1 = q6 + momentum
        q10 = q1 + 0.4 * momentum
        b1 = q1 + np.array([-0.015, 0.008, 0.007])
        books = {}
        for name in replay.BOOKS:
            quotes = {"T6H": q6, "T1H": q1 if name == "pinnacle" else b1, "T10M": q10}
            quote_book = book([])
            for window, probs in quotes.items():
                at = kickoff - replay.WINDOWS[window]
                for oid, probability in zip(replay.OUTCOME_IDS, probs, strict=True):
                    timeline(quote_book, oid).append(state(at, price=float(1 / (probability * 1.01))))
            books[name] = quote_book
        histories[fixture_id] = {"fixtureId": fixture_id, "bookmakers": books}
    return selection, histories


def test_fixed_id_split_is_not_reassigned_after_missingness():
    selection, histories = synthetic_input()
    del histories["0"]
    del histories["21"]
    result = replay.evaluate(selection, histories)
    primary = result["primary_B"]
    assert primary["train_n"] == 19 and primary["test_n"] == 9
    assert {row["fixture_id"] for row in primary["per_test_event"]} == {str(i) for i in range(20, 30) if i != 21}
    assert all(metric["n"] == 9 for metric in primary["model_metrics"].values())
    excluded = result["coverage_panels"]["common_primary"]["excluded"]
    assert {(row["fixture_id"], row["split"]) for row in excluded} == {("0", "train"), ("21", "test")}


def test_test_target_mutation_cannot_change_coefficients_or_forecasts():
    selection, histories = synthetic_input()
    baseline = replay.evaluate(selection, histories)
    changed = copy.deepcopy(histories)
    for i in range(20, 30):
        for oid, prob in zip(replay.OUTCOME_IDS, (0.35, 0.30, 0.35), strict=True):
            timeline(changed[str(i)]["bookmakers"]["pinnacle"], oid)[-1]["price"] = 1 / (prob * 1.01)
    altered = replay.evaluate(selection, changed)
    assert baseline["primary_B"]["coefficients"] == altered["primary_B"]["coefficients"]
    for left, right in zip(baseline["primary_B"]["per_test_event"], altered["primary_B"]["per_test_event"], strict=True):
        for name in replay.MODELS:
            assert left["models"][name]["q_forecast"] == right["models"][name]["q_forecast"]
    assert baseline["primary_B"]["model_metrics"]["persistence"]["mean_mse"] != altered["primary_B"]["model_metrics"]["persistence"]["mean_mse"]


def test_insufficient_common_panel_prevents_any_fit(monkeypatch):
    selection, histories = synthetic_input()
    for i in range(6):
        del histories[str(20 + i)]["bookmakers"]["bet365"]
    monkeypatch.setattr(replay, "fit_ridge", lambda *a, **kw: pytest.fail("Fit attempted below declared sample minimum"))
    result = replay.evaluate(selection, histories)
    assert result["primary_B"]["status"] == "INSUFFICIENT_DATA"
    assert result["primary_B"]["model_metrics"] is None
    assert result["coverage_panels"]["persistence"]["eligible_test_n"] == 10
    assert result["coverage_panels"]["common_primary"]["eligible_test_n"] == 4


def test_ridge_matches_stacked_closed_form_and_probabilities_normalized():
    selection, histories = synthetic_input()
    result = replay.evaluate(selection, histories)
    training = result["snapshots"][:20]
    xs, ys = [], []
    for row in training:
        p6 = np.array(row["snapshots"]["pinnacle"]["T6H"]["q"])
        p1 = np.array(row["snapshots"]["pinnacle"]["T1H"]["q"])
        p10 = np.array(row["snapshots"]["pinnacle"]["T10M"]["q"])
        xs.extend(p1 - p6)
        ys.extend(p10 - p1)
    expected = np.dot(xs, ys) / (np.dot(xs, xs) + 1e-4)
    assert result["primary_B"]["coefficients"]["ridge_momentum"] == pytest.approx([expected])
    for row in result["primary_B"]["per_test_event"]:
        for model in row["models"].values():
            assert sum(model["q_forecast"]) == pytest.approx(1)
            assert all(0 < q < 1 for q in model["q_forecast"])
    assert replay.normalized([-100, 0, 1]).sum() == pytest.approx(1)


def test_secondary_checks_same_selection_without_resurrecting_suspended_quote():
    selection, histories = synthetic_input()
    kickoff = replay.dt(selection[0]["kickoff_at"])
    followup = kickoff - timedelta(minutes=55)
    # Synthetic reference/soft disparity yields a home candidate.
    pin_q = 0.455
    target_book = histories["0"]["bookmakers"]["bet365"]
    home_before = next(row for row in timeline(target_book) if replay.dt(row["createdAt"]) == kickoff - timedelta(hours=1))
    assert pin_q * home_before["price"] - 1 > 0.02
    timeline(target_book).append(state(followup, active=False))
    timeline(target_book).append(state(followup + timedelta(seconds=1), active=True))
    result = replay.evaluate(selection, histories)
    row = result["secondary_C"]["observations"][0]
    assert row["selection"] == "home"
    assert row["status"] == "FOLLOWUP_UNAVAILABLE"
    assert row["reasons"] == ["INACTIVE_STATE"]
    assert not row["premium_retained_observed"]
    assert result["primary_B"]["train_n"] == 20
    assert result["primary_B"]["test_n"] == 10


def test_extra_fixture_or_unapproved_date_rejected():
    selection, histories = synthetic_input()
    with pytest.raises(ValueError, match="outside"):
        replay.evaluate(selection, {**histories, "protected": {}})
    selection[0]["kickoff_at"] = "2025-12-31T20:00:00Z"
    with pytest.raises(ValueError, match="January--June"):
        replay.evaluate(selection, histories)


@pytest.mark.parametrize("gap_minutes,purged", [(0, True), (49, True), (50, True), (51, False)])
def test_training_boundary_purges_targets_not_yet_available_without_moving_ids(gap_minutes, purged):
    selection, histories = synthetic_input()
    old_kickoff = replay.dt(selection[19]["kickoff_at"])
    new_kickoff = replay.dt(selection[20]["kickoff_at"]) - timedelta(minutes=gap_minutes)
    delta = new_kickoff - old_kickoff
    selection[19]["kickoff_at"] = new_kickoff.isoformat()
    for quote_book in histories["19"]["bookmakers"].values():
        for oid in replay.OUTCOME_IDS:
            for row in timeline(quote_book, oid):
                row["createdAt"] = (replay.dt(row["createdAt"]) + delta).isoformat()
    result = replay.evaluate(selection, histories)
    assert result["primary_B"]["purged_boundary_ids"] == (["19"] if purged else [])
    assert result["primary_B"]["train_n"] == (19 if purged else 20)
    assert {row["fixture_id"] for row in result["primary_B"]["per_test_event"]} == {str(i) for i in range(20, 30)}
    if purged:
        changed = copy.deepcopy(histories)
        for oid, probability in zip(replay.OUTCOME_IDS, (0.7, 0.15, 0.15), strict=True):
            timeline(changed["19"]["bookmakers"]["pinnacle"], oid)[-1]["price"] = 1 / (probability * 1.01)
        altered = replay.evaluate(selection, changed)
        assert result["primary_B"]["coefficients"] == altered["primary_B"]["coefficients"]


def test_mismatched_raw_identity_excluded_without_using_its_quotes():
    selection, histories = synthetic_input()
    histories["0"]["fixtureId"] = "wrong-id"
    result = replay.evaluate(selection, histories)
    rejected = result["coverage_panels"]["common_primary"]["excluded"][0]
    assert rejected["fixture_id"] == "0"
    assert all("HISTORY_FIXTURE_ID_MISMATCH" in reason for reason in rejected["reasons"])


def test_purge_uses_first_fixed_test_decision_even_when_that_history_is_missing():
    selection, histories = synthetic_input()
    original = replay.dt(selection[19]["kickoff_at"])
    updated = replay.dt(selection[20]["kickoff_at"]) - timedelta(minutes=20)
    shift = updated - original
    selection[19]["kickoff_at"] = updated.isoformat()
    for quoted in histories["19"]["bookmakers"].values():
        for oid in replay.OUTCOME_IDS:
            for row in timeline(quoted, oid):
                row["createdAt"] = (replay.dt(row["createdAt"]) + shift).isoformat()
    del histories["20"]
    result = replay.evaluate(selection, histories)
    assert result["primary_B"]["purged_boundary_ids"] == ["19"]
    assert result["primary_B"]["train_n"] == 19
    assert result["primary_B"]["test_n"] == 9
    missing = next(row for row in result["coverage_panels"]["common_primary"]["excluded"] if row["fixture_id"] == "20")
    assert all("HISTORY_NOT_AVAILABLE" in reason for reason in missing["reasons"])
