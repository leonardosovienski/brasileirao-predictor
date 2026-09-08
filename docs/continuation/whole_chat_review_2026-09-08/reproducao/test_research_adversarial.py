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


def test_provider_event_cannot_split_into_two_canonical_event_ids():
    demo = demo_inputs()
    original = demo["quotes.jsonl"][:6]
    alias = deepcopy(original)
    for row in alias:
        row["event_id"] = "second-canonical-id-for-same-provider-event"
        row["snapshot_id"] += "-alias"
    result = scan_quotes(
        original + alias,
        as_of=timestamp(demo["fixtures.jsonl"][0]["decision_at"]),
        policy=price_policy(demo["protocol.json"]["price_policy"]),
    )
    assert not result["selected_candidates"], (
        "Same (source, source_event_id) produced multiple picks: "
        + str([(r["event_id"], r["provenance"]["source_event_id"]) for r in result["selected_candidates"]])
    )


def test_cli_invalid_timestamp_does_not_echo_arbitrary_input(tmp_path, capsys):
    demo = demo_inputs()
    policy = tmp_path / "policy.json"
    quotes = tmp_path / "quotes.jsonl"
    policy.write_text(json.dumps(demo["protocol.json"]["price_policy"]), encoding="utf-8")
    quotes.write_text("", encoding="utf-8")
    marker = "SYNTHETIC_INPUT_CANARY_NOT_A_CREDENTIAL"
    result = main([
        "scan", "--quotes", str(quotes), "--policy", str(policy),
        "--as-of", marker, "--output-dir", str(tmp_path / "run"),
    ])
    assert result == 2
    assert marker not in capsys.readouterr().err


def test_invalid_calibration_eligibility_is_not_truthy_permission():
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
        match_id="synthetic-past", home_team="A", away_team="B",
        kickoff=datetime(2030, 2, 5, tzinfo=UTC),
        completed_at=datetime(2030, 2, 5, 2, tzinfo=UTC),
        available_at=datetime(2030, 2, 5, 3, tzinfo=UTC),
        home_xg=1.5, away_xg=1.0,
    )
    target = Fixture("synthetic-target", "A", "B", datetime(2030, 2, 15, 2, tzinfo=UTC))
    with pytest.raises(ValueError, match="eligible|eligibility|boolean|bool"):
        malformed = replace(calibration, eligible="false")
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
