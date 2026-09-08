"""Read-only, exact-ID extraction for the explicitly authorized 2026 replay.

No cohort files, stored model forecasts, future outcomes, or result-only tables
are opened. All 380 official fixtures remain in the output, including pending
fixtures. The retrospective odds have no historical execution attestation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO = Path("C:/Users/Superleo13/projetos/brasileirao-predictor")
INPUT_HASH = "14153f7cbb348e9eef22a8e1c438757b1ef482951e2576d4a8381d7928e8e142"


def utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(UTC)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_schedule(schedule, expected_size=380):
    if len(schedule) != expected_size:
        raise ValueError("Incomplete official schedule")
    ids = [r["event_id"] for r in schedule]
    refs = [r["cbf_ref"] for r in schedule]
    if len(set(ids)) != len(ids) or len(set(refs)) != len(refs):
        raise ValueError("Duplicate canonical identity")
    for row in schedule:
        if row["season"] != 2026 or type(row["round"]) is not int or not 1 <= row["round"] <= 38:
            raise ValueError("Invalid official round or season")
        expected = "test_exploratory" if row["round"] <= 19 else "paper_betting"
        if row["role"] != expected:
            raise ValueError("Role must follow official round")
        if type(row["event_id"]) is not int or row["event_id"] <= 0:
            raise ValueError("Invalid canonical event ID")
        if row["event_id"] in row.get("superseded_event_ids", []):
            raise ValueError("Canonical event is superseded")
        if row.get("kickoff_at") and utc(row["kickoff_at"]).year != 2026:
            raise ValueError("Kickoff is outside 2026")


def eligible_ids(schedule, as_of, completion_buffer_hours):
    cutoff = utc(as_of) - timedelta(hours=completion_buffer_hours)
    return [r["event_id"] for r in schedule if r.get("kickoff_at") and utc(r["kickoff_at"]) <= cutoff]


def query_rows(db_path, ids, as_of, completion_buffer_hours):
    """The exact identity/date/time boundary exists inside SQL, before fetch."""
    if not ids:
        return []
    cutoff = (utc(as_of) - timedelta(hours=completion_buffer_hours)).isoformat()
    marks = ",".join("?" for _ in ids)
    sql = f"""
    SELECT s.event_id, s.date AS s_date, s.kickoff_at, s.home_team AS s_home,
           s.away_team AS s_away, s.home_score AS s_home_score,
           s.away_score AS s_away_score, s.superseded_by_event_id,
           s.result_observed_at, m.date, m.home_team, m.away_team,
           m.home_score, m.away_score, m.tournament, m.city, m.neutral,
           s.odds_home, s.odds_draw, s.odds_away, s.odds_over, s.odds_under,
           s.odds_btts_yes, s.odds_btts_no
      FROM sofascore_matches s LEFT JOIN matches m ON m.event_id = s.event_id
     WHERE s.event_id IN ({marks})
       AND s.date >= '2026-01-01' AND s.date < '2027-01-01'
       AND julianday(s.kickoff_at) <= julianday(?)
       AND (s.result_observed_at IS NULL OR julianday(s.result_observed_at) <= julianday(?))
       AND (m.date IS NULL OR (m.date >= '2026-01-01' AND m.date < '2027-01-01'))
     ORDER BY s.event_id
    """
    connection = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.row_factory = sqlite3.Row
        return [dict(r) for r in connection.execute(sql, [*ids, cutoff, utc(as_of).isoformat()]).fetchall()]
    finally:
        connection.close()


def valid_goal(value):
    return type(value) is int and value >= 0


def clean_odd(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 1:
        return None
    return float(value)


def materialize(schedule, rows, as_of, completion_buffer_hours, expected_size=380):
    validate_schedule(schedule, expected_size)
    if completion_buffer_hours < 0:
        raise ValueError("Completion buffer cannot be negative")
    allowed = set(eligible_ids(schedule, as_of, completion_buffer_hours))
    source = {}
    for row in rows:
        if row["event_id"] not in allowed or row["event_id"] in source:
            raise ValueError("Unexpected or duplicate database identity")
        source[row["event_id"]] = row
    out = []
    for fixture in schedule:
        event = {
            "event_id": fixture["event_id"], "cbf_ref": fixture["cbf_ref"],
            "season": 2026, "round": fixture["round"], "role": fixture["role"],
            "home": fixture["home_team"], "away": fixture["away_team"],
            "kickoff": fixture.get("kickoff_at"), "date": None,
            "tournament": "Brasileirão Série A", "city": None, "neutral": 0,
            "result": None, "odds": {"1x2": [None]*3, "ou25": [None]*2, "btts": [None]*2},
            "completion_state": None, "result_observed_at": None,
            "odds_provenance": "retrospective_sofascore_flat_no_bookmaker_or_observed_at",
            "odds_execution_attested": False,
        }
        if event["kickoff"]:
            event["date"] = utc(event["kickoff"]).date().isoformat()
        row = source.get(event["event_id"])
        if not event["kickoff"]:
            state = "PENDING_KICKOFF"
        elif event["event_id"] not in allowed:
            state = "PENDING_COMPLETION_BUFFER"
        elif row is None:
            state = "NO_ELIGIBLE_DATABASE_ROW"
        elif row.get("superseded_by_event_id") is not None:
            state = "REJECTED_SUPERSEDED_IDENTITY"
        elif utc(row["kickoff_at"]) != utc(event["kickoff"]):
            state = "REJECTED_KICKOFF_MISMATCH"
        elif (row.get("s_home"), row.get("s_away")) != (event["home"], event["away"]):
            state = "REJECTED_TEAM_MISMATCH"
        elif row.get("date") is None:
            state = "NO_MATCHES_RESULT_ROW"
        elif (row.get("home_team"), row.get("away_team")) != (event["home"], event["away"]):
            state = "REJECTED_MATCHES_TEAM_MISMATCH"
        elif any(row.get(key) is None for key in ("home_score", "away_score", "s_home_score", "s_away_score")):
            state = "PENDING_RESULT"
        elif not all(valid_goal(row[key]) for key in ("home_score", "away_score", "s_home_score", "s_away_score")):
            state = "REJECTED_INVALID_RESULT"
        elif (row["home_score"], row["away_score"]) != (row["s_home_score"], row["s_away_score"]):
            state = "REJECTED_RESULT_CONFLICT"
        else:
            observed = row.get("result_observed_at")
            try:
                valid_observed = observed is None or utc(observed) <= utc(as_of)
            except (ValueError, AttributeError):
                valid_observed = False
            if not valid_observed:
                state = "RESULT_UNAVAILABLE_AS_OF"
            else:
                state = "COMPLETED"
                event["result"] = {"home_goals": row["home_score"], "away_goals": row["away_score"], "home_xg": None, "away_xg": None}
                event["result_observed_at"] = observed
                event["tournament"] = row.get("tournament") or event["tournament"]
                event["city"] = row.get("city")
                event["neutral"] = int(row.get("neutral") or 0)
                event["odds"] = {
                    "1x2": [clean_odd(row.get(k)) for k in ("odds_home", "odds_draw", "odds_away")],
                    "ou25": [clean_odd(row.get(k)) for k in ("odds_over", "odds_under")],
                    "btts": [clean_odd(row.get(k)) for k in ("odds_btts_yes", "odds_btts_no")],
                }
        event["completion_state"] = state
        out.append(event)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=REPO)
    args = parser.parse_args()
    if sha(args.plan) != args.plan_sha256:
        raise ValueError("Frozen plan hash mismatch")
    plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
    # Exact names finalized with the parent before execution.
    as_of = plan["as_of_utc"]
    buffer_hours = plan["completion_buffer_hours"]
    source_dir = args.repo / "data/research/season_2026_turn_split"
    schedule_path = source_dir / "schedule_manifest.json"
    history_path = source_dir / "historical_2021_2025.json"
    contract_path = args.repo / "contracts/season-2026-turn-split-paper.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8-sig"))
    if sha(schedule_path) != contract["schedule_manifest_sha256"] or sha(history_path) != INPUT_HASH:
        raise ValueError("Frozen split source hash mismatch")
    schedule = json.loads(schedule_path.read_text(encoding="utf-8-sig"))
    validate_schedule(schedule)
    path = args.outdir / "canonical_input_2026.json"
    if path.exists():
        raise ValueError("Refusing to overwrite already extracted 2026 input")
    queried_ids = eligible_ids(schedule, as_of, buffer_hours)
    rows = query_rows(args.repo / "data/matches.db", queried_ids, as_of, buffer_hours)
    events = materialize(schedule, rows, as_of, buffer_hours)
    args.outdir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    summary = {}
    for role in ("test_exploratory", "paper_betting"):
        part = [r for r in events if r["role"] == role]
        summary[role] = {
            "official_fixtures": len(part),
            "completion_states": dict(Counter(r["completion_state"] for r in part)),
            "complete_retrospective_odds_vectors": {
                market: sum(r["completion_state"] == "COMPLETED" and all(v is not None for v in r["odds"][market]) for r in part)
                for market in ("1x2", "ou25", "btts")
            },
        }
    manifest = {
        "as_of_utc": as_of, "completion_buffer_hours": buffer_hours,
        "plan_sha256": args.plan_sha256, "script_sha256": sha(Path(__file__)),
        "schedule_sha256": sha(schedule_path), "historical_input_sha256": sha(history_path),
        "canonical_input_sha256": sha(path), "queried_canonical_ids": queried_ids,
        "queried_ids_count": len(queried_ids), "database_rows_fetched": len(rows),
        "all_official_fixtures_preserved": len(events) == 380,
        "summary_by_role": summary,
        "sql_read_only": True, "cohort_ledgers_read": False,
        "limitations": [
            "Retrospective flat odds are not attested available before kickoff.",
            "Completed means concordant integer scores in two tables plus completion buffer, not provider lifecycle verification.",
            "Missing result_observed_at uses only the declared completion buffer as an availability assumption.",
            "Games without data remain in the official 190-per-turn denominator.",
        ],
    }
    (args.outdir / "extraction_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
