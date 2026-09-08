"""Independent synthetic replay review; never loads historical raw files."""
from __future__ import annotations

import copy
import importlib.util
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("independent_extension_evaluate", Path(__file__).with_name("evaluate.py"))
ev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ev)
BOUNDARY = "2026-04-19T21:20:00Z"


def fixture(fixture_id="synthetic_1", kickoff="2026-05-01T20:00:00Z"):
    return {"fixture_id": fixture_id, "kickoff_at": kickoff}


def history(row, target=(0.2, 0.4, 0.4), *, missing_target=False):
    kickoff = datetime.fromisoformat(row["kickoff_at"].replace("Z", "+00:00"))
    vectors = [(360, (0.6, 0.2, 0.2)), (60, (0.4, 0.3, 0.3)), (10, target)]
    outcomes = {}
    for i, outcome_id in enumerate(("101", "102", "103")):
        states = [{"createdAt": (kickoff - timedelta(minutes=lead)).isoformat(),
                   "price": 1 / (1.05 * q[i]),
                   "active": not (missing_target and lead == 10 and i == 0)}
                  for lead, q in vectors]
        outcomes[outcome_id] = {"players": {"0": states}}
    return {"fixtureId": row["fixture_id"], "bookmakers": {"pinnacle": {
        "markets": {"101": {"outcomes": outcomes}}}}}


def run(selection, histories):
    return ev.evaluate(selection, histories, previous_ids=set(), training_latest_target_at=BOUNDARY,
                       expected_n=len(selection))


def test_target_mutation_changes_loss_but_never_prediction_or_selected_side():
    row = fixture()
    first = run([row], {row["fixture_id"]: history(row, (0.2, 0.4, 0.4))})["records"][0]
    second = run([row], {row["fixture_id"]: history(row, (0.8, 0.1, 0.1))})["records"][0]
    assert first["forecasts"] == second["forecasts"]
    assert first["secondary_price_proxy"]["side"] == second["secondary_price_proxy"]["side"] == "home"
    assert first["losses"] != second["losses"]
    assert first["secondary_price_proxy"]["observed_reference_proxy"] < 0
    assert second["secondary_price_proxy"]["observed_reference_proxy"] > 0


def test_signal_with_inactive_target_stays_in_full_signal_denominator():
    rows = [fixture("first"), fixture("second", "2026-05-02T20:00:00Z"), fixture("third", "2026-05-03T20:00:00Z")]
    result = run(rows, {"first": history(rows[0]), "second": history(rows[1], missing_target=True)})
    summary = result["secondary_price_proxy"]
    assert result["selected_n"] == 3 and result["primary_metrics"]["n"] == 1
    assert summary["feature_eligible_n"] == 2
    assert summary["signal_n"] == 2
    assert summary["signal_target_available_n"] == 1
    assert summary["signal_target_missing_n"] == 1
    assert result["records"][1]["secondary_price_proxy"]["side"] == "home"
    assert result["records"][2]["feature_exclusion_reasons"] == ["T6H:HISTORY_NOT_AVAILABLE", "T1H:HISTORY_NOT_AVAILABLE"]


def test_arithmetic_and_scenario_are_independently_recomputed():
    row = fixture()
    result = run([row], {row["fixture_id"]: history(row)})
    actual = result["records"][0]
    beta = -0.31988646513691255
    q6, q1, target = (0.6, 0.2, 0.2), (0.4, 0.3, 0.3), (0.2, 0.4, 0.4)
    candidate = [now + beta * (now - past) for past, now in zip(q6, q1)]
    expected_loss = sum((prediction - observed) ** 2 for prediction, observed in zip(candidate, target)) / 3
    expected_baseline = sum((prediction - observed) ** 2 for prediction, observed in zip(q1, target)) / 3
    assert actual["losses"]["frozen_ridge_momentum"] == pytest.approx(expected_loss)
    assert actual["losses"]["persistence"] == pytest.approx(expected_baseline)
    assert result["primary_metrics"]["paired_mean_mse_delta"] == pytest.approx(expected_loss - expected_baseline)
    assert actual["secondary_price_proxy"]["observed_reference_proxy"] == pytest.approx(0.2 / (1.05 * 0.4) - 1)
    assert actual["secondary_price_proxy"]["after_cost_scenario_proxy"] == pytest.approx(0.2 / (1.05 * 0.4) - 1 - 0.02)


def test_monthly_and_leave_one_use_identical_paired_event_losses():
    rows = [fixture("one", "2026-04-20T20:00:00Z"), fixture("two"), fixture("three", "2026-05-02T20:00:00Z")]
    targets = [(0.2, 0.4, 0.4), (0.8, 0.1, 0.1), (0.4, 0.3, 0.3)]
    result = run(rows, {row["fixture_id"]: history(row, target) for row, target in zip(rows, targets)})
    deltas = {row["fixture_id"]: row["losses"]["frozen_ridge_momentum"] - row["losses"]["persistence"]
              for row in result["records"]}
    assert result["monthly"]["2026-04"]["metrics"]["n"] == 1
    assert result["monthly"]["2026-05"]["metrics"]["n"] == 2
    assert result["monthly"]["2026-05"]["metrics"]["paired_mean_mse_delta"] == pytest.approx((deltas["two"] + deltas["three"]) / 2)
    for row in result["leave_one_event_out"]["observations"]:
        expected = sum(value for key, value in deltas.items() if key != row["removed_fixture_id"]) / 2
        assert row["paired_mean_mse_delta"] == pytest.approx(expected)
    assert result["leave_one_event_out"]["refitting"] is False
    assert result["status"] == "INSUFFICIENT_DATA"


def test_boundary_uses_decision_not_match_kickoff():
    row = fixture(kickoff="2026-04-19T21:30:00Z")
    with pytest.raises(ValueError, match="strictly after"):
        run([row], {})


def test_real_frozen_plan_schema_passes_without_loading_raw():
    plan = json.loads(Path(__file__).with_name("plan.json").read_text())
    ev.validate_plan(plan)
    changed = copy.deepcopy(plan)
    changed["secondary_price_proxy"]["threshold"] = 0.01
    with pytest.raises(ValueError, match="threshold"):
        ev.validate_plan(changed)


def test_same_time_suspension_excludes_all_features_even_with_old_active_price():
    row = fixture()
    payload = history(row)
    leg = payload["bookmakers"]["pinnacle"]["markets"]["101"]["outcomes"]["101"]["players"]["0"]
    leg.append({**leg[1], "active": False})
    result = run([row], {row["fixture_id"]: payload})
    assert result["coverage"]["feature_eligible_n"] == 0
    assert result["secondary_price_proxy"]["signal_n"] == 0
    assert any("CONFLICTING_STATE" in reason for reason in result["records"][0]["feature_exclusion_reasons"])
