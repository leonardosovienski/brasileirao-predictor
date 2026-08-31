"""17 contratos reconstruídos para o coletor A1 OddsPapi."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from brasileirao_scripts.collect_odds_a1 import capture_complete
from brasileirao_scripts.collect_odds_a1 import main as collector_main
from brasileirao_scripts.evaluate_gate_a1 import evaluate
from brasileirao_predictor.collector_a1 import (
    OddsPapiClient,
    QuotaGuard,
    SnapshotStore,
    TeamAliases,
    build_snapshots,
    canonical_json,
    event_id,
    parse_utc,
    quota_status,
)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "odds_snapshot_v1.json"
KICKOFF = "2026-08-25T23:00:00Z"
CAPTURED = datetime(2026, 8, 25, 22, tzinfo=UTC)


@pytest.fixture
def aliases(tmp_path: Path) -> TeamAliases:
    path = tmp_path / "aliases.json"
    teams_path = tmp_path / "teams_brasileirao.json"
    path.write_text(
        json.dumps({"mapping_version": "teams-2026-08-24", "aliases": {"Home FC": "home", "Away FC": "away"}}),
        encoding="utf-8",
    )
    teams_path.write_text(
        json.dumps({"teams": {"Home": {"slug": "home"}, "Away": {"slug": "away"}}}),
        encoding="utf-8",
    )
    return TeamAliases(path)


@pytest.fixture
def payload() -> dict[str, object]:
    players = lambda price: {"players": {"0": {"price": price}}}  # noqa: E731
    return {
        "fixtureId": "fixture-1",
        "participant1Name": "Home FC",
        "participant2Name": "Away FC",
        "startTime": KICKOFF,
        "bookmakerOdds": {
            "pinnacle": {
                "bookmakerIsActive": True,
                "suspended": False,
                "markets": {"101": {"outcomes": {"101": players(2.1), "102": players(3.2), "103": players(3.5)}}},
            }
        },
    }


def rows(payload: dict[str, object], aliases: TeamAliases) -> list[dict[str, object]]:
    return build_snapshots(payload, aliases, CAPTURED)[0]


def test_01_key_absent_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ODDSPAPI_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ODDSPAPI_KEY"):
        OddsPapiClient()


def test_02_historical_endpoint_is_not_exposed() -> None:
    assert not hasattr(OddsPapiClient, "historical")
    assert not hasattr(OddsPapiClient, "historical_odds")


def test_03_fuzzy_only_suggests(aliases: TeamAliases) -> None:
    result = aliases.resolve("Hme FC")
    assert result.canonical is None
    assert result.suggestion == "Home FC"


def test_04_unknown_alias_quarantines(payload: dict[str, object], aliases: TeamAliases) -> None:
    payload["participant1Name"] = "Unknown"
    snapshots, quarantine = build_snapshots(payload, aliases, CAPTURED)
    assert snapshots == [] and quarantine[0]["reason"] == "unknown_team_alias"


def test_05_event_id_is_deterministic() -> None:
    assert event_id("home", "away", KICKOFF) == "br-serie-a|2026|home|away|2026-08-25"


def test_06_naive_timestamp_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        parse_utc("2026-08-25T22:00:00")


def test_07_equal_kickoff_rejected(payload: dict[str, object], aliases: TeamAliases) -> None:
    with pytest.raises(ValueError, match="strictly before"):
        build_snapshots(payload, aliases, parse_utc(KICKOFF))


def test_08_all_snapshots_are_unhomologated(payload: dict[str, object], aliases: TeamAliases) -> None:
    assert rows(payload, aliases) and all(item["homologated"] is False for item in rows(payload, aliases))


def test_totals_parser_does_not_collapse_other_lines_into_ou25(
    payload: dict[str, object], aliases: TeamAliases
) -> None:
    payload["bookmakerOdds"]["pinnacle"]["markets"]["totals"] = {  # type: ignore[index]
        "outcomes": {
            "all": {
                "players": {
                    "o15": {"price": 1.4, "bookmakerOutcomeId": "Over 1.5"},
                    "u15": {"price": 2.8, "bookmakerOutcomeId": "Under 1.5"},
                    "o25": {"price": 1.9, "bookmakerOutcomeId": "Over 2.5"},
                    "u25": {"price": 1.95, "bookmakerOutcomeId": "Under 2.5"},
                    "o35": {"price": 2.7, "bookmakerOutcomeId": "Over 3.5"},
                    "u35": {"price": 1.45, "bookmakerOutcomeId": "Under 3.5"},
                }
            }
        }
    }

    totals = [item for item in rows(payload, aliases) if item["market"] == "ou2.5"]
    assert [(item["selection"], item["odds"]) for item in totals] == [("over", 1.9), ("under", 1.95)]


def test_09_schema_rejects_additional_property(payload: dict[str, object], aliases: TeamAliases) -> None:
    item = rows(payload, aliases)[0]
    item["roi"] = 1
    assert list(Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(item))


def test_10_schema_rejects_sofascore_source(payload: dict[str, object], aliases: TeamAliases) -> None:
    item = rows(payload, aliases)[0]
    item["source_id"] = "sofascore_aggregate"
    assert list(Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(item))


def test_11_invalid_odds_go_to_quarantine(tmp_path: Path, payload: dict[str, object], aliases: TeamAliases) -> None:
    store = SnapshotStore(tmp_path / "snapshots", SCHEMA)
    item = rows(payload, aliases)[0]
    item["odds"] = 1.0
    assert store.append(item) == "conflict"
    assert (tmp_path / "odds_quarantine" / "quarantine.jsonl").exists()


def test_12_hash_chain_detects_tampering(tmp_path: Path, payload: dict[str, object], aliases: TeamAliases) -> None:
    store = SnapshotStore(tmp_path / "snapshots", SCHEMA)
    for item in rows(payload, aliases):
        assert store.append(item) == "written"
    path = next((tmp_path / "snapshots").glob("*.jsonl"))
    text = path.read_text(encoding="utf-8").replace('"odds": 2.1', '"odds": 9.9')
    path.write_text(text, encoding="utf-8")
    assert store.verify(path) is False


def test_13_identical_snapshot_is_deduplicated(
    tmp_path: Path, payload: dict[str, object], aliases: TeamAliases
) -> None:
    store = SnapshotStore(tmp_path / "snapshots", SCHEMA)
    item = rows(payload, aliases)[0]
    assert store.append(item) == "written"
    assert store.append(item) == "duplicate"


def test_14_same_identity_different_value_is_conflict(
    tmp_path: Path, payload: dict[str, object], aliases: TeamAliases
) -> None:
    store = SnapshotStore(tmp_path / "snapshots", SCHEMA)
    item = rows(payload, aliases)[0]
    assert store.append(item) == "written"
    changed = dict(item)
    changed["odds"] = 2.2
    changed.pop("hash_self")
    changed["hash_self"] = hashlib.sha256(canonical_json(changed)).hexdigest()
    assert store.append(changed) == "conflict"


def test_15_collector_exposes_no_financial_execution_api() -> None:
    forbidden = {"roi", "stake", "place_bet", "pick", "expected_value"}
    assert forbidden.isdisjoint(set(dir(OddsPapiClient)) | set(dir(SnapshotStore)))


def test_invalid_middle_row_does_not_poison_valid_batch_tail(
    tmp_path: Path, payload: dict[str, object], aliases: TeamAliases
) -> None:
    store = SnapshotStore(tmp_path / "snapshots", SCHEMA)
    batch = rows(payload, aliases)[:3]
    batch[1]["odds"] = 1.0

    assert store.append_batch(batch) == ["written", "conflict", "written"]
    path = next((tmp_path / "snapshots").glob("*.jsonl"))
    persisted = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(persisted) == 2
    assert persisted[1]["hash_prev"] == persisted[0]["hash_self"]
    assert store.verify(path) is True


def test_batch_retry_is_deduplicated(tmp_path: Path, payload: dict[str, object], aliases: TeamAliases) -> None:
    store = SnapshotStore(tmp_path / "snapshots", SCHEMA)
    batch = rows(payload, aliases)[:3]

    assert store.append_batch(batch) == ["written", "written", "written"]
    assert store.append_batch(batch) == ["duplicate", "duplicate", "duplicate"]


def test_operational_mirror_is_bitemporal_and_versions_reschedules(
    tmp_path: Path, payload: dict[str, object], aliases: TeamAliases
) -> None:
    import sqlite3

    db_path = tmp_path / "odds.db"
    store = SnapshotStore(tmp_path / "snapshots", SCHEMA, operational_db=db_path)
    first = rows(payload, aliases)[0]
    assert store.append(first) == "written"
    moved_payload = dict(payload)
    moved_payload["startTime"] = "2026-08-26T23:00:00Z"
    moved = build_snapshots(moved_payload, aliases, datetime(2026, 8, 26, 22, tzinfo=UTC))[0][0]
    assert store.append(moved) == "written"
    connection = sqlite3.connect(db_path)
    versions = connection.execute(
        "SELECT version,lifecycle_status,superseded_by FROM odds_event_versions ORDER BY version"
    ).fetchall()
    facts = connection.execute(
        "SELECT event_version,valid_from FROM odds_snapshot_facts ORDER BY valid_from"
    ).fetchall()
    assert versions[0][1] == "RESCHEDULED" and versions[0][2] == "fixture-1|v2"
    assert versions[1][0:2] == (2, "SCHEDULED")
    assert [row[0] for row in facts] == [1, 2]
    persisted = json.loads((tmp_path / "snapshots" / "2026-08-26.jsonl").read_text(encoding="utf-8"))
    assert persisted["event_version"] == 2
    assert persisted["lifecycle_status"] == "SCHEDULED"
    assert persisted["supersedes_event_version"] == 1


def test_json_duplicate_repairs_missing_operational_mirror(
    tmp_path: Path, payload: dict[str, object], aliases: TeamAliases
) -> None:
    import sqlite3

    db_path = tmp_path / "odds.db"
    store = SnapshotStore(tmp_path / "snapshots", SCHEMA, operational_db=db_path)
    item = rows(payload, aliases)[0]
    assert store.append(item) == "written"
    with sqlite3.connect(db_path) as connection:
        connection.execute("DELETE FROM odds_snapshot_facts")
    assert store.append(item) == "duplicate"
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM odds_snapshot_facts").fetchone()[0] == 1


def test_capture_window_is_not_closed_after_partial_batch_failure() -> None:
    snapshots = [{"snapshot_id": "a"}, {"snapshot_id": "b"}]
    assert capture_complete(snapshots, [], ["written", "duplicate"]) is True
    assert capture_complete(snapshots, [], ["written", "conflict"]) is False
    assert capture_complete(snapshots, [{"reason": "unknown_alias"}], ["written"]) is False


def test_16_economic_mode_is_rehearsal_only(tmp_path: Path) -> None:
    for day in range(1, 8):
        (tmp_path / f"2026-08-{day:02d}.json").write_text(json.dumps({"mode": "economic"}), encoding="utf-8")
    assert evaluate(tmp_path)["verdict"] == "REHEARSAL_ONLY_BUDGETED"


def test_17_full_mode_failure_restarts_clock(tmp_path: Path) -> None:
    for day in range(1, 8):
        (tmp_path / f"2026-08-{day:02d}.json").write_text(json.dumps({"mode": "full"}), encoding="utf-8")
    result = evaluate(tmp_path)
    assert result["verdict"] == "FAIL_RESTART_CLOCK"
    assert result["restart_clock_required"] is True
    assert result["criteria"]["oddspapi_key_rotated_and_attested"] is False
    assert result["external_evidence"]["key_rotation_attestation_present"] is False


def test_cli_reports_only_sanitized_runtime_detail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["collect_odds_a1.py", "--discover"])
    monkeypatch.setattr("brasileirao_scripts.collect_odds_a1.OddsPapiClient", lambda: (_ for _ in ()).throw(RuntimeError("safe")))
    assert collector_main() == 1
    assert json.loads(capsys.readouterr().err)["safe_detail"] == "safe"


def test_cli_hides_arbitrary_exception_text(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["collect_odds_a1.py", "--discover"])
    monkeypatch.setattr(
        "brasileirao_scripts.collect_odds_a1.OddsPapiClient",
        lambda: (_ for _ in ()).throw(ValueError("must-not-leak")),
    )
    assert collector_main() == 1
    output = json.loads(capsys.readouterr().err)
    assert output["safe_detail"] is None
    assert "must-not-leak" not in json.dumps(output)


def test_quota_status_accepts_nested_account_and_rejects_invalid() -> None:
    assert quota_status({"subscription": {"request_count": 12, "request_limit": 250}}) == (12, 250)
    with pytest.raises(RuntimeError, match="request_count"):
        quota_status({"subscription": {"request_limit": 250}})


def test_quota_guard_reserves_budget_limits_attempts_and_backs_off(tmp_path: Path) -> None:
    guard = QuotaGuard(tmp_path / "quota.json", reserve=20, max_attempts=2, backoff_minutes=30)
    now = datetime(2026, 8, 27, 12, tzinfo=UTC)
    assert guard.allow("f1", "T-1440m", now, 229, 250) == (True, "allowed")
    assert guard.allow("f1", "T-1440m", now, 230, 250) == (False, "monthly_reserve")
    guard.record("f1", "T-1440m", now)
    assert guard.allow("f1", "T-1440m", now, 100, 250) == (False, "backoff")
    later = datetime(2026, 8, 27, 13, tzinfo=UTC)
    assert guard.allow("f1", "T-1440m", later, 100, 250) == (True, "allowed")
    guard.record("f1", "T-1440m", later)
    assert guard.allow("f1", "T-1440m", later, 100, 250) == (False, "attempt_limit")
