"""Pure point-in-time comparison of declared complete-market snapshots.

No provider, file, database, clock or betting operation is accessed here. A
snapshot hash documents supplied provenance; it does not authenticate the
provider or prove that a bookmaker accepted the displayed price.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

_SIDES = {"1x2": ("away", "draw", "home"), "ou25": ("over", "under"), "btts": ("no", "yes")}
_CLOCKS = ("observed_at", "available_at", "received_at", "kickoff_at")
_IDENTIFIERS = ("snapshot_id", "source", "source_event_id", "event_id", "bookmaker")
_FIELDS = set(_CLOCKS + _IDENTIFIERS) | {
    "market",
    "period",
    "line",
    "status",
    "odds",
    "raw_payload_hash",
    "snapshot_scope",
}


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"invalid_number:{name}")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"invalid_number:{name}") from exc
    if not math.isfinite(number):
        raise ValueError(f"invalid_number:{name}")
    return number


def _clock(value: Any, name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid_timestamp:{name}") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"invalid_timestamp:{name}")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class PricePolicy:
    """Explicit research assumptions, independent of all protected cohorts."""

    reference_books: tuple[str, ...]
    max_age_seconds: float
    max_skew_seconds: float
    cost_per_unit: float
    commission_on_profit: float
    min_reference_books: int = 1
    min_ev: float | None = None
    max_ev: float | None = None

    def __post_init__(self) -> None:
        books = self.reference_books
        if (
            not isinstance(books, tuple)
            or not books
            or any(not isinstance(book, str) or not book.strip() or book != book.strip() for book in books)
            or len(set(books)) != len(books)
        ):
            raise ValueError("reference_books must be a nonempty tuple of distinct bookmaker keys")
        if (
            isinstance(self.min_reference_books, bool)
            or not isinstance(self.min_reference_books, int)
            or not 1 <= self.min_reference_books <= len(books)
        ):
            raise ValueError("min_reference_books must be between one and the reference book count")
        if _number(self.max_age_seconds, "max_age_seconds") <= 0:
            raise ValueError("max_age_seconds must be positive")
        if _number(self.max_skew_seconds, "max_skew_seconds") < 0:
            raise ValueError("max_skew_seconds cannot be negative")
        if not 0 <= _number(self.cost_per_unit, "cost_per_unit") < 1:
            raise ValueError("cost_per_unit must be in [0, 1)")
        if not 0 <= _number(self.commission_on_profit, "commission_on_profit") < 1:
            raise ValueError("commission_on_profit must be in [0, 1)")
        for name in ("min_ev", "max_ev"):
            value = getattr(self, name)
            if value is not None and not 0 <= _number(value, name) <= 1:
                raise ValueError(f"{name} must be in [0, 1] or None")
        if self.min_ev is not None and self.max_ev is not None and self.min_ev > self.max_ev:
            raise ValueError("min_ev cannot exceed max_ev")


def _identity(row: Any) -> tuple[str, str, str] | None:
    if not isinstance(row, dict):
        return None
    parts = tuple(row.get(name) for name in ("event_id", "bookmaker", "market"))
    if all(isinstance(part, str) and part.strip() and part == part.strip() for part in parts) and parts[2] in _SIDES:
        return parts  # type: ignore[return-value]
    return None


def _normalize(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("snapshot_must_be_object")
    if any(not isinstance(key, str) for key in row):
        raise ValueError("snapshot_keys_must_be_strings")
    if missing := _FIELDS - row.keys():
        raise ValueError(f"missing_fields:{','.join(sorted(missing))}")
    if extra := row.keys() - _FIELDS:
        raise ValueError(f"unknown_fields:{','.join(sorted(extra))}")
    for name in _IDENTIFIERS:
        value = row[name]
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"invalid_identifier:{name}")
    if row["snapshot_scope"] != "complete_market":
        raise ValueError("snapshot_scope_must_be_complete_market")
    digest = row["raw_payload_hash"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None:
        raise ValueError("invalid_raw_payload_hash")
    market = row["market"]
    if not isinstance(market, str) or market not in _SIDES or row["period"] != "FT":
        raise ValueError("unsupported_market_or_period")
    if market == "ou25":
        if _number(row["line"], "line") != 2.5:
            raise ValueError("ou25_requires_line_2.5")
    elif row["line"] is not None:
        raise ValueError("line_must_be_null_for_1x2_or_btts")
    clocks = {name: _clock(row[name], name) for name in _CLOCKS}
    if not clocks["observed_at"] <= clocks["available_at"] <= clocks["received_at"]:
        raise ValueError("observation_availability_receipt_clock_order")
    status, odds = row["status"], row["odds"]
    if status not in ("active", "suspended", "unavailable") or not isinstance(odds, dict):
        raise ValueError("invalid_status_or_odds_object")
    if status == "active":
        if set(odds) != set(_SIDES[market]):
            raise ValueError("incomplete_or_mismatched_market")
        for side, odd in odds.items():
            if _number(odd, f"odds.{side}") <= 1:
                raise ValueError(f"invalid_decimal_odds:{side}")
    elif odds:
        raise ValueError("inactive_snapshot_must_not_contain_prices")
    return {
        **row,
        **clocks,
        "raw_payload_hash": digest.lower(),
        "odds": {side: float(odd) for side, odd in sorted(odds.items())},
    }


def _provenance(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **{name: row[name] for name in _IDENTIFIERS},
        **{name: row[name].isoformat() for name in _CLOCKS},
        "raw_payload_hash": row["raw_payload_hash"],
        "snapshot_scope": row["snapshot_scope"],
        "market": row["market"],
        "period": row["period"],
        "line": row["line"],
        "status": row["status"],
        "odds": dict(row["odds"]),
        "source_authentication_proven": False,
    }


def _canonical(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"), default=lambda item: item.isoformat())


def _fair(row: dict[str, Any]) -> dict[str, float]:
    implied = {side: 1.0 / odd for side, odd in row["odds"].items()}
    total = sum(implied.values())
    if total <= 1:
        raise ValueError("reference_has_no_positive_overround")
    return {side: value / total for side, value in implied.items()}


def scan_quotes(rows: list[dict], *, as_of: datetime, policy: PricePolicy) -> dict[str, Any]:
    """Evaluate every latest market state and choose at most one pick per event.

    Latest means latest local receipt no later than ``as_of``. Invalid latest
    states block earlier prices. An unorderable or unidentifiable malformed row
    blocks the entire batch because its effect on latest state is unknown.
    """
    decision = _clock(as_of, "as_of")
    if not isinstance(policy, PricePolicy):
        raise ValueError("policy must be PricePolicy")
    result: dict[str, Any] = {
        "schema_version": "price-strength-comparison/1",
        "status": "RESEARCH_ONLY",
        "capital_enabled": False,
        "execution_proven": False,
        "as_of": decision.isoformat(),
        "policy": {**asdict(policy), "reference_books": list(policy.reference_books)},
        "method": "mean-proportional-devig-independent-reference/v1",
        "validation_errors": [],
        "snapshot_reviews": [],
        "evaluations": [],
        "selected_candidates": [],
        "batch_blocked": False,
    }
    if not isinstance(rows, list):
        result["validation_errors"].append({"row_index": None, "reason": "rows_must_be_list"})
        result["batch_blocked"] = True
        return result
    states: dict[tuple, list[dict]] = defaultdict(list)
    sources: dict[tuple, set[str]] = defaultdict(set)
    snapshot_ids: dict[str, set[str]] = defaultdict(set)
    for index, raw in enumerate(rows):
        identifier = raw.get("snapshot_id") if isinstance(raw, dict) else None
        review = {"row_index": index, "snapshot_id": identifier if isinstance(identifier, str) else None}
        result["snapshot_reviews"].append(review)
        key = _identity(raw)
        try:
            received = _clock(raw.get("received_at"), "received_at") if isinstance(raw, dict) else None
        except ValueError:
            received = None
        try:
            row = _normalize(raw)
        except ValueError as exc:
            reason = str(exc)
            result["validation_errors"].append({**review, "reason": reason})
            review.update(status="rejected", reason=reason)
            if received is not None and received > decision:
                review["availability_reason"] = "received_after_as_of"
            elif key is not None and received is not None:
                states[key].append({"row": None, "received": received, "index": index})
            else:
                result["batch_blocked"] = True
            continue
        if row["received_at"] > decision:
            review.update(status="excluded", reason="received_after_as_of")
            continue
        sources[(row["event_id"], row["bookmaker"])].add(row["source"])
        snapshot_ids[row["snapshot_id"]].add(_canonical(row))
        assert key is not None  # _normalize validated every identity field above.
        states[key].append({"row": row, "received": row["received_at"], "index": index})

    conflicts = {identifier for identifier, versions in snapshot_ids.items() if len(versions) > 1}
    latest: dict[tuple, dict] = {}
    rejected: dict[tuple, str] = {}
    for key, history in sorted(states.items()):
        last_time = max(item["received"] for item in history)
        last = [item for item in history if item["received"] == last_time]
        for item in history:
            review = result["snapshot_reviews"][item["index"]]
            if "status" not in review:
                review.update(status="excluded", reason="superseded_snapshot")
        if any(item["row"] is None for item in last):
            rejected[key] = "latest_snapshot_invalid"
        elif len({_canonical(item["row"]) for item in last}) > 1:
            rejected[key] = "conflicting_latest_snapshots"
            result["validation_errors"].append({"row_index": last[0]["index"], "reason": rejected[key]})
        else:
            row = last[0]["row"]
            latest[key] = row
            if row["snapshot_id"] in conflicts:
                rejected[key] = "snapshot_id_conflict"
                result["validation_errors"].append({"row_index": last[0]["index"], "reason": rejected[key]})
            elif len(sources[(row["event_id"], row["bookmaker"])]) > 1:
                rejected[key] = "ambiguous_bookmaker_source"
            elif decision >= row["kickoff_at"]:
                rejected[key] = "decision_not_strictly_pre_kickoff"
            elif row["status"] != "active":
                rejected[key] = f"latest_snapshot_{row['status']}"
            elif (decision - row["observed_at"]).total_seconds() > policy.max_age_seconds:
                rejected[key] = "latest_snapshot_stale"
        for item in last:
            review = result["snapshot_reviews"][item["index"]]
            if key in rejected:
                review.update(status="rejected", reason=rejected[key])
            else:
                review.update(status="latest", reason="latest_available_snapshot")

    event_clocks: dict[str, set[datetime]] = defaultdict(set)
    event_sources: dict[tuple, set[str]] = defaultdict(set)
    source_events: dict[tuple, set[str]] = defaultdict(set)
    for row in latest.values():
        event_clocks[row["event_id"]].add(row["kickoff_at"])
        event_sources[(row["event_id"], row["source"])].add(row["source_event_id"])
        source_events[(row["source"], row["source_event_id"])].add(row["event_id"])
    for key, row in latest.items():
        if len(event_clocks[row["event_id"]]) > 1:
            rejected[key] = "event_kickoff_conflict"
        if len(event_sources[(row["event_id"], row["source"])]) > 1:
            rejected[key] = "event_source_identity_conflict"
        if len(source_events[(row["source"], row["source_event_id"])]) > 1:
            rejected[key] = "source_event_canonical_identity_conflict"
    if result["batch_blocked"]:
        rejected.update({key: "batch_validation_failed" for key in states})
    for key, history in states.items():
        if key in rejected:
            last_time = max(item["received"] for item in history)
            for item in history:
                if item["received"] == last_time:
                    result["snapshot_reviews"][item["index"]].update(status="rejected", reason=rejected[key])

    candidates = []
    for key in sorted(states):
        event_id, bookmaker, market = key
        base = {"event_id": event_id, "bookmaker": bookmaker, "market": market, "execution_proven": False}
        if key in rejected:
            result["evaluations"].append(
                {
                    **base,
                    "status": "rejected",
                    "reason": rejected[key],
                    "provenance": _provenance(latest[key]) if key in latest else None,
                }
            )
            continue
        offer = latest[key]
        reference_rows = []
        reference_exclusions = []
        for book in sorted(policy.reference_books):
            reference_key = (event_id, book, market)
            reason = None
            if book == bookmaker:
                reason = "offering_book_excluded_from_reference"
            elif reference_key not in latest:
                reason = rejected.get(reference_key, "reference_snapshot_missing")
            elif reference_key in rejected:
                reason = rejected[reference_key]
            else:
                reference = latest[reference_key]
                if any(
                    abs((reference[clock] - offer[clock]).total_seconds()) > policy.max_skew_seconds
                    for clock in ("observed_at", "available_at", "received_at")
                ):
                    reason = "reference_clock_skew"
                else:
                    try:
                        probabilities = _fair(reference)
                        reference_rows.append((reference, probabilities))
                    except ValueError as exc:
                        reason = str(exc)
            if reason:
                reference_exclusions.append({"bookmaker": book, "reason": reason})
        reason = None
        if len(reference_rows) < policy.min_reference_books:
            reason = "insufficient_independent_reference_books"
        elif any(
            (
                max(row[clock] for row, _ in reference_rows) - min(row[clock] for row, _ in reference_rows)
            ).total_seconds()
            > policy.max_skew_seconds
            for clock in ("observed_at", "available_at", "received_at")
        ):
            reason = "reference_clock_skew"
        fair = {}
        if reason is None:
            fair = {
                side: sum(probabilities[side] for _, probabilities in reference_rows) / len(reference_rows)
                for side in _SIDES[market]
            }
            normalization = sum(fair.values())
            fair = {side: value / normalization for side, value in fair.items()}
        reference_provenance = [_provenance(row) for row, _ in reference_rows]
        reference_fingerprint = None
        if reason is None:
            reference_fingerprint = hashlib.sha256(
                _canonical(
                    {
                        "as_of": result["as_of"],
                        "policy": result["policy"],
                        "method": result["method"],
                        "reference_provenance": reference_provenance,
                    }
                ).encode()
            ).hexdigest()
        for side, odd in offer["odds"].items():
            evaluation = {
                **base,
                "period": "FT",
                "line": offer["line"],
                "selection": side,
                "decimal_odds": odd,
                "status": "rejected",
                "reason": reason,
                "provenance": _provenance(offer),
                "reference_provenance": reference_provenance,
                "reference_probabilities": dict(fair) if reason is None else None,
                "reference_fingerprint": reference_fingerprint,
                "reference_books_used": [row["bookmaker"] for row, _ in reference_rows],
                "reference_exclusions": reference_exclusions,
                "reference_probability": None,
                "gross_ev": None,
                "net_ev": None,
            }
            if reason is None:
                probability = fair[side]
                gross = probability * odd - 1.0
                net = probability * (1 + (odd - 1) * (1 - policy.commission_on_profit)) - 1 - policy.cost_per_unit
                evaluation.update(reference_probability=probability, gross_ev=gross, net_ev=net)
                if net <= 0:
                    evaluation["reason"] = "non_positive_net_ev"
                elif policy.min_ev is not None and net < policy.min_ev:
                    evaluation["reason"] = "below_minimum_net_ev"
                elif policy.max_ev is not None and net > policy.max_ev:
                    evaluation["reason"] = "above_maximum_net_ev"
                else:
                    evaluation.update(status="candidate", reason="positive_net_ev_with_independent_reference")
                    fingerprint = {"as_of": result["as_of"], "policy": result["policy"], "evaluation": evaluation}
                    evaluation["candidate_id"] = hashlib.sha256(_canonical(fingerprint).encode()).hexdigest()
                    candidates.append(evaluation)
            result["evaluations"].append(evaluation)
    picked = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            -item["net_ev"],
            item["event_id"],
            item["market"],
            item["selection"],
            item["bookmaker"],
            item["provenance"]["snapshot_id"],
        ),
    ):
        if candidate["event_id"] in picked:
            candidate.update(status="not_selected", reason="one_candidate_per_event")
            continue
        picked.add(candidate["event_id"])
        candidate.update(status="selected_for_research", reason="highest_net_ev_for_event")
        result["selected_candidates"].append(dict(candidate))
    return result
