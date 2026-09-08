"""Independent synthetic fixtures; never open provider raw histories."""
from __future__ import annotations

import copy
import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location("extension_evaluator", Path(__file__).with_name("evaluate.py"))
ev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ev)
BOUNDARY = "2026-04-19T21:20:00+00:00"


def input_data(n=51):
    selection, histories = [], {}
    first = datetime(2026, 4, 20, 20, tzinfo=UTC)
    q6 = np.array([0.6, 0.25, 0.15])
    q1 = np.array([0.4, 0.35, 0.25])
    target = ev.replay.normalized(q1 + ev.BETA * (q1 - q6))
    for index in range(n):
        fixture_id = f"test{index}"
        kickoff = first + timedelta(days=index)
        selection.append({"fixture_id": fixture_id, "kickoff_at": kickoff.isoformat()})
        outcomes = {}
        for side, outcome_id in enumerate(ev.replay.OUTCOME_IDS):
            rows = []
            for window, q in (("T6H", q6), ("T1H", q1), ("T10M", target)):
                rows.append({"createdAt": (kickoff - ev.replay.WINDOWS[window]).isoformat(),
                             "price": float(1 / (q[side] * 1.02)), "active": True})
            outcomes[outcome_id] = {"players": {"0": rows}}
        histories[fixture_id] = {"fixtureId": fixture_id, "bookmakers": {
            "pinnacle": {"markets": {"101": {"outcomes": outcomes}}}}}
    return selection, histories


def run(selection, histories):
    return ev.evaluate(selection, histories, previous_ids=set(), training_latest_target_at=BOUNDARY)


def leg(history, oid="101"):
    return history["bookmakers"]["pinnacle"]["markets"]["101"]["outcomes"][oid]["players"]["0"]


def plan():
    return {**copy.deepcopy(ev.EXPECTED), "secondary_price_proxy": {"threshold": 0.02, "cost_scenario": 0.02}}


def test_frozen_candidate_matches_independent_arithmetic_and_no_training():
    selection, histories = input_data()
    result = run(selection, histories)
    assert result["new_training_events"] == 0
    assert result["fixed_beta"] == -0.31988646513691255
    assert result["primary_metrics"]["n"] == 51
    assert result["primary_metrics"]["frozen_ridge_momentum_mean_mse"] < 1e-30
    expected_baseline = np.mean((np.array([0.4, 0.35, 0.25]) -
        np.array([0.46397729302738254, 0.31801135348630874, 0.21801135348630874])) ** 2)
    assert result["primary_metrics"]["persistence_mean_mse"] == pytest.approx(expected_baseline)
    assert result["primary_metrics"]["events_lower_mse"] == 51
    assert result["status"] == "OBSERVED_LOWER_PRICE_PREDICTION_ERROR"
    assert result["confirmation"] is False and result["economic_evidence"] is False


def test_predict_does_not_read_target_or_football_outcomes():
    class Forbidden(dict):
        def __getitem__(self, key):
            raise AssertionError("Target accessed by prediction")
    features = {"T6H": {"q": [0.6, 0.25, 0.15]}, "T1H": {"q": [0.4, 0.35, 0.25]}, "T10M": Forbidden()}
    forecast = ev.predict(features)
    assert forecast["frozen_ridge_momentum"][0] == pytest.approx(0.46397729302738254)


def test_target_changes_loss_but_cannot_change_forecast_or_signal_selection():
    selection, histories = input_data()
    first = run(selection, histories)
    for oid, probability in zip(ev.replay.OUTCOME_IDS, [0.2, 0.5, 0.3], strict=True):
        leg(histories["test0"], oid)[2]["price"] = 1 / (1.02 * probability)
    changed = run(selection, histories)
    a, b = first["records"][0], changed["records"][0]
    assert a["forecasts"] == b["forecasts"]
    assert a["secondary_price_proxy"]["side"] == b["secondary_price_proxy"]["side"] == "home"
    assert a["losses"] != b["losses"]


def test_missing_target_signal_remains_in_denominator_and_no_old_quote_resurrection():
    selection, histories = input_data()
    leg(histories["test0"])[2]["active"] = False
    result = run(selection, histories)
    assert result["selected_n"] == 51
    assert result["primary_metrics"]["n"] == 50
    assert result["secondary_price_proxy"]["signal_n"] == 51
    assert result["secondary_price_proxy"]["signal_target_available_n"] == 50
    assert result["secondary_price_proxy"]["signal_target_missing_n"] == 1
    assert result["records"][0]["secondary_price_proxy"]["status"] == "SIGNAL_TARGET_MISSING"
    assert "INACTIVE_STATE" in result["records"][0]["target_exclusion_reasons"][0]


