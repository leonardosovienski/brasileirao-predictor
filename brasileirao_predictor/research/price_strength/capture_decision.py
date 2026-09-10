"""Offline API receipt -> conditional comparison -> explicit execution abstention.

This adapter does not authenticate a provider, infer bookmaker publication,
settle a match, or send an order. All three normalized clocks describe local
availability of the same complete API response, not three independent clocks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

from .artifacts import read_hashed, write_artifacts
from .historical_admission import timestamp
from .live_capture_admission import audit_capture, strict_json_loads
from .quotes import PricePolicy, scan_quotes

_BOOKS = ("pinnacle", "bet365.bet.br")
_MISSING = [
    "bookmaker_publication_and_personal_offer_availability",
    "accepted_price_and_stake",
    "offer_capacity_and_currency",
    "actual_variable_and_fixed_costs",
    "independent_future_economic_validation",
]


def decide_captures(captures: list[tuple[bytes | None, dict[str, Any]]], *, contract: dict[str, Any]) -> dict[str, Any]:
    """Use the latest response at the declared cutoff, never an older good row."""
    if (
        set(contract)
        != {"schema_version", "fixture_id", "identity", "kickoff_at", "decision_at", "policy", "initial_bankroll_units"}
        or contract["schema_version"] != "api-capture-decision/1"
    ):
        raise ValueError("invalid_decision_contract")
    fixture = contract["fixture_id"]
    if not isinstance(fixture, str) or not fixture or fixture != fixture.strip():
        raise ValueError("invalid_frozen_fixture")
    identity = contract["identity"]
    if (
        not isinstance(identity, dict)
        or set(identity) != {"participant1Id", "participant2Id", "sportId", "tournamentId", "seasonId"}
        or any(type(v) is not int or v <= 0 for v in identity.values())
        or identity["participant1Id"] == identity["participant2Id"]
    ):
        raise ValueError("invalid_frozen_identity")
    cutoff, kickoff = timestamp(contract["decision_at"]), timestamp(contract["kickoff_at"])
    if cutoff >= kickoff:
        raise ValueError("decision_must_precede_frozen_kickoff")
    raw_policy = contract["policy"]
    if not isinstance(raw_policy, dict) or raw_policy.get("reference_books") != ["pinnacle"]:
        raise ValueError("adapter_requires_frozen_pinnacle_reference")
    policy = PricePolicy(**{**raw_policy, "reference_books": tuple(raw_policy["reference_books"])})
    bank = contract["initial_bankroll_units"]
    if type(bank) not in (int, float) or not math.isfinite(bank) or bank <= 0:
        raise ValueError("invalid_scenario_bankroll")
    result: dict[str, Any] = {
        "schema_version": "api-capture-decision/1",
        "fixture_id": fixture,
        "decision_at": cutoff.isoformat(),
        "kickoff_at": kickoff.isoformat(),
        "action": "ABSTAIN",
        "execution_admitted": False,
        "profitability_established": False,
        "real_capital_enabled": False,
        "labels_accessed": False,
        "clock_semantics": "local_API_response_availability_only_not_bookmaker_publication",
        "cost_semantics": "explicit_hypothetical_policy_not_verified_costs",
        "missing_execution_evidence": list(_MISSING),
        "capture_reviews": [],
        "latest_capture_sha256": None,
        "api_audit": None,
        "conditional_scan": None,
        "portfolio": {
            "initial_bankroll_units": float(bank),
            "stakes_units": 0.0,
            "bets": 0,
            "abstentions": 1,
            "locked_capital_units": 0.0,
            "betting_pnl_units": 0.0,
            "bankroll_before_unknown_fixed_costs_units": float(bank),
            "actual_fixed_costs_units": None,
            "total_net_pnl_units": None,
            "roi_on_stakes": None,
            "return_on_bankroll_after_all_costs": None,
        },
    }
    states = []
    malformed_clock = False
    for raw, receipt in captures:
        digest = hashlib.sha256(raw).hexdigest() if raw is not None else None
        review = {"sha256": digest, "reason": "eligible_for_latest_selection"}
        result["capture_reviews"].append(review)
        try:
            received = timestamp(receipt["received_at"])
            started = timestamp(receipt["requested_at"])
            if received < started:
                raise ValueError("receipt_before_request")
        except (ValueError, TypeError, KeyError, OverflowError):
            review["reason"] = "ambiguous_receipt_clock"
            malformed_clock = True
            continue
        if received > cutoff:
            review["reason"] = "not_received_by_cutoff"
            continue
        states.append((received, raw, receipt, review))
    if malformed_clock:
        result["reason"] = "AMBIGUOUS_RECEIPT_CLOCK_NO_FALLBACK"
        return result
    if not states:
        result["reason"] = "NO_CAPTURE_RECEIVED_BY_CUTOFF"
        return result
    latest_time = max(item[0] for item in states)
    latest = [item for item in states if item[0] == latest_time]
    # Equal local times cannot establish a canonical revision, including a
    # failed receipt versus a good receipt with identical payload bytes.
    if len(latest) != 1:
        result["reason"] = "AMBIGUOUS_LATEST_CAPTURE_NO_FALLBACK"
        return result
    received, raw, receipt, review = latest[0]
    for item in states:
        item[3]["reason"] = "latest_at_cutoff" if item is latest[0] else "superseded_by_later_receipt"
    result["latest_capture_sha256"] = review["sha256"]
    if (
        raw is None
        or receipt.get("endpoint") != "https://api.oddspapi.io/v4/odds"
        or receipt.get("parameters")
        != {"fixtureId": fixture, "bookmakers": "pinnacle,bet365.bet.br", "oddsFormat": "decimal"}
        or receipt.get("status") != "SAVED"
        or type(receipt.get("http_status")) is not int
        or receipt["http_status"] != 200
        or receipt.get("sha256") != review["sha256"]
        or type(receipt.get("bytes")) is not int
        or receipt["bytes"] != len(raw)
    ):
        result["reason"] = "LATEST_TRANSPORT_OR_INTEGRITY_REJECTED"
        return result
    if (cutoff - received).total_seconds() > policy.max_age_seconds:
        result["reason"] = "LATEST_API_RESPONSE_STALE"
        return result
    try:
        payload = strict_json_loads(raw)
        if not isinstance(payload, dict) or timestamp(payload.get("startTime")) != kickoff:
            result["reason"] = "FROZEN_KICKOFF_MISMATCH"
            return result
        audit = audit_capture(payload, receipt, fixture, expected_identity=identity)
    except (ValueError, TypeError, KeyError, OverflowError):
        result["reason"] = "LATEST_PAYLOAD_INVALID"
        return result
    result["api_audit"] = audit
    if not audit["pair_api_state_admitted"]:
        result["reason"] = "LATEST_API_PAIR_REJECTED"
        return result
    quotes = [
        {
            "observed_at": received.isoformat(),
            "available_at": received.isoformat(),
            "received_at": received.isoformat(),
            "kickoff_at": kickoff.isoformat(),
            "snapshot_id": review["sha256"] + ":" + book,
            "source": "oddspapi_collector_response",
            "source_event_id": fixture,
            "event_id": fixture,
            "bookmaker": book,
            "market": "1x2",
            "period": "FT",
            "line": None,
            "status": "active",
            "odds": {side: leg["price"] for side, leg in audit["bookmakers"][book]["legs"].items()},
            "raw_payload_hash": review["sha256"],
            "snapshot_scope": "complete_market",
        }
        for book in _BOOKS
    ]
    result["conditional_scan"] = scan_quotes(quotes, as_of=cutoff, policy=policy)
    result["reason"] = "API_COMPARISON_ONLY_EXECUTION_EVIDENCE_MISSING"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditar capturas explícitas sem API, desfechos ou ordens")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--capture", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        contract, contract_hash = read_hashed(args.contract, jsonl=False)
        receipt, receipt_hash = read_hashed(args.receipt, jsonl=False)
        if not isinstance(contract, dict) or not isinstance(receipt, dict):
            raise ValueError("object_contracts_required")
        records = receipt.get("requests")
        if not isinstance(records, list):
            raise ValueError("request_receipt_list_required")
        inputs = {"contract": args.contract, "receipt": args.receipt}
        hashes = {"contract": contract_hash, "receipt": receipt_hash}
        captures: list[tuple[bytes | None, dict[str, Any]]] = []
        supplied = {path.name for path in args.capture}
        if len(supplied) != len(args.capture):
            raise ValueError("distinct_capture_files_required")
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("invalid_request_receipt")
            parameters = record.get("parameters")
            relevant = (
                record.get("endpoint") == "https://api.oddspapi.io/v4/odds"
                and isinstance(parameters, dict)
                and parameters.get("fixtureId") == contract["fixture_id"]
            )
            if relevant and record.get("file") not in supplied:
                if record.get("file") is not None or record.get("status") == "SAVED":
                    raise ValueError("all_saved_fixture_captures_required")
                # A failed attempt without a body still supersedes older offers.
                captures.append((None, record))
        for index, path in enumerate(args.capture):
            # Read/hash identical bytes; parsing failure must remain visible,
            # never be silently dropped in favor of an earlier valid response.
            from .artifacts import _input_path

            raw = _input_path(path).read_bytes()
            matches = [r for r in records if isinstance(r, dict) and r.get("file") == path.name]
            if len(matches) != 1:
                raise ValueError("unique_receipt_for_each_capture_required")
            key = f"capture_{index}"
            inputs[key], hashes[key] = path, hashlib.sha256(raw).hexdigest()
            captures.append((raw, matches[0]))
        result = decide_captures(captures, contract=contract)
        write_artifacts(
            args.output_dir,
            inputs=inputs,
            artifacts={"decision.json": result},
            metadata={
                "status": "RESEARCH_ONLY",
                "input_hashes_used": hashes,
                "profitability_established": False,
                "real_capital_enabled": False,
            },
        )
        print(json.dumps({"action": result["action"], "reason": result["reason"]}))
        return 0
    except (ValueError, TypeError, KeyError, OSError, OverflowError):
        print("Decisão recusada: entrada, contrato ou saída inválidos.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
