"""Offline The Odds API v4 receipt decoder, independent of protected collectors.

This module does not fetch odds or open a database. It preserves a complete
response as one observation, including empty/invalid states. A changed-at clock
and the presence of an odd never certify commercial availability or execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SPORT = "soccer_brazil_campeonato"
VERSION = "the-odds-api-receipt/2"


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed.astimezone(UTC)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError("non-finite JSON number")


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def decode_snapshot(
    raw: bytes, *, received_at: str, expected_sha256: str, expected_event_id: str | None = None
) -> dict[str, Any]:
    received = _utc(received_at)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise ValueError("raw SHA256 mismatch")
    payload = json.loads(raw, object_pairs_hook=_object, parse_constant=_nonfinite)
    if expected_event_id is not None:
        if not expected_event_id.strip() or not isinstance(payload, dict) or payload.get("id") != expected_event_id:
            raise ValueError("event response identity mismatch")
        events = [payload]
    elif isinstance(payload, list):
        events = payload
    else:
        raise ValueError("list response required; event endpoint requires expected_event_id")
    output = {
        "schema_version": VERSION,
        "source": "the_odds_api",
        "raw_sha256": digest,
        "received_at": received.isoformat(),
        "published_at": None,
        "observation_status": "VALID_EMPTY" if not events else "OBSERVED",
        "economic_evidence_eligible": False,
        "capital_authorized": False,
        "execution": "ABSTAIN",
        "events": [],
        "rejections": [],
    }
    seen_events = set()
    for index, event in enumerate(events):
        try:
            if not isinstance(event, dict) or event.get("sport_key") != SPORT:
                raise ValueError("event schema/sport mismatch")
            identity, home, away = event.get("id"), event.get("home_team"), event.get("away_team")
            if any(not isinstance(v, str) or not v.strip() for v in (identity, home, away)) or home == away:
                raise ValueError("invalid event identity")
            if identity in seen_events:
                raise ValueError("duplicate event identity")
            seen_events.add(identity)
            kickoff = _utc(event["commence_time"])
            books = event["bookmakers"]
            if not isinstance(books, list):
                raise ValueError("invalid bookmakers")
            normalized = {
                "source_event_id": identity,
                "home_team": home,
                "away_team": away,
                "kickoff_at": kickoff.isoformat(),
                "received_before_kickoff": received < kickoff,
                "bookmakers": [],
            }
            seen_books = set()
            for book in books:
                if not isinstance(book, dict) or not isinstance(book.get("key"), str) or not book["key"].strip():
                    raise ValueError("invalid bookmaker identity")
                name = book["key"]
                if name in seen_books:
                    raise ValueError("duplicate bookmaker")
                seen_books.add(name)
                changed = _utc(book["last_update"])
                if changed > received:
                    raise ValueError("book changed after receipt")
                markets = book.get("markets")
                if not isinstance(markets, list):
                    raise ValueError("invalid markets")
                normalized_book = {
                    "bookmaker": name,
                    "last_changed_at": changed.isoformat(),
                    "commercial_status": "UNKNOWN",
                    "markets": [],
                }
                seen_markets = set()
                for market in markets:
                    if not isinstance(market, dict):
                        raise ValueError("invalid market")
                    key = market.get("key")
                    if key not in {"h2h", "totals", "h2h_3_way_h1", "totals_h1"}:
                        continue
                    if key in seen_markets:
                        raise ValueError("duplicate market")
                    seen_markets.add(key)
                    market_changed = _utc(market["last_update"]) if "last_update" in market else changed
                    if market_changed > received:
                        raise ValueError("market changed after receipt")
                    outcomes = market.get("outcomes")
                    if not isinstance(outcomes, list):
                        raise ValueError("invalid outcomes")
                    by_line: dict[float | None, dict[str, float]] = {}
                    for outcome in outcomes:
                        if not isinstance(outcome, dict) or not _number(outcome.get("price")) or outcome["price"] <= 1:
                            raise ValueError("invalid decimal price")
                        is_total = key.startswith("totals")
                        line = outcome.get("point") if is_total else None
                        if is_total and (line is None or not _number(line) or line < 0):
                            raise ValueError("invalid total line")
                        if not is_total and outcome.get("point") is not None:
                            raise ValueError("line on a three-way market")
                        names = (
                            {"Over": "over", "Under": "under"}
                            if is_total
                            else {home: "home", "Draw": "draw", away: "away"}
                        )
                        outcome_name = outcome.get("name")
                        selection = names.get(outcome_name) if isinstance(outcome_name, str) else None
                        if selection is None:
                            raise ValueError("unknown selection")
                        selections = by_line.setdefault(line, {})
                        if selection in selections:
                            raise ValueError("duplicate selection")
                        selections[selection] = float(outcome["price"])
                    for line, selections in by_line.items():
                        expected = {"over", "under"} if key.startswith("totals") else {"home", "draw", "away"}
                        normalized_book["markets"].append(
                            {
                                "market": key,
                                "line": line,
                                "odds": selections,
                                "complete": set(selections) == expected,
                                "last_changed_at": market_changed.isoformat(),
                                "received_at": received.isoformat(),
                                "published_at": None,
                                "observation_status": "OBSERVED_COMPLETE"
                                if set(selections) == expected
                                else "INCOMPLETE",
                            }
                        )
                normalized["bookmakers"].append(normalized_book)
            output["events"].append(normalized)
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            output["rejections"].append({"event_index": index, "reason": str(exc)})
    if output["rejections"]:
        output["observation_status"] = "INVALID_RESPONSE"
        # No caller may salvage older/other rows from a corrupt response.
        output["events"] = []
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--received-at", required=True)
    parser.add_argument("--event-id")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = decode_snapshot(
        args.raw.read_bytes(),
        received_at=args.received_at,
        expected_sha256=args.sha256,
        expected_event_id=args.event_id,
    )
    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2)
    # Exclusive creation preserves every receipt/version; no operational default.
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(encoded + "\n")
    print(json.dumps({"observation_status": result["observation_status"], "execution": "ABSTAIN"}))
    if result["observation_status"] == "INVALID_RESPONSE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
