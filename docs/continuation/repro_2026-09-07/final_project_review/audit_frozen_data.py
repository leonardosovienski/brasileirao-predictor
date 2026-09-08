"""Deterministic audit of explicitly authorized snapshots; never open a DB/cohort."""
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent / "new_split_backtest"
REPO = Path("C:/Users/Superleo13/projetos/brasileirao-predictor")
SPLIT = REPO / "data/research/season_2026_turn_split"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timezone missing")
    return dt


history = read(SPLIT / "historical_2021_2025.json")
schedule = read(SPLIT / "schedule_manifest.json")
events = read(WORK / "data/canonical_input_2026.json")
manifest = read(WORK / "data/extraction_manifest.json")
plan = read(WORK / "plan.json")
contract = read(REPO / "contracts/season-2026-turn-split-paper.json")
issues = []
profile = {"history": {}, "schedule_2026": {}, "input_2026": {}}
for year in range(2021, 2026):
    rows = [r for r in history if utc(r["kickoff"]).year == year]
    pairs = Counter((r["home"], r["away"]) for r in rows)
    games = Counter(t for r in rows for t in (r["home"], r["away"]))
    errors = [r["event_id"] for r in rows if any(type(r["result"][k]) is not int or r["result"][k] < 0 for k in ("home_goals", "away_goals"))]
    if len(rows) != 380 or len(games) != 20 or set(games.values()) != {38} or set(pairs.values()) != {1} or errors:
        issues.append({"historical_year_structure": year, "invalid_scores": errors})
    markets = {}
    for market, bounds in plan["selection"]["odds_bounds_inclusive"].items():
        complete, gated, overrounds = 0, 0, []
        for row in rows:
            odds = row["odds"][market]
            valid = all(type(o) in (float, int) and math.isfinite(o) and o > 1 for o in odds)
            complete += valid
            if valid:
                overround = math.fsum(1/o for o in odds)
                overrounds.append(overround)
                gated += all(bounds[0] <= o <= bounds[1] for o in odds) and 1 <= overround <= 1.3
        markets[market] = {"complete_vectors": complete, "fixed_gates_valid": gated, "overround_min": min(overrounds, default=None), "overround_max": max(overrounds, default=None)}
    profile["history"][str(year)] = {"events": len(rows), "teams": len(games), "matches_per_team": sorted(set(games.values())), "unique_ordered_pairs": len(pairs), "invalid_scores": errors, "markets": markets}

rounds = {}
for round_number in range(1, 39):
    rows = [r for r in schedule if r["round"] == round_number]
    teams = Counter(t for r in rows for t in (r["home_team"], r["away_team"]))
    expected_refs = set(range((round_number-1)*10+1, round_number*10+1))
    valid = len(rows) == 10 and len(teams) == 20 and set(teams.values()) == {1} and {r["cbf_ref"] for r in rows} == expected_refs
    rounds[str(round_number)] = valid
    if not valid:
        issues.append({"round_structure": round_number})
allpairs = Counter((r["home_team"], r["away_team"]) for r in schedule)
profile["schedule_2026"] = {"fixtures": len(schedule), "unique_event_ids": len({r["event_id"] for r in schedule}), "unique_ordered_pairs": len(allpairs), "ordered_pair_counts": sorted(set(allpairs.values())), "all_38_rounds_have_10_matches_20_teams_and_correct_references": all(rounds.values()), "role_counts": dict(Counter(r["role"] for r in schedule)), "identity_resolutions": contract["identity_resolutions"]}
if len(schedule) != 380 or len(allpairs) != 380:
    issues.append({"schedule_pair_structure": profile["schedule_2026"]})
by_id = {r["event_id"]: r for r in schedule}
for event in events:
    source = by_id.get(event["event_id"])
    if source is None or any(event[k] != source[k] for k in ("cbf_ref", "round", "role")) or (event["home"],event["away"],event["kickoff"]) != (source["home_team"],source["away_team"],source["kickoff_at"]):
        issues.append({"canonical_identity_mismatch": event["event_id"]})
completed = [r for r in events if r["completion_state"] == "COMPLETED"]
negative_observation_delay = [r["event_id"] for r in completed if r["result_observed_at"] and utc(r["result_observed_at"]) < utc(r["kickoff"])]
after_cutoff = [r["event_id"] for r in completed if utc(r["result_observed_at"]) > utc(plan["as_of_utc"])]
profile["input_2026"] = {"events": len(events), "completed": len(completed), "completed_with_observation_time": sum(r["result_observed_at"] is not None for r in completed), "negative_observation_delay_ids": negative_observation_delay, "after_cutoff_observation_ids": after_cutoff, "completion_by_role": manifest["summary_by_role"], "all_pending_have_no_result_or_odds": all(r["result"] is None and all(o is None for vector in r["odds"].values() for o in vector) for r in events if r["completion_state"] != "COMPLETED")}
checks = {
    "history": sha(SPLIT / "historical_2021_2025.json") == plan["data_sources"]["historical_sha256"],
    "schedule": sha(SPLIT / "schedule_manifest.json") == plan["data_sources"]["schedule_sha256"],
    "contract": sha(REPO / "contracts/season-2026-turn-split-paper.json") == plan["data_sources"]["contract_sha256"],
    "input": sha(WORK / "data/canonical_input_2026.json") == manifest["canonical_input_sha256"],
    "plan": sha(WORK / "plan.json") == manifest["plan_sha256"],
}
if not all(checks.values()) or negative_observation_delay or after_cutoff:
    issues.append({"hash_or_temporal_check": checks, "negative_delays": negative_observation_delay, "future_observations": after_cutoff})
result = {"status": "PASS" if not issues else "FAIL", "issues": issues, "source_hash_checks": checks, "profile": profile, "database_opened": False, "cohort_ledgers_opened": False}
(ROOT / "frozen_data_profile.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
