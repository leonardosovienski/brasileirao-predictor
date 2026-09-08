"""Adversarial synthetic tests for the independent economic auditor."""

import json
from copy import deepcopy
from pathlib import Path

from audit_results import audit_payloads
from economics import run_replay

PLAN = json.loads(Path(__file__).with_name("plan.json").read_text(encoding="utf-8"))


def synthetic_cohort():
    events = []
    for i in range(380):
        round_number = i // 10 + 1
        events.append({
            "id": f"fixture_{i:03d}", "round": round_number,
            "role": "test" if round_number <= 19 else "paper",
            "kickoff_at": f"2026-{i // 32 + 1:02d}-{i % 28 + 1:02d}T12:00:00Z",
            "p_1x2": None, "p_over25": None, "p_btts": None, "odds": {},
            "home_goals": None, "away_goals": None,
        })
    # Two chronological settlements: one loss and one win at odds 2.
    for i in [0, 1]:
        events[i].update(p_1x2=[.55, .20, .25], odds={"1x2": [2, 4, 4]},
                         home_goals=i, away_goals=1-i)
    return events


def payloads(events=None):
    inputs = {arm: deepcopy(events if events is not None else synthetic_cohort())
              for arm in ["primary_calibrated", "diagnostic_raw"]}
    results = {"arms": {arm: run_replay(rows) for arm, rows in inputs.items()}}
    return inputs, results


def test_full_official_denominators_and_independent_brl_arithmetic():
    report = audit_payloads(*payloads(), PLAN)
    assert report["status"] == "PASS"
    raw = report["audited"]["diagnostic_raw"]
    assert raw["turn_counts"] == {"first_turn": 190, "second_turn": 190}
    assert raw["overall"]["net_profit_units"] == -.04
    assert raw["illustration_brl"]["overall"]["net_profit_brl"] == -2
    assert raw["illustration_brl"]["overall"]["final_bankroll_brl"] == 4998
    assert raw["illustration_brl"]["overall"]["max_drawdown_brl"] == 51


def test_forged_profit_and_missing_cost_are_caught():
    inputs, results = payloads()
    results["arms"]["primary_calibrated"]["overall"]["net_profit_units"] = 100
    results["arms"]["primary_calibrated"]["decisions"][0]["settlement"]["cost_units"] = 0
    report = audit_payloads(inputs, results, PLAN)
    assert report["status"] == "FAIL"
    assert any("net_profit_units" in error for error in report["errors"])
    assert any("cost_units" in error for error in report["errors"])


def test_missing_official_fixture_detected_even_with_internally_consistent_results():
    report = audit_payloads(*payloads(synthetic_cohort()[:-1]), PLAN)
    assert report["status"] == "FAIL"
    assert any("190 per turn" in error for error in report["errors"])


def test_wrong_candidate_is_caught_even_when_reported_profit_is_unchanged():
    inputs, results = payloads()
    results["arms"]["diagnostic_raw"]["decisions"][0]["candidate"]["side"] = "away"
    report = audit_payloads(inputs, results, PLAN)
    assert report["status"] == "FAIL"
    assert any("candidate.side" in error for error in report["errors"])


def test_arms_cannot_use_different_quotes_or_outcomes():
    inputs, results = payloads()
    inputs["primary_calibrated"][0]["odds"]["1x2"][0] = 2.1
    results["arms"]["primary_calibrated"] = run_replay(inputs["primary_calibrated"])
    report = audit_payloads(inputs, results, PLAN)
    assert report["status"] == "FAIL"
    assert "Arm input fixture metadata, quotes or outcomes differ" in report["errors"]


def test_wrong_drawdown_caught_independently_of_correct_final_profit():
    inputs, results = payloads()
    results["arms"]["diagnostic_raw"]["overall"]["max_drawdown_units"] = .04
    report = audit_payloads(inputs, results, PLAN)
    assert report["status"] == "FAIL"
    assert any("max_drawdown_units" in error for error in report["errors"])


def test_nonnumeric_fabricated_pending_roi_is_caught():
    inputs, results = payloads()
    results["arms"]["diagnostic_raw"]["by_role"]["paper"]["net_roi"] = 0
    report = audit_payloads(inputs, results, PLAN)
    assert report["status"] == "FAIL"
    assert any("paper.net_roi" in error for error in report["errors"])
