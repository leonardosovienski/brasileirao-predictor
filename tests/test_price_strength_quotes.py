"""Synthetic price comparisons: no network, local fixtures or real database."""

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from brasileirao_predictor.research.price_strength.quotes import PricePolicy, scan_quotes

AS_OF = datetime(2030, 1, 1, 9, tzinfo=UTC)


def policy(**changes):
    return PricePolicy(
        **{
            "reference_books": ("reference",),
            "max_age_seconds": 300,
            "max_skew_seconds": 30,
            "cost_per_unit": 0.02,
            "commission_on_profit": 0.05,
            **changes,
        }
    )


def snapshot(book="reference", **changes):
    event = changes.get("event_id", "event")
    return {
        "snapshot_id": f"{event}-{book}",
        "source": "synthetic-provider",
        "source_event_id": f"source-{event}",
        "event_id": event,
        "bookmaker": book,
        "market": "ou25",
        "period": "FT",
        "line": 2.5,
        "kickoff_at": "2030-01-01T11:00:00Z",
        "observed_at": "2030-01-01T08:59:00Z",
        "available_at": "2030-01-01T08:59:01Z",
        "received_at": "2030-01-01T08:59:02Z",
        "status": "active",
        "odds": {"over": 1.9, "under": 1.9} if book == "reference" else {"over": 2.4, "under": 1.7},
        "raw_payload_hash": "a" * 64,
        "snapshot_scope": "complete_market",
        **changes,
    }


def evaluation(report, book="offer", side="over"):
    return next(row for row in report["evaluations"] if row["bookmaker"] == book and row.get("selection") == side)


def test_explicit_friction_and_independent_probability_have_reviewable_provenance():
    report = scan_quotes([snapshot(), snapshot("offer")], as_of=AS_OF, policy=policy())
    selected = report["selected_candidates"]
    assert len(selected) == 1
    assert selected[0]["reference_probability"] == pytest.approx(0.5)
    assert selected[0]["gross_ev"] == pytest.approx(0.2)
    assert selected[0]["net_ev"] == pytest.approx(0.145)
    assert selected[0]["reference_books_used"] == ["reference"]
    assert selected[0]["reference_provenance"][0]["odds"] == {"over": 1.9, "under": 1.9}
    assert report["status"] == "RESEARCH_ONLY"
    assert not report["capital_enabled"] and not report["execution_proven"]
    assert not selected[0]["provenance"]["source_authentication_proven"]
    assert not report["validation_errors"]
    json.dumps(report, allow_nan=False)


def test_offering_book_never_contributes_to_its_own_reference():
    report = scan_quotes(
        [snapshot(), snapshot("offer")],
        as_of=AS_OF,
        policy=policy(reference_books=("reference", "offer")),
    )
    offer = evaluation(report)
    assert offer["reference_probability"] == pytest.approx(0.5)
    assert {item["bookmaker"] for item in offer["reference_provenance"]} == {"reference"}
    assert {item["reason"] for item in offer["reference_exclusions"]} == {"offering_book_excluded_from_reference"}


def test_reference_book_cannot_self_validate_when_no_independent_reference_exists():
    report = scan_quotes([snapshot(odds={"over": 3, "under": 1.5})], as_of=AS_OF, policy=policy())
    assert not report["selected_candidates"]
    assert {row["reason"] for row in report["evaluations"]} == {"insufficient_independent_reference_books"}


@pytest.mark.parametrize("status", ["suspended", "unavailable"])
@pytest.mark.parametrize("book", ["offer", "reference"])
def test_latest_inactive_state_never_revives_older_prices(status, book):
    rows = [
        snapshot(),
        snapshot("offer"),
        snapshot(
            book,
            snapshot_id="new-state",
            status=status,
            odds={},
            observed_at="2030-01-01T08:59:30Z",
            available_at="2030-01-01T08:59:31Z",
            received_at="2030-01-01T08:59:32Z",
        ),
    ]
    report = scan_quotes(rows, as_of=AS_OF, policy=policy())
    assert not report["selected_candidates"]
    assert any(row["reason"] == f"latest_snapshot_{status}" for row in report["evaluations"])


@pytest.mark.parametrize(
    "changes",
    [
        {"odds": {"over": 5.0}},
        {"odds": {"over": None, "under": 1.9}},
        {"odds": {"over": float("nan"), "under": 1.9}},
        {"raw_payload_hash": "missing-evidence"},
        {"line": 3.5},
        {"period": "1H"},
    ],
)
def test_malformed_latest_state_blocks_old_valid_price(changes):
    invalid = snapshot("offer", snapshot_id="invalid-latest", received_at="2030-01-01T08:59:50Z", **changes)
    report = scan_quotes([snapshot(), snapshot("offer"), invalid], as_of=AS_OF, policy=policy())
    assert report["validation_errors"]
    assert not report["selected_candidates"]
    assert any(row["reason"] == "latest_snapshot_invalid" for row in report["evaluations"])
    json.dumps(report, allow_nan=False)


