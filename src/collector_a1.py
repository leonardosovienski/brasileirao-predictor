"""Coletor OddsPapi do Gate A1: append-only, PIT e sempre não homologado."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Literal, cast

import requests
from jsonschema import Draft202012Validator, FormatChecker

SOURCE_ID = "oddspapi_v4"
BASE_URL = "https://api.oddspapi.io/v4"
TOURNAMENT_ID = 325
TARGET_BOOKMAKERS = (
    "pinnacle",
    "betano.bet.br",
    "estrelabet",
    "sportingbet.bet.br",
    "superbet.bet.br",
    "kto",
    "pixbet",
)
CadenceMode = Literal["economic", "full"]


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True)
class AliasResult:
    canonical: str | None
    suggestion: str | None


class TeamAliases:
    def __init__(self, path: Path) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.mapping_version = str(payload["mapping_version"])
        self.aliases = {str(key): str(value) for key, value in payload["aliases"].items()}

    def resolve(self, source_name: str) -> AliasResult:
        if source_name in self.aliases:
            return AliasResult(self.aliases[source_name], None)
        suggestions = get_close_matches(source_name, self.aliases, n=1, cutoff=0.72)
        return AliasResult(None, suggestions[0] if suggestions else None)


class OddsPapiClient:
    """Cliente somente de endpoints prospectivos; não expõe histórico."""

    def __init__(self, api_key: str | None = None, timeout: int = 30) -> None:
        self._api_key = (api_key or os.getenv("ODDSPAPI_KEY", "")).strip()
        if not self._api_key:
            raise RuntimeError("ODDSPAPI_KEY ausente")
        self.timeout = timeout

    def _get(self, endpoint: str, **params: object) -> Any:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params=cast(Any, {**params, "apiKey": self._api_key}),
            timeout=self.timeout,
        )
        if response.status_code != 200:
            detail = response.text[:240].replace(self._api_key, "[REDACTED]")
            raise RuntimeError(f"OddsPapi HTTP {response.status_code}: {detail}")
        return response.json()

    def fixtures(self, start: str, end: str) -> list[dict[str, Any]]:
        payload = self._get("fixtures", sportId=10, tournamentId=TOURNAMENT_ID, **{"from": start, "to": end})
        if not isinstance(payload, list):
            raise RuntimeError("payload de fixtures inválido")
        return [item for item in payload if isinstance(item, dict)]

    def odds(self, fixture_id: str) -> dict[str, Any]:
        payload = self._get("odds", fixtureId=fixture_id, oddsFormat="decimal", verbosity=3)
        if not isinstance(payload, dict):
            raise RuntimeError("payload de odds inválido")
        return payload


class SnapshotStore:
    def __init__(self, root: Path, schema_path: Path, quarantine_root: Path | None = None) -> None:
        self.root = root
        self.quarantine_root = quarantine_root or root.parent / "odds_quarantine"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def _path(self, captured_at: str) -> Path:
        return self.root / f"{parse_utc(captured_at).date().isoformat()}.jsonl"

    @staticmethod
    def _identity(snapshot: dict[str, Any]) -> tuple[Any, ...]:
        return tuple(
            snapshot[key] for key in ("source_event_id", "bookmaker", "market", "selection", "line", "captured_at")
        )

    def quarantine(self, reason: str, payload: dict[str, Any]) -> None:
        self.quarantine_root.mkdir(parents=True, exist_ok=True)
        record = {"recorded_at": utc_text(datetime.now(UTC)), "reason": reason, "payload": payload}
        with (self.quarantine_root / "quarantine.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def append(self, snapshot: dict[str, Any]) -> Literal["written", "duplicate", "conflict"]:
        errors = sorted(self.validator.iter_errors(snapshot), key=lambda error: list(error.path))
        if errors:
            self.quarantine("schema_invalid: " + errors[0].message, snapshot)
            return "conflict"
        captured = parse_utc(snapshot["captured_at"])
        kickoff = parse_utc(snapshot["kickoff_at"])
        if captured >= kickoff:
            self.quarantine("pit_violation", snapshot)
            return "conflict"
        path = self._path(snapshot["captured_at"])
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
        same = [item for item in existing if self._identity(item) == self._identity(snapshot)]
        if same:
            if any(item["hash_self"] == snapshot["hash_self"] for item in same):
                return "duplicate"
            self.quarantine("identity_conflict", snapshot)
            return "conflict"
        expected_prev = existing[-1]["hash_self"] if existing else None
        if snapshot["hash_prev"] != expected_prev:
            self.quarantine("hash_prev_mismatch", snapshot)
            return "conflict"
        material = dict(snapshot)
        claimed = material.pop("hash_self")
        if hashlib.sha256(canonical_json(material)).hexdigest() != claimed:
            self.quarantine("hash_self_mismatch", snapshot)
            return "conflict"
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n")
        return "written"

    def verify(self, path: Path) -> bool:
        previous: str | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            if item["hash_prev"] != previous:
                return False
            claimed = item.pop("hash_self")
            if hashlib.sha256(canonical_json(item)).hexdigest() != claimed:
                return False
            previous = claimed
        return True

    def seal(self, path: Path) -> dict[str, Any]:
        if not self.verify(path):
            raise RuntimeError("hash-chain inválida")
        seal = {
            "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sealed_at": utc_text(datetime.now(UTC)),
        }
        path.with_suffix(".seal.json").write_text(json.dumps(seal, indent=2) + "\n", encoding="utf-8")
        return seal


def event_id(home: str, away: str, kickoff_at: str) -> str:
    return f"br-serie-a|2026|{home}|{away}|{parse_utc(kickoff_at).date().isoformat()}"


def _market_rows(book: dict[str, Any]) -> list[tuple[str, str, float | None, float, str]]:
    rows: list[tuple[str, str, float | None, float, str]] = []
    for market_id, market in book.get("markets", {}).items():
        outcomes = market.get("outcomes", {})
        if market_id == "101":
            names = {"101": "home", "102": "draw", "103": "away"}
            for outcome_id, outcome in outcomes.items():
                for player in outcome.get("players", {}).values():
                    if outcome_id in names and isinstance(player.get("price"), int | float):
                        rows.append(("1x2", names[outcome_id], None, float(player["price"]), "normal"))
            continue
        flattened = [player for outcome in outcomes.values() for player in outcome.get("players", {}).values()]
        labels = [str(player.get("bookmakerOutcomeId", "")).casefold() for player in flattened]
        if labels and all(any(side in label for side in ("over", "under")) for label in labels):
            if any("2.5" in label for label in labels):
                for player, label in zip(flattened, labels, strict=True):
                    side = "over" if "over" in label else "under"
                    if isinstance(player.get("price"), int | float):
                        rows.append(("ou2.5", side, 2.5, float(player["price"]), "unverified"))
        elif set(labels) == {"yes", "no"}:
            for player, label in zip(flattened, labels, strict=True):
                if isinstance(player.get("price"), int | float):
                    rows.append(("btts", label, None, float(player["price"]), "unverified"))
    return rows


def build_snapshots(
    payload: dict[str, Any], aliases: TeamAliases, captured_at: datetime, hash_prev: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    home_result = aliases.resolve(str(payload.get("participant1Name", "")))
    away_result = aliases.resolve(str(payload.get("participant2Name", "")))
    if not home_result.canonical or not away_result.canonical:
        return [], [
            {
                "reason": "unknown_team_alias",
                "home": payload.get("participant1Name"),
                "away": payload.get("participant2Name"),
                "home_suggestion": home_result.suggestion,
                "away_suggestion": away_result.suggestion,
            }
        ]
    kickoff = str(payload["startTime"])
    if captured_at >= parse_utc(kickoff):
        raise ValueError("captured_at must be strictly before kickoff_at")
    canonical_event = event_id(home_result.canonical, away_result.canonical, kickoff)
    snapshots: list[dict[str, Any]] = []
    previous = hash_prev
    bookmaker_odds = payload.get("bookmakerOdds", {})
    for bookmaker in TARGET_BOOKMAKERS:
        book = bookmaker_odds.get(bookmaker)
        if not isinstance(book, dict):
            continue
        status = "suspended" if book.get("suspended") else "active" if book.get("bookmakerIsActive", True) else "closed"
        for market, selection, line, odd, identity_status in _market_rows(book):
            material: dict[str, Any] = {
                "schema_version": "odds_snapshot/1",
                "snapshot_id": "pending",
                "source_id": SOURCE_ID,
                "source_event_id": str(payload["fixtureId"]),
                "event_id": canonical_event,
                "bookmaker": bookmaker,
                "market": market,
                "selection": selection,
                "line": line,
                "odds": odd,
                "status": status,
                "identity_status": identity_status,
                "captured_at": utc_text(captured_at),
                "kickoff_at": utc_text(parse_utc(kickoff)),
                "mapping_version": aliases.mapping_version,
                "homologated": False,
                "hash_prev": previous,
                "supersedes": None,
            }
            material["snapshot_id"] = hashlib.sha256(canonical_json(material)).hexdigest()[:24]
            material["hash_self"] = hashlib.sha256(canonical_json(material)).hexdigest()
            previous = material["hash_self"]
            snapshots.append(material)
    return snapshots, []


def compute_daily_metrics(
    snapshots: list[dict[str, Any]], expected_event_ids: set[str], *, mode: CadenceMode = "economic"
) -> dict[str, Any]:
    events = {item["event_id"] for item in snapshots}
    event_coverage = len(events & expected_event_ids) / len(expected_event_ids) if expected_event_ids else 0.0
    expected_markets = len(events) * len(TARGET_BOOKMAKERS) * 3
    present_markets = {(item["event_id"], item["bookmaker"], item["market"]) for item in snapshots}
    books = {item["bookmaker"] for item in snapshots}
    conflicts = sum(item.get("collector_state") == "conflict" for item in snapshots)
    capture_times = sorted({parse_utc(item["captured_at"]) for item in snapshots})
    gaps = [(right - left).total_seconds() for left, right in zip(capture_times, capture_times[1:], strict=False)]
    continuity = None if mode == "economic" else (sum(gap <= 3600 for gap in gaps) / len(gaps) if gaps else 0.0)
    return {
        "schema_version": "collector_metrics/1",
        "mode": mode,
        "calculated_at": utc_text(datetime.now(UTC)),
        "event_coverage": event_coverage,
        "market_coverage": len(present_markets) / expected_markets if expected_markets else 0.0,
        "continuity": continuity,
        "freshness": None
        if not snapshots
        else max(
            (parse_utc(item["kickoff_at"]) - parse_utc(item["captured_at"])).total_seconds() for item in snapshots
        ),
        "identity_resolution_rate": 1.0 if snapshots else 0.0,
        "conflict_rate": conflicts / len(snapshots) if snapshots else 0.0,
        "reference_present": "pinnacle" in books,
        "soft_books_count": len(books - {"pinnacle"}),
        "max_gap_seconds": None if mode == "economic" else (max(gaps) if gaps else None),
        "snapshots": len(snapshots),
        "homologated": False,
    }


def safe_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", value.casefold()).strip("-")