def test_latest_feature_suspension_rejects_even_with_reactivated_target():
    selection, histories = input_data()
    leg(histories["test0"])[1]["active"] = False
    result = run(selection, histories)
    assert result["records"][0]["features_eligible"] is False
    assert result["records"][0]["target_eligible"] is True
    assert result["secondary_price_proxy"]["signal_n"] == 50


def test_future_state_has_no_effect_on_any_cutoff():
    selection, histories = input_data()
    first = run(selection, histories)
    leg(histories["test0"]).append({"createdAt": selection[0]["kickoff_at"], "active": False, "price": 200})
    assert first == run(selection, histories)


def test_identity_mismatch_is_excluded_and_never_replaced():
    selection, histories = input_data()
    histories["test0"]["fixtureId"] = "different"
    del histories["test1"]
    result = run(selection, histories)
    assert result["selected_n"] == 51 and result["primary_metrics"]["n"] == 49
    assert result["records"][0]["feature_exclusion_reasons"] == ["T6H:HISTORY_FIXTURE_ID_MISMATCH", "T1H:HISTORY_FIXTURE_ID_MISMATCH"]
    assert result["records"][1]["feature_exclusion_reasons"] == ["T6H:HISTORY_NOT_AVAILABLE", "T1H:HISTORY_NOT_AVAILABLE"]


def test_minimum_complete_status_does_not_hide_descriptive_metrics():
    selection, histories = input_data()
    histories = {key: value for key, value in histories.items() if int(key.removeprefix("test")) < 29}
    result = run(selection, histories)
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["primary_metrics"]["n"] == 29
    assert result["primary_metrics"]["relative_mse_reduction"] == pytest.approx(1)


def test_no_valid_data_is_explicit_null_and_months_keep_selected_events():
    selection, _ = input_data()
    result = run(selection, {})
    assert result["primary_metrics"]["n"] == 0
    assert result["primary_metrics"]["paired_mean_mse_delta"] is None
    assert result["secondary_price_proxy"]["signal_n"] == 0
    assert result["secondary_price_proxy"]["observed_reference_proxy_mean"] is None
    assert sum(row["secondary_price_proxy"]["selected_n"] for row in result["monthly"].values()) == 51
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("mutation", ["duplicate", "previous", "boundary", "naive", "later_season", "extra_history", "unsorted"])
def test_selection_temporal_identity_and_scope_guards(mutation):
    selection, histories = input_data()
    previous = set()
    if mutation == "duplicate":
        selection[1]["fixture_id"] = "test0"
    elif mutation == "previous":
        previous = {"test0"}
    elif mutation == "boundary":
        selection[0]["kickoff_at"] = "2026-04-19T22:20:00+00:00"
    elif mutation == "naive":
        selection[0]["kickoff_at"] = "2026-04-20T20:00:00"
    elif mutation == "later_season":
        selection[-1]["kickoff_at"] = "2026-07-01T00:00:00+00:00"
    elif mutation == "extra_history":
        histories["unselected"] = {}
    else:
        selection[0], selection[1] = selection[1], selection[0]
    with pytest.raises(ValueError):
        ev.evaluate(selection, histories, previous_ids=previous, training_latest_target_at=BOUNDARY)


def test_same_timestamp_price_conflict_and_stale_state_are_excluded():
    selection, histories = input_data()
    duplicate = copy.deepcopy(leg(histories["test0"])[1])
    duplicate["price"] += 0.1
    leg(histories["test0"]).append(duplicate)
    leg(histories["test1"])[0]["createdAt"] = (
        ev.replay.dt(selection[1]["kickoff_at"]) - timedelta(hours=12, seconds=1)).isoformat()
    result = run(selection, histories)
    assert result["primary_metrics"]["n"] == 49
    assert any("CONFLICTING_STATE" in reason for reason in result["records"][0]["feature_exclusion_reasons"])
    assert any("STALE_SELECTION" in reason for reason in result["records"][1]["feature_exclusion_reasons"])


def test_secondary_proxy_is_independent_arithmetic_not_settlement():
    selection, histories = input_data()
    result = run(selection, histories)
    proxy = result["records"][0]["secondary_price_proxy"]
    expected = 0.46397729302738254 / (1.02 * 0.4) - 1
    assert proxy["observed_reference_proxy"] == pytest.approx(expected)
    assert proxy["after_cost_scenario_proxy"] == pytest.approx(expected - 0.02)
    assert "roi" not in proxy and "profit" not in proxy


