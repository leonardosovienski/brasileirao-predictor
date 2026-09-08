"""Synthetic desired-behavior regressions; never fit or evaluate real observations."""

import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from brasileirao_predictor.research.price_strength.__main__ import main
from brasileirao_predictor.research.price_strength.demo import demo_inputs
from brasileirao_predictor.research.price_strength.dynamic_xg import (
    DynamicXGConfig,
    Fixture,
    LambdaCalibration,
    XGObservation,
    forecast,
)
from brasileirao_predictor.research.price_strength.quotes import scan_quotes
from brasileirao_predictor.research.price_strength.study import price_policy, run_study, timestamp


@pytest.mark.parametrize("reverse", [False, True])
def test_provider_event_cannot_split_into_two_canonical_event_ids(reverse):
    demo = demo_inputs()
    original = demo["quotes.jsonl"][:6]
    alias = deepcopy(original)
    for row in alias:
        row["event_id"] = "second-canonical-id-for-same-provider-event"
        row["snapshot_id"] += "-alias"
    rows = original + alias
    result = scan_quotes(
        rows[::-1] if reverse else rows,
        as_of=timestamp(demo["fixtures.jsonl"][0]["decision_at"]),
        policy=price_policy(demo["protocol.json"]["price_policy"]),
    )
    assert not result["selected_candidates"], "Same (source, source_event_id) produced multiple picks: " + str(
        [(r["event_id"], r["provenance"]["source_event_id"]) for r in result["selected_candidates"]]
    )
    assert {row["reason"] for row in result["snapshot_reviews"]} == {"source_event_canonical_identity_conflict"}


def test_cli_invalid_timestamp_does_not_echo_arbitrary_input(tmp_path, capsys):
    demo = demo_inputs()
    policy = tmp_path / "policy.json"
    quotes = tmp_path / "quotes.jsonl"
    policy.write_text(json.dumps(demo["protocol.json"]["price_policy"]), encoding="utf-8")
    quotes.write_text("", encoding="utf-8")
    marker = "SYNTHETIC_INPUT_CANARY_NOT_A_CREDENTIAL"
    result = main(
        [
            "scan",
            "--quotes",
            str(quotes),
            "--policy",
            str(policy),
            "--as-of",
            marker,
            "--output-dir",
            str(tmp_path / "run"),
        ]
    )
    assert result == 2
    assert marker not in capsys.readouterr().err


@pytest.mark.parametrize("invalid", ["false", "true", 0, 1, None])
def test_invalid_calibration_eligibility_is_not_truthy_permission(invalid):
    config = DynamicXGConfig(min_team_matches=1, min_calibration_matches=1)
    calibration = LambdaCalibration(
        config_fingerprint=config.fingerprint,
        training_end=datetime(2030, 1, 1, tzinfo=UTC),
        calibration_end=datetime(2030, 2, 1, tzinfo=UTC),
        eligible=False,
        reason="INSUFFICIENT_CALIBRATION",
        n_matches=1,
        home_scale=1,
        away_scale=1,
        latest_available_at=None,
        used_match_ids=(),
    )
    observation = XGObservation(
        match_id="synthetic-past",
        home_team="A",
        away_team="B",
        kickoff=datetime(2030, 2, 5, tzinfo=UTC),
        completed_at=datetime(2030, 2, 5, 2, tzinfo=UTC),
        available_at=datetime(2030, 2, 5, 3, tzinfo=UTC),
        home_xg=1.5,
        away_xg=1.0,
    )
    target = Fixture("synthetic-target", "A", "B", datetime(2030, 2, 15, 2, tzinfo=UTC))
    with pytest.raises(ValueError, match="eligible|eligibility|boolean|bool"):
        malformed = replace(calibration, eligible=invalid)
        forecast([observation], target, datetime(2030, 2, 15, 1, tzinfo=UTC), config, malformed)