def test_unorderable_invalid_row_blocks_batch_without_fallback():
    invalid = snapshot("another-book", received_at="yesterday")
    report = scan_quotes([snapshot(), snapshot("offer"), invalid], as_of=AS_OF, policy=policy())
    assert report["batch_blocked"]
    assert report["validation_errors"]
    assert not report["selected_candidates"]


def test_future_receipt_does_not_change_a_past_decision():
    rows = [snapshot(), snapshot("offer")]
    before = scan_quotes(rows, as_of=AS_OF, policy=policy())
    rows.append(
        snapshot("offer", snapshot_id="future", status="suspended", odds={}, received_at="2030-01-01T09:01:00Z")
    )
    after = scan_quotes(rows, as_of=AS_OF, policy=policy())
    assert before["selected_candidates"] == after["selected_candidates"]
    assert after["snapshot_reviews"][-1]["reason"] == "received_after_as_of"


@pytest.mark.parametrize("clock", ["observed_at", "available_at", "received_at", "kickoff_at"])
def test_naive_snapshot_timestamps_are_reported_as_validation_errors(clock):
    report = scan_quotes([snapshot(**{clock: "2030-01-01T08:59:00"}), snapshot("offer")], as_of=AS_OF, policy=policy())
    assert report["validation_errors"]
    assert not report["selected_candidates"]


@pytest.mark.parametrize(
    "changes",
    [
        {"observed_at": "2030-01-01T08:59:02Z"},
        {"available_at": "2030-01-01T08:59:03Z"},
    ],
)
def test_clock_order_cannot_be_inverted(changes):
    report = scan_quotes([snapshot(**changes), snapshot("offer")], as_of=AS_OF, policy=policy())
    assert report["validation_errors"][0]["reason"] == "observation_availability_receipt_clock_order"
    assert not report["selected_candidates"]


def test_naive_decision_clock_is_rejected():
    with pytest.raises(ValueError, match="invalid_timestamp:as_of"):
        scan_quotes([], as_of=datetime(2030, 1, 1), policy=policy())


def test_decision_exactly_at_kickoff_is_not_pre_match():
    report = scan_quotes([snapshot(), snapshot("offer")], as_of=datetime(2030, 1, 1, 11, tzinfo=UTC), policy=policy())
    assert not report["selected_candidates"]
    assert {row["reason"] for row in report["evaluations"]} == {"decision_not_strictly_pre_kickoff"}


def test_staleness_uses_decision_clock_and_does_not_search_older_prices():
    rows = [
        snapshot(),
        snapshot("offer"),
        snapshot(
            "offer",
            snapshot_id="recent-receipt-old-quote",
            observed_at="2030-01-01T08:00:00Z",
            received_at="2030-01-01T08:59:50Z",
        ),
    ]
    report = scan_quotes(rows, as_of=AS_OF, policy=policy())
    assert not report["selected_candidates"]
    assert any(row["reason"] == "latest_snapshot_stale" for row in report["evaluations"])


def test_timestamp_skew_excludes_reference_even_when_both_quotes_are_fresh():
    reference = snapshot(
        observed_at="2030-01-01T08:58:00Z", available_at="2030-01-01T08:58:01Z", received_at="2030-01-01T08:58:02Z"
    )
    report = scan_quotes([reference, snapshot("offer")], as_of=AS_OF, policy=policy())
    assert not report["selected_candidates"]
    assert evaluation(report)["reference_exclusions"] == [{"bookmaker": "reference", "reason": "reference_clock_skew"}]


def test_each_reference_contributes_once_regardless_of_capture_count():
    rows = [snapshot(), snapshot("reference2", odds={"over": 1.5, "under": 2.5}), snapshot("offer")]
    rows.extend(
        snapshot(
            snapshot_id=f"old-{i}",
            odds={"over": 1.2, "under": 4},
            observed_at="2030-01-01T08:58:00Z",
            available_at="2030-01-01T08:58:01Z",
            received_at=f"2030-01-01T08:58:{i + 2:02d}Z",
        )
        for i in range(5)
    )
    report = scan_quotes(rows, as_of=AS_OF, policy=policy(reference_books=("reference", "reference2")))
    expected = (0.5 + (1 / 1.5) / (1 / 1.5 + 1 / 2.5)) / 2
    assert evaluation(report)["reference_probability"] == pytest.approx(expected)
    assert len(evaluation(report)["reference_provenance"]) == 2


def test_ambiguous_sources_for_same_book_are_rejected():
    rows = [
        snapshot(),
        snapshot("offer"),
        snapshot(
            source="another-source",
            snapshot_id="other-source",
            received_at="2030-01-01T08:59:10Z",
        ),
    ]
    report = scan_quotes(rows, as_of=AS_OF, policy=policy())
    assert not report["selected_candidates"]
    assert any(row["reason"] == "ambiguous_bookmaker_source" for row in report["evaluations"])


@pytest.mark.parametrize(
    "changes",
    [
        {"kickoff_at": "2030-01-01T12:00:00Z"},
        {"source_event_id": "different-event-in-provider"},
    ],
)
def test_event_identity_or_kickoff_conflict_blocks_cross_book_comparison(changes):
    report = scan_quotes([snapshot(), snapshot("offer", **changes)], as_of=AS_OF, policy=policy())
    assert not report["selected_candidates"]
    assert all(row["reason"].startswith("event_") for row in report["evaluations"])


