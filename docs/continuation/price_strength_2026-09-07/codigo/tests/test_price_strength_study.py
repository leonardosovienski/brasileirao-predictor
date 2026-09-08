"""End-to-end synthetic regressions for chronology and research receipts."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from brasileirao_predictor.research.price_strength.__main__ import main
from brasileirao_predictor.research.price_strength.demo import demo_inputs
from brasileirao_predictor.research.price_strength.study import run_study


def inputs():
    return {name.split(".")[0]: value for name, value in demo_inputs().items()}


def test_full_synthetic_study_compares_probabilities_and_keeps_execution_unproven():
    result = run_study(**inputs())
    summary = result["summary.json"]
    assert summary["fixtures"] == summary["calibrated_forecasts"] == summary["labelled_fixtures"] == 4
    assert not summary["execution_proven"] and not summary["real_capital_enabled"]
    assert not summary["profitability_established"]
    for market in ("1x2", "ou25", "btts"):
        assert summary["paired_metrics"]["calibrated_xg"]["market"][market]["n"] == 4
    assert summary["quote_candidates"] == 4
    for scan in result["price_scans.jsonl"]:
        assert len(scan["selected_candidates"]) == 1
        priced = [row for row in scan["evaluations"] if row.get("xg_diagnostics")]
        assert priced and set(priced[0]["xg_diagnostics"]) == {"raw_xg", "calibrated_xg"}


def test_history_and_fixture_order_do_not_change_predictions_or_paired_metrics():
    original = inputs()
    shuffled = deepcopy(original)
    for key in ("history", "fixtures", "quotes"):
        shuffled[key].reverse()
    first, second = run_study(**original), run_study(**shuffled)
    for name in ("forecasts.jsonl", "comparisons.jsonl", "summary.json"):
        assert first[name] == second[name]
    assert [s["selected_candidates"] for s in first["price_scans.jsonl"]] == [
        s["selected_candidates"] for s in second["price_scans.jsonl"]
    ]


def test_future_evaluation_statistics_do_not_change_first_forecast_or_calibration():
    original = inputs()
    altered = deepcopy(original)
    for row in altered["history"][-4:]:
        row.update(home_xg=10.0, away_xg=9.0, home_goals=8, away_goals=7)
    first, second = run_study(**original), run_study(**altered)
    assert first["forecasts.jsonl"][0] == second["forecasts.jsonl"][0]
    assert first["summary.json"]["calibration"] == second["summary.json"]["calibration"]


def test_missing_results_and_prices_reduce_paired_coverage_without_imputation():
    raw = inputs()
    raw["history"][-1].update(home_goals=None, away_goals=None)
    raw["quotes"] = []
    result = run_study(**raw)
    assert result["summary.json"]["labelled_fixtures"] == 3
    assert result["summary.json"]["calibrated_forecasts"] == 4
    assert result["summary.json"]["paired_metrics"]["calibrated_xg"]["market"]["1x2"]["n"] == 0


def test_frozen_external_baseline_is_compared_on_the_same_fixtures():
    raw = inputs()
    preliminary = run_study(**raw)
    raw["baseline"] = [
        {
            "match_id": row["match_id"],
            "decision_at": row["decision_at"],
            "generated_at": row["decision_at"],
            "candidate_id": "synthetic-frozen-control",
            "probabilities": row["raw"]["probabilities"],
        }
        for row in preliminary["forecasts.jsonl"]
    ]
    result = run_study(**raw)
    metrics = result["summary.json"]["paired_metrics"]["raw_xg"]["frozen_baseline"]
    assert metrics["1x2"]["n"] == 4
    assert metrics["1x2"]["mean_delta_brier"] == 0
    raw["baseline"][0]["generated_at"] = raw["protocol"]["report_as_of"]
    with pytest.raises(ValueError, match="generated after"):
        run_study(**raw)


@pytest.mark.parametrize(
    "change,expected",
    [
        (lambda raw: raw["protocol"].update(data_kind="UNTOUCHED_HOLDOUT"), "exploratory"),
        (lambda raw: raw["protocol"].update(calibration_end=raw["protocol"]["evaluation_start"]), "ordered"),
        (lambda raw: raw["fixtures"].append(raw["fixtures"][0]), "duplicate"),
        (lambda raw: raw["quotes"][0].update(event_id="wrong-match"), "fixture universe"),
        (lambda raw: raw["quotes"][0].update(kickoff_at=raw["protocol"]["report_as_of"]), "kickoff"),
    ],
)
def test_invalid_study_contracts_fail_closed(change, expected):
    raw = inputs()
    change(raw)
    with pytest.raises(ValueError, match=expected):
        run_study(**raw)


def test_cli_demo_writes_reproducible_receipts_and_never_overwrites(tmp_path):
    output = tmp_path / "demo"
    assert main(["demo", "--output-dir", str(output)]) == 0
    manifest = json.loads((output / "run/manifest.json").read_text())
    assert manifest["status"] == "COMPLETE"
    assert manifest["metadata"]["real_capital_enabled"] is False
    for row in manifest["inputs"].values():
        assert hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() == row["sha256"]
    for name, row in manifest["artifacts"].items():
        assert hashlib.sha256((output / "run" / name).read_bytes()).hexdigest() == row["sha256"]
    original = (output / "run/manifest.json").read_bytes()
    assert main(["demo", "--output-dir", str(output)]) == 2
    assert (output / "run/manifest.json").read_bytes() == original


def test_cli_scan_requires_explicit_inputs_and_retains_invalid_snapshot_evidence(tmp_path):
    demo = demo_inputs()
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(demo["protocol.json"]["price_policy"]))
    quotes = tmp_path / "quotes.jsonl"
    rows = demo["quotes.jsonl"][:6]
    rows[3].update(status="suspended", odds={})
    quotes.write_text("".join(json.dumps(row) + "\n" for row in rows))
    result = tmp_path / "scan"
    assert (
        main(
            [
                "scan",
                "--quotes",
                str(quotes),
                "--policy",
                str(policy),
                "--as-of",
                demo["fixtures.jsonl"][0]["decision_at"],
                "--output-dir",
                str(result),
            ]
        )
        == 0
    )
    scan = json.loads((result / "scan.json").read_text())
    assert any("suspended" in row.get("reason", "") for row in scan["evaluations"])
    with pytest.raises(SystemExit):
        main(["study", "--output-dir", str(tmp_path / "empty")])


@pytest.mark.parametrize("reverse", [False, True])
def test_conflicting_evaluation_identity_is_rejected_even_with_identical_scores(reverse):
    raw = inputs()
    conflicting = {**raw["history"][-1], "home_team": "Unrelated synthetic team"}
    raw["history"].append(conflicting)
    if reverse:
        raw["history"].reverse()
    with pytest.raises(ValueError, match="identity"):
        run_study(**raw)