def test_monthly_and_leave_one_out_are_event_paired_without_refitting():
    selection, histories = input_data()
    result = run(selection, histories)
    assert sum(row["metrics"]["n"] for row in result["monthly"].values()) == 51
    assert len(result["leave_one_event_out"]["observations"]) == 51
    assert result["leave_one_event_out"]["refitting"] is False
    assert all(row["paired_mean_mse_delta"] == pytest.approx(result["primary_metrics"]["paired_mean_mse_delta"])
               for row in result["leave_one_event_out"]["observations"])


def test_zero_movement_has_no_signal_and_undefined_relative_reduction():
    selection, histories = input_data()
    for history in histories.values():
        for oid in ev.replay.OUTCOME_IDS:
            rows = leg(history, oid)
            for row in rows:
                row["price"] = 3 / 1.02
    result = run(selection, histories)
    assert result["primary_metrics"]["persistence_mean_mse"] == 0
    assert result["primary_metrics"]["relative_mse_reduction"] is None
    assert result["secondary_price_proxy"]["no_signal_n"] == 51
    assert result["status"] == "OBSERVED_NOT_LOWER_PRICE_PREDICTION_ERROR"


@pytest.mark.parametrize("changed", ["beta", "minimum_complete_test_events", "threshold", "cost_scenario", "models"])
def test_plan_parameters_cannot_be_changed(changed):
    frozen = plan()
    if changed in ("threshold", "cost_scenario"):
        frozen["secondary_price_proxy"][changed] += 0.01
    elif changed == "models":
        frozen[changed].append("another_model")
    else:
        frozen[changed] += 1
    with pytest.raises(ValueError):
        ev.validate_plan(frozen)


def synthetic_manifest(selection, *, codes=None):
    codes = codes or [429] * len(selection)
    return {"finished_at": "2026-09-07T22:00:00+00:00", "plan_file_sha256_before_first_request": ev.sha(b"plan"),
            "status": "COMPLETE_NO_RETRIES", "attempted_count": len(codes), "unattempted_count": len(selection) - len(codes),
            "records": [{"fixture_id": row["fixture_id"], "http_status": code}
                        for row, code in zip(selection, codes)]}


def test_acquisition_all_failed_keeps_no_histories(tmp_path):
    selection, _ = input_data()
    assert ev.load_histories(selection, tmp_path, synthetic_manifest(selection), b"plan") == ({}, {})


def test_valid_early_stop_prefix_retains_unattempted_missing(tmp_path):
    selection, _ = input_data()
    manifest = synthetic_manifest(selection, codes=[429, 429, 429])
    manifest["status"] = "STOP_PROVIDER_ERROR_NO_RETRY"
    histories, _ = ev.load_histories(selection, tmp_path, manifest, b"plan")
    result = run(selection, histories)
    assert result["selected_n"] == 51 and result["primary_metrics"]["n"] == 0


@pytest.mark.parametrize("failure", ["running", "partial_complete", "invalid_stop", "wrong_order", "wrong_plan", "unattempted_raw", "failed_raw", "unknown_raw", "wrong_count"])
def test_acquisition_integrity_and_stopping_guards(tmp_path, failure):
    selection, _ = input_data()
    manifest = synthetic_manifest(selection)
    if failure == "running":
        manifest["status"] = "RUNNING"
    elif failure == "partial_complete":
        manifest = synthetic_manifest(selection, codes=[429])
    elif failure == "invalid_stop":
        manifest = synthetic_manifest(selection, codes=[429])
        manifest["status"] = "STOP_PROVIDER_ERROR_NO_RETRY"
    elif failure == "wrong_order":
        manifest["records"][0], manifest["records"][1] = manifest["records"][1], manifest["records"][0]
    elif failure == "wrong_plan":
        manifest["plan_file_sha256_before_first_request"] = "different"
    elif failure == "unattempted_raw":
        manifest = synthetic_manifest(selection, codes=[401])
        manifest["status"] = "STOP_PROVIDER_ERROR_NO_RETRY"
        (tmp_path / "test1.json").write_text("{}")
    elif failure == "failed_raw":
        (tmp_path / "test0.json").write_text("{}")
    elif failure == "unknown_raw":
        (tmp_path / "unselected.json").write_text("{}")
    else:
        manifest["attempted_count"] = 50
    with pytest.raises(ValueError):
        ev.load_histories(selection, tmp_path, manifest, b"plan")