def test_conflicting_snapshots_at_same_receipt_time_are_not_resolved_by_input_order():
    rows = [snapshot(), snapshot("offer"), snapshot("offer", snapshot_id="conflicting", odds={"over": 5, "under": 1.3})]
    for ordered in (rows, list(reversed(rows))):
        report = scan_quotes(ordered, as_of=AS_OF, policy=policy())
        assert not report["selected_candidates"]
        assert report["validation_errors"]
        assert any(row["reason"] == "conflicting_latest_snapshots" for row in report["evaluations"])


def test_exact_duplicate_snapshot_does_not_change_weight_or_candidates():
    rows = [snapshot(), snapshot("offer")]
    expected = scan_quotes(rows, as_of=AS_OF, policy=policy())
    actual = scan_quotes(rows + [snapshot()], as_of=AS_OF, policy=policy())
    assert expected["selected_candidates"] == actual["selected_candidates"]


@pytest.mark.parametrize(
    "market,line,reference_odds,offer_odds",
    [
        ("1x2", None, {"home": 3, "draw": 3, "away": 3}, {"home": 4, "draw": 3, "away": 3}),
        ("btts", None, {"yes": 1.9, "no": 1.9}, {"yes": 2.4, "no": 1.7}),
    ],
)
def test_supported_markets_preserve_canonical_outcomes(market, line, reference_odds, offer_odds):
    # 1X2 needs a positive reference margin, independently of offered prices.
    if market == "1x2":
        reference_odds = {side: 2.9 for side in reference_odds}
    rows = [
        snapshot(market=market, line=line, odds=reference_odds),
        snapshot("offer", market=market, line=line, odds=offer_odds),
    ]
    report = scan_quotes(rows, as_of=AS_OF, policy=policy())
    assert len(report["selected_candidates"]) == 1
    assert report["selected_candidates"][0]["market"] == market
    assert report["selected_candidates"][0]["line"] == line


def test_insufficient_reference_count_and_nonpositive_reference_margin_fail_closed():
    report = scan_quotes([snapshot(odds={"over": 2, "under": 2}), snapshot("offer")], as_of=AS_OF, policy=policy())
    assert not report["selected_candidates"]
    assert evaluation(report)["reference_exclusions"][0]["reason"] == "reference_has_no_positive_overround"
    report = scan_quotes(
        [snapshot(), snapshot("offer")],
        as_of=AS_OF,
        policy=policy(reference_books=("reference", "missing"), min_reference_books=2),
    )
    assert not report["selected_candidates"]


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"cost_per_unit": 0.3}, "non_positive_net_ev"),
        ({"min_ev": 0.15}, "below_minimum_net_ev"),
        ({"max_ev": 0.14}, "above_maximum_net_ev"),
    ],
)
def test_filters_use_net_ev_after_explicit_costs(changes, reason):
    report = scan_quotes([snapshot(), snapshot("offer")], as_of=AS_OF, policy=policy(**changes))
    assert not report["selected_candidates"]
    assert evaluation(report)["reason"] == reason


def test_one_candidate_per_event_and_deterministic_tie_break_independent_of_input_order():
    rows = [
        snapshot(),
        snapshot("offer-b"),
        snapshot("offer-a"),
        snapshot(event_id="event2"),
        snapshot("offer-a", event_id="event2"),
    ]
    before = scan_quotes(rows, as_of=AS_OF, policy=policy())
    after = scan_quotes(list(reversed(rows)), as_of=AS_OF, policy=policy())
    assert before["selected_candidates"] == after["selected_candidates"]
    assert len(before["selected_candidates"]) == 2
    assert {row["bookmaker"] for row in before["selected_candidates"]} == {"offer-a"}
    assert evaluation(before, "offer-b")["reason"] == "one_candidate_per_event"


@pytest.mark.parametrize(
    "changes",
    [
        {"reference_books": ()},
        {"reference_books": ("a", "a")},
        {"reference_books": ["a"]},
        {"min_reference_books": 0},
        {"min_reference_books": True},
        {"max_age_seconds": 0},
        {"max_skew_seconds": -1},
        {"cost_per_unit": -0.1},
        {"commission_on_profit": 1},
        {"min_ev": float("nan")},
        {"min_ev": 0.2, "max_ev": 0.1},
    ],
)
def test_invalid_policy_is_rejected_before_comparison(changes):
    with pytest.raises(ValueError):
        replace(policy(), **changes)


def test_no_implicit_legacy_snapshot_adapter_or_provenance_fabrication():
    legacy = {
        "event_id": "event",
        "bookmaker": "offer",
        "market": "ou2.5",
        "odd": 2.4,
        "odds_captured_at": "2030-01-01T08:59:00Z",
        "selection": "over",
    }
    report = scan_quotes([snapshot(), snapshot("offer"), legacy], as_of=AS_OF, policy=policy())
    assert report["batch_blocked"] and report["validation_errors"]
    assert not report["selected_candidates"]
