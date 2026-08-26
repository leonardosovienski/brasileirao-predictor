"""17 contratos reconstruídos para o coletor A1 OddsPapi."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.evaluate_gate_a1 import evaluate
from src.collector_a1 import (
    OddsPapiClient,
    SnapshotStore,
    TeamAliases,
    build_snapshots,
    canonical_json,
    event_id,
    parse_utc,
)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "odds_snapshot_v1.json"
KICKOFF = "2026-08-25T23:00:00Z"
CAPTURED = datetime(2026, 8, 25, 22, tzinfo=UTC)


@pytest.fixture
def aliases(tmp_path: Path) -> TeamAliases:
    path = tmp_path / "aliases.json"
    path.write_text(
        json.dumps({"mapping_version": "teams-2026-08-24", "aliases": {"Home FC": "home", "Away FC": "away"}}),
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


def test_16_economic_mode_is_rehearsal_only(tmp_path: Path) -> None:
    for day in range(1, 8):
        (tmp_path / f"2026-08-{day:02d}.json").write_text(json.dumps({"mode": "economic"}), encoding="utf-8")
    assert evaluate(tmp_path)["verdict"] == "REHEARSAL_ONLY"


def test_17_full_mode_failure_restarts_clock(tmp_path: Path) -> None:
    for day in range(1, 8):
        (tmp_path / f"2026-08-{day:02d}.json").write_text(json.dumps({"mode": "full"}), encoding="utf-8")
    result = evaluate(tmp_path)
    assert result["verdict"] == "FAIL_RESTART_CLOCK"
    assert result["restart_clock_required"] is True
