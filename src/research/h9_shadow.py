"""Append-only H9 decisions and same-book settlement; permanently shadow-only."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

TRIAL = "h9-ou25-prospective-replication"
MIN_EDGE = 0.02
MAX_EDGE = 0.15
HORIZON = timedelta(minutes=90)


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n")


def emit(
    *,
    prediction: dict[str, Any],
    quotes: list[dict[str, Any]],
    approved_bookmaker: str | None,
    ledger: Path,
) -> dict[str, Any]:
    """Emit at most one immutable shadow pick from information known by H-1.5."""
    if not approved_bookmaker:
        return {"status": "BLOCKED_NO_STABLE_BOOKMAKER", "capital_enabled": False}
    event_id = str(prediction["event_id"])
    kickoff = _time(prediction["kickoff_at"])
    predicted = _time(prediction["predicted_at"])
    if predicted >= kickoff or predicted < kickoff - HORIZON - timedelta(minutes=15):
        raise ValueError("H9 prediction must be emitted in the H-1.5 decision window")
    existing = _read(ledger)
    if any(row.get("kind") == "decision" and row.get("event_id") == event_id for row in existing):
        return {"status": "ALREADY_EMITTED", "capital_enabled": False}
    eligible = []
    for quote in quotes:
        if (
            str(quote.get("source_event_id")) != event_id
            or quote.get("bookmaker") != approved_bookmaker
            or quote.get("market") != "ou2.5"
            or quote.get("selection") not in {"over", "under"}
        ):
            continue
        captured, ingested = _time(quote["odds_captured_at"]), _time(quote["retrieved_at"])
        if captured <= predicted and ingested <= predicted:
            eligible.append((quote["selection"], float(quote["decimal_odds"]), captured, quote))
    probabilities = {"over": float(prediction["p_over"]), "under": 1.0 - float(prediction["p_over"])}
    candidates = [
        (probabilities[selection] * odds - 1.0, selection, odds, captured, quote)
        for selection, odds, captured, quote in eligible
    ]
    if not candidates:
        return {"status": "NO_EXECUTABLE_QUOTE", "capital_enabled": False}
    edge, selection, odds, captured, quote = max(candidates, key=lambda item: item[0])
    if not MIN_EDGE < edge <= MAX_EDGE:
        return {"status": "NO_SELECTION", "edge": edge, "capital_enabled": False}
    row = {
        "kind": "decision",
        "decision_id": str(uuid.uuid4()),
        "trial": TRIAL,
        "event_id": event_id,
        "kickoff_at": kickoff.isoformat(),
        "predicted_at": predicted.isoformat(),
        "selection": selection,
        "model_probability": probabilities[selection],
        "edge": edge,
        "executed_odds": odds,
        "bookmaker": approved_bookmaker,
        "quote_published_at": captured.isoformat(),
        "quote_ingested_at": _time(quote["retrieved_at"]).isoformat(),
        "stake_units": 1.0,
        "scientific_state": "SHADOW",
        "capital_enabled": False,
        "policy_fingerprint": prediction.get("policy_fingerprint"),
        "elo_policy": prediction.get("elo_policy"),
    }
    _append(ledger, row)
    return {"status": "EMITTED", **row}


def settle(
    *,
    event_id: str,
    home_goals: int,
    away_goals: int,
    result_published_at: str,
    closing_quotes: list[dict[str, Any]],
    ledger: Path,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    rows = _read(ledger)
    decisions = [row for row in rows if row.get("kind") == "decision" and row.get("event_id") == str(event_id)]
    if len(decisions) != 1:
        raise ValueError("exactly one H9 decision is required")
    decision = decisions[0]
    if any(row.get("kind") == "settlement" and row.get("decision_id") == decision["decision_id"] for row in rows):
        return {"status": "ALREADY_SETTLED", "capital_enabled": False}
    kickoff = _time(decision["kickoff_at"])
    published = _time(result_published_at)
    if published < kickoff + timedelta(hours=2):
        raise ValueError("result is not stable for H9 settlement")
    candidates = []
    for quote in closing_quotes:
        if (
            str(quote.get("source_event_id")) == str(event_id)
            and quote.get("bookmaker") == decision["bookmaker"]
            and quote.get("market") == "ou2.5"
            and quote.get("selection") == decision["selection"]
        ):
            captured = _time(quote["odds_captured_at"])
            if captured < kickoff:
                candidates.append((captured, float(quote["decimal_odds"])))
    if not candidates:
        raise ValueError("same-book pre-kickoff closing quote is unavailable")
    _, closing_odds = max(candidates, key=lambda item: item[0])
    total = int(home_goals) + int(away_goals)
    won = total > 2.5 if decision["selection"] == "over" else total < 2.5
    pnl = decision["executed_odds"] - 1.0 if won else -1.0
    row = {
        "kind": "settlement",
        "decision_id": decision["decision_id"],
        "trial": TRIAL,
        "event_id": str(event_id),
        "recorded_at": recorded_at or datetime.now(UTC).isoformat(),
        "result_published_at": published.isoformat(),
        "score": f"{int(home_goals)}-{int(away_goals)}",
        "won": won,
        "pnl_units": pnl,
        "closing_odds_same_book": closing_odds,
        "clv": (decision["executed_odds"] - closing_odds) / closing_odds,
        "capital_enabled": False,
    }
    _append(ledger, row)
    return {"status": "SETTLED", **row}