def test_raw_hash_is_checked_before_loading_and_original_content_retained(tmp_path):
    selection, histories = input_data()
    manifest = synthetic_manifest(selection)
    content = json.dumps(histories["test0"]).encode()
    path = tmp_path / "test0.json"
    path.write_bytes(content)
    manifest["records"][0].update(http_status=200, sha256=ev.sha(content))
    loaded, hashes = ev.load_histories(selection, tmp_path, manifest, b"plan")
    assert loaded == {"test0": histories["test0"]}
    assert hashes == {"test0": ev.sha(content)}
    path.write_bytes(content + b" ")
    with pytest.raises(ValueError, match="hash"):
        ev.load_histories(selection, tmp_path, manifest, b"plan")


def test_compaction_discards_unneeded_payload_without_changing_reconstruction():
    selection, histories = input_data()
    before = run(selection, histories)
    enriched = histories["test0"]
    enriched["footballResults"] = "forbidden and unused"
    enriched["bookmakers"]["other_book"] = {"markets": {}}
    enriched["bookmakers"]["pinnacle"]["markets"]["999"] = {"unused": True}
    enriched["bookmakers"]["pinnacle"]["suspended"] = True
    histories["test0"] = ev.compact_history({"historyraw": enriched})
    assert set(histories["test0"]) == {"fixtureId", "bookmakers"}
    assert set(histories["test0"]["bookmakers"]) == {"pinnacle"}
    assert set(histories["test0"]["bookmakers"]["pinnacle"]["markets"]) == {"101"}
    assert before == run(selection, histories)


def synthetic_sources():
    selection, _ = input_data()
    old = [{"fixture_id": f"old{i}", "kickoff_at": (datetime(2026, 1, 1, 20, tzinfo=UTC) + timedelta(days=i)).isoformat()}
           for i in range(30)]
    universe = old + selection
    result = {"ridge_beta": ev.BETA, "training_ids": [f"old{i}" for i in range(13)]}
    as_bytes = lambda value: json.dumps(value, sort_keys=True).encode()
    selection_bytes, old_bytes, universe_bytes, result_bytes = map(as_bytes, (selection, old, universe, result))
    frozen = plan()
    frozen.update(selection_file_sha256=ev.sha(selection_bytes), source_replay_sha256=ev.sha(ev.SOURCE_REPLAY.read_bytes()),
                  excluded_previous_selection_file_sha256=ev.sha(old_bytes), source_universe_sha256=ev.sha(universe_bytes),
                  source_pinnacle_results_sha256=ev.sha(result_bytes), training_latest_target_at="2026-01-13T19:50:00+00:00")
    return frozen, selection_bytes, old_bytes, universe_bytes, result_bytes


def test_sources_derive_training_boundary_and_all_unused_events_without_price_data():
    sources = synthetic_sources()
    previous_ids, target_at = ev.validate_sources(*sources)
    assert len(previous_ids) == 30
    assert target_at == "2026-01-13T19:50:00+00:00"


@pytest.mark.parametrize("mutation", ["source_hash", "boundary", "coefficient", "omit_eligible", "change_metadata"])
def test_sources_reject_drift_and_omitted_eligible_events(mutation):
    frozen, selection_bytes, old_bytes, universe_bytes, result_bytes = synthetic_sources()
    if mutation == "source_hash":
        frozen["source_replay_sha256"] = "wrong"
    elif mutation == "boundary":
        frozen["training_latest_target_at"] = "2026-01-13T20:00:00+00:00"
    elif mutation == "coefficient":
        result = json.loads(result_bytes)
        result["ridge_beta"] += 0.01
        result_bytes = json.dumps(result).encode()
        frozen["source_pinnacle_results_sha256"] = ev.sha(result_bytes)
    elif mutation == "omit_eligible":
        selection = json.loads(selection_bytes)[1:]
        selection_bytes = json.dumps(selection).encode()
        frozen["selection_file_sha256"] = ev.sha(selection_bytes)
    else:
        selection = json.loads(selection_bytes)
        selection[0]["kickoff_at"] = "2026-04-21T20:00:00+00:00"
        selection_bytes = json.dumps(selection).encode()
        frozen["selection_file_sha256"] = ev.sha(selection_bytes)
    with pytest.raises(ValueError):
        ev.validate_sources(frozen, selection_bytes, old_bytes, universe_bytes, result_bytes)
