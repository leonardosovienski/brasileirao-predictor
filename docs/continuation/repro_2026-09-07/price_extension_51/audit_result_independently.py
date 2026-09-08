"""Read existing derived records and verify arithmetic, without replay or raw data."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

WORK = Path(__file__).resolve().parent
read = lambda name: json.loads((WORK / name).read_text(encoding="utf-8"))
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
parse = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
result = read("result.json")
plan = read("plan.json")
selection = read("selection.json")
manifest = read("acquisition_manifest.json")
receipt = read("implementation_receipt.json")
errors = []
checks = 0


def check(condition, label):
    global checks
    checks += 1
    if not condition:
        errors.append(label)


def close(actual, expected, label):
    check(isinstance(actual, (int, float)) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12), label)


def normalized(values):
    clipped = [max(0.000001, value) for value in values]
    total = math.fsum(clipped)
    return [value / total for value in clipped]


def average(values):
    return math.fsum(values) / len(values)


ids = [row["fixture_id"] for row in selection]
records = result["records"]
check([row["fixture_id"] for row in records] == ids, "record order and full selection")
check(len(ids) == len(set(ids)) == 51, "all 51 distinct selected IDs")
check([row["fixture_id"] for row in manifest["records"]] == ids, "all acquisition IDs once")
check(manifest["attempted_count"] == manifest["saved_count"] == 51, "acquisition attempt/saved counts")
check(all(row["http_status"] == 200 for row in manifest["records"]), "all HTTP 200")
check(manifest["quota_before"]["request_count"] == manifest["quota_after"]["request_count"] == 62, "quota unchanged")
for name, key in [("plan.json", "plan_sha256"), ("selection.json", "selection_sha256"),
                  ("acquisition_manifest.json", "acquisition_manifest_sha256"), ("evaluate.py", "script_sha256")]:
    check(result["provenance"][key] == digest(WORK / name), f"provenance {name}")
for name, expected in receipt["hashes"].items():
    check(expected == digest(WORK / name), f"frozen implementation {name}")
check(parse(receipt["frozen_before_first_evaluation"]) < parse(result["provenance"]["generated_at"]), "implementation before evaluation")
check(manifest["plan_file_sha256_before_first_request"] == digest(WORK / "plan.json"), "acquisition plan hash")
check(result["provenance"]["raw_sha256_by_fixture_id"] == {row["fixture_id"]: row["sha256"] for row in manifest["records"]}, "raw hashes match manifest without opening raw")

feature_n = target_n = signal_n = 0
deltas, baseline_losses, candidate_losses, complete_ids = [], [], [], []
monthly = {}
excluded = []
reasons = Counter()
for row in records:
    event_id = row["fixture_id"]
    kickoff = parse(row["kickoff_at"])
    check(parse(row["decision_at"]) == kickoff - timedelta(hours=1), f"{event_id}: decision time")
    check(parse(row["target_at"]) == kickoff - timedelta(minutes=10), f"{event_id}: target time")
    check(parse(row["decision_at"]) > parse(plan["training_latest_target_at"]), f"{event_id}: training boundary")
    for window, lead in (("T6H", 360), ("T1H", 60), ("T10M", 10)):
        snapshot = row["snapshots"][window]
        if snapshot["eligible"]:
            cutoff = kickoff - timedelta(minutes=lead)
            check(parse(snapshot["cutoff_at"]) == cutoff, f"{event_id}/{window}: cutoff")
            implied = [1 / price for price in snapshot["odds"]]
            booksum = math.fsum(implied)
            close(snapshot["booksum"], booksum, f"{event_id}/{window}: booksum")
            check(0.99 <= booksum <= 1.30, f"{event_id}/{window}: declared margin interval")
            for side in range(3):
                check(1.01 <= snapshot["odds"][side] <= 20, f"{event_id}/{window}/{side}: price interval")
                close(snapshot["q"][side], implied[side] / booksum, f"{event_id}/{window}/{side}: normalized reference")
                age = (cutoff - parse(snapshot["leg_state_at"][side])).total_seconds()
                check(0 <= age <= 21600, f"{event_id}/{window}/{side}: temporal state age")
                close(snapshot["leg_age_seconds"][side], age, f"{event_id}/{window}/{side}: reported age")
    feature_ok = row["snapshots"]["T6H"]["eligible"] and row["snapshots"]["T1H"]["eligible"]
    target_ok = row["snapshots"]["T10M"]["eligible"]
    check(row["features_eligible"] == feature_ok, f"{event_id}: feature eligibility")
    check(row["target_eligible"] == target_ok, f"{event_id}: target eligibility")
    check(row["paired_mse_eligible"] == (feature_ok and target_ok), f"{event_id}: paired eligibility")
    feature_n += feature_ok
    target_n += target_ok
    reasons.update(row["feature_exclusion_reasons"])
    if not feature_ok or not target_ok:
        excluded.append({"fixture_id": event_id, "kickoff_at": row["kickoff_at"],
                         "feature_reasons": row["feature_exclusion_reasons"], "target_reasons": row["target_exclusion_reasons"]})
    if not feature_ok:
        check(row["forecasts"] is None and row["losses"] is None, f"{event_id}: unavailable features not predicted")
        continue
    q6, q1 = row["snapshots"]["T6H"]["q"], row["snapshots"]["T1H"]["q"]
    expected = {"persistence": normalized(q1),
                "frozen_ridge_momentum": normalized([now + plan["beta"] * (now - past) for past, now in zip(q6, q1)])}
    for name in expected:
        for side in range(3):
            close(row["forecasts"][name][side], expected[name][side], f"{event_id}/{name}/{side}: frozen prediction")
    proxies = [q * price - 1 for q, price in zip(expected["frozen_ridge_momentum"], row["snapshots"]["T1H"]["odds"])]
    side = max(range(3), key=lambda index: proxies[index])
    close(row["secondary_price_proxy"]["best_predicted_reference_proxy"], proxies[side], f"{event_id}: feature-only best proxy")
    signal = proxies[side] > 0.02
    signal_n += signal
    check(row["secondary_price_proxy"]["status"].startswith("SIGNAL_") == signal, f"{event_id}: frozen signal threshold")
    if target_ok:
        target = row["snapshots"]["T10M"]["q"]
        losses = {name: average([(p - q) ** 2 for p, q in zip(vector, target)]) for name, vector in expected.items()}
        for name, expected_loss in losses.items():
            close(row["losses"][name], expected_loss, f"{event_id}/{name}: MSE")
        baseline_losses.append(losses["persistence"])
        candidate_losses.append(losses["frozen_ridge_momentum"])
        deltas.append(losses["frozen_ridge_momentum"] - losses["persistence"])
        complete_ids.append(event_id)
        monthly.setdefault(row["kickoff_at"][:7], []).append(len(deltas) - 1)

metrics = result["primary_metrics"]
check(metrics["n"] == len(deltas) == 50, "primary complete denominator")
close(metrics["persistence_mean_mse"], average(baseline_losses), "baseline mean")
close(metrics["frozen_ridge_momentum_mean_mse"], average(candidate_losses), "candidate mean")
close(metrics["paired_mean_mse_delta"], average(deltas), "paired mean delta")
close(metrics["relative_mse_reduction"], 1 - average(candidate_losses) / average(baseline_losses), "relative MSE change")
check(metrics["events_lower_mse"] == sum(delta < 0 for delta in deltas), "better events")
check(metrics["events_higher_mse"] == sum(delta > 0 for delta in deltas), "worse events")
check(result["coverage"]["feature_eligible_n"] == feature_n, "feature coverage count")
check(result["coverage"]["target_eligible_n"] == target_n, "target coverage count")
check(result["coverage"]["feature_exclusion_reason_counts"] == dict(reasons), "reason counts")
check(result["secondary_price_proxy"]["signal_n"] == signal_n == 0, "zero qualifying frozen signals")
check(result["secondary_price_proxy"]["feature_eligible_n"] == feature_n, "proxy eligible denominator")
for month, indices in monthly.items():
    actual = result["monthly"][month]["metrics"]
    check(actual["n"] == len(indices), f"{month}: denominator")
    close(actual["paired_mean_mse_delta"], average([deltas[index] for index in indices]), f"{month}: paired mean")
    close(actual["relative_mse_reduction"], 1 - average([candidate_losses[index] for index in indices]) / average([baseline_losses[index] for index in indices]), f"{month}: relative MSE")
loo_deltas = []
for row in result["leave_one_event_out"]["observations"]:
    excluded_index = complete_ids.index(row["removed_fixture_id"])
    indices = [index for index in range(len(deltas)) if index != excluded_index]
    expected = average([deltas[index] for index in indices])
    loo_deltas.append(expected)
    close(row["paired_mean_mse_delta"], expected, f"leave {row['removed_fixture_id']}: paired delta")
    close(row["relative_mse_reduction"], 1 - average([candidate_losses[index] for index in indices]) / average([baseline_losses[index] for index in indices]), f"leave {row['removed_fixture_id']}: relative MSE")
close(result["leave_one_event_out"]["paired_delta_min"], min(loo_deltas), "leave-one minimum")
close(result["leave_one_event_out"]["paired_delta_max"], max(loo_deltas), "leave-one maximum")
check(len(loo_deltas) == 50, "all 50 leave-one exclusions")
audit = {"status": "VERIFIED" if not errors else "ERRORS", "checks": checks, "errors": errors,
         "result_sha256": digest(WORK / "result.json"), "raw_opened": False, "evaluator_rerun": False,
         "new_api_requests": 0, "refits": 0, "excluded_events": excluded,
         "monthly": {month: result["monthly"][month]["metrics"] for month in monthly},
         "leave_one_delta_range": [min(loo_deltas), max(loo_deltas)], "primary": metrics,
         "feature_eligible_n": feature_n, "target_eligible_n": target_n, "signal_n": signal_n}
(WORK / "independent_result_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(audit, ensure_ascii=False))
raise SystemExit(bool(errors))