def test_study_ignores_identity_changes_received_only_after_decision():
    demo = demo_inputs()
    arguments = {name.split(".")[0]: value for name, value in demo.items()}
    expected = run_study(**arguments)
    future = deepcopy(arguments["quotes"][0])
    future.update(
        snapshot_id="synthetic-future-reschedule",
        received_at=arguments["protocol"]["report_as_of"],
        available_at=arguments["protocol"]["report_as_of"],
        observed_at=arguments["protocol"]["report_as_of"],
        kickoff_at="2030-12-01T18:00:00+00:00",
    )
    arguments["quotes"].append(future)
    actual = run_study(**arguments)
    assert actual["forecasts.jsonl"] == expected["forecasts.jsonl"]
    assert actual["summary.json"] == expected["summary.json"]


def test_study_rejects_provider_event_aliases_across_per_fixture_scans():
    arguments = {name.split(".")[0]: value for name, value in demo_inputs().items()}
    first_id = arguments["fixtures"][0]["match_id"]
    second_id = arguments["fixtures"][1]["match_id"]
    for row in arguments["quotes"]:
        if row["event_id"] == second_id:
            row["source_event_id"] = first_id
    with pytest.raises(ValueError, match="source event maps to multiple"):
        run_study(**arguments)


def test_future_alias_does_not_change_global_study_identity_mapping():
    arguments = {name.split(".")[0]: value for name, value in demo_inputs().items()}
    expected = run_study(**arguments)
    alias = deepcopy(arguments["quotes"][0])
    second = arguments["fixtures"][1]
    alias.update(
        snapshot_id="future-alias-only",
        event_id=second["match_id"],
        kickoff_at=second["kickoff"],
        received_at=arguments["protocol"]["report_as_of"],
    )
    arguments["quotes"].append(alias)
    actual = run_study(**arguments)
    assert actual["summary.json"] == expected["summary.json"]
    assert [scan["selected_candidates"] for scan in actual["price_scans.jsonl"]] == [
        scan["selected_candidates"] for scan in expected["price_scans.jsonl"]
    ]


@pytest.mark.parametrize("receipt", [None, "unreadable-synthetic-timestamp", "2030-05-20T17:00:00"])
def test_unknown_quote_receipt_never_bypasses_validation_as_future(receipt):
    arguments = {name.split(".")[0]: value for name, value in demo_inputs().items()}
    unknown = deepcopy(arguments["quotes"][0])
    unknown.update(snapshot_id="unknown-receipt", received_at=receipt, kickoff_at="2030-12-01T18:00:00+00:00")
    arguments["quotes"].append(unknown)
    result = run_study(**arguments)
    scan = result["price_scans.jsonl"][0]
    assert scan["batch_blocked"]
    assert not scan["selected_candidates"]
    assert any(error["reason"] == "invalid_timestamp:received_at" for error in scan["validation_errors"])


def test_provider_ids_are_namespaced_by_source():
    demo = demo_inputs()
    original = demo["quotes.jsonl"][:6]
    other = deepcopy(original)
    for row in other:
        row.update(event_id="independent-event", source="different-synthetic-provider")
        row["snapshot_id"] += "-other-source"
    result = scan_quotes(
        original + other,
        as_of=timestamp(demo["fixtures.jsonl"][0]["decision_at"]),
        policy=price_policy(demo["protocol.json"]["price_policy"]),
    )
    assert len(result["selected_candidates"]) == 2


def test_future_provider_alias_cannot_reject_current_scanner_candidates():
    demo = demo_inputs()
    original = demo["quotes.jsonl"][:6]
    future = deepcopy(original)
    for row in future:
        row.update(event_id="future-canonical-alias", received_at=demo["protocol.json"]["report_as_of"])
        row["snapshot_id"] += "-future"
    arguments = {
        "as_of": timestamp(demo["fixtures.jsonl"][0]["decision_at"]),
        "policy": price_policy(demo["protocol.json"]["price_policy"]),
    }
    expected = scan_quotes(original, **arguments)
    actual = scan_quotes(original + future, **arguments)
    assert actual["selected_candidates"] == expected["selected_candidates"]
