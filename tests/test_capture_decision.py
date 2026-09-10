"""Synthetic adversarial evidence for the isolated receipt decision adapter."""

import hashlib
import json
from copy import deepcopy

import pytest
from test_live_capture_admission import payload

from brasileirao_predictor.research.price_strength.capture_decision import decide_captures, main


def contract():
    return {
        "schema_version": "api-capture-decision/1",
        "fixture_id": "id1",
        "identity": {"participant1Id": 1, "participant2Id": 2, "sportId": 10, "tournamentId": 325, "seasonId": 77},
        "kickoff_at": "2026-09-12T00:00:00Z",
        "decision_at": "2026-09-09T20:00:02Z",
        "initial_bankroll_units": 100,
        "policy": {
            "reference_books": ["pinnacle"],
            "max_age_seconds": 120,
            "max_skew_seconds": 15,
            "cost_per_unit": 0.02,
            "commission_on_profit": 0.0,
        },
    }


def capture(*, obj=None, at="2026-09-09T20:00:01Z", raw=None):
    if obj is None:
        obj = payload()
        obj.update(contract()["identity"])
        for outcome in obj["bookmakerOdds"]["pinnacle"]["markets"]["101"]["outcomes"].values():
            outcome["players"]["0"]["price"] = 2.7
        obj["bookmakerOdds"]["bet365.bet.br"]["markets"]["101"]["outcomes"]["101"]["players"]["0"]["price"] = 3.3
    raw = raw if raw is not None else json.dumps(obj).encode("utf-8")
    receipt = {
        "endpoint": "https://api.oddspapi.io/v4/odds",
        "status": "SAVED",
        "http_status": 200,
        "requested_at": at,
        "received_at": at,
        "parameters": {"fixtureId": "id1", "bookmakers": "pinnacle,bet365.bet.br", "oddsFormat": "decimal"},
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "file": "capture.json",
    }
    return raw, receipt


def run(rows=None, cfg=None):
    return decide_captures(rows if rows is not None else [capture()], contract=cfg or contract())


def test_positive_conditional_price_is_never_promoted_to_an_execution_or_profit():
    result = run()
    selected = result["conditional_scan"]["selected_candidates"]
    assert len(selected) == 1 and selected[0]["net_ev"] == pytest.approx(0.08)
    assert selected[0]["bookmaker"] == "bet365.bet.br"
    assert selected[0]["reference_books_used"] == ["pinnacle"]
    assert result["action"] == "ABSTAIN" and not result["execution_admitted"]
    assert result["portfolio"]["stakes_units"] == 0 and result["portfolio"]["bets"] == 0
    assert result["portfolio"]["roi_on_stakes"] is None
    assert result["portfolio"]["total_net_pnl_units"] is None  # Fixed costs remain unknown.
    assert not result["profitability_established"] and not result["labels_accessed"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("http_status", 503),
        ("http_status", True),
        ("status", "FAILED"),
        ("sha256", "0" * 64),
        ("bytes", 1),
        ("bytes", True),
        ("endpoint", "https://example.invalid/odds"),
        ("parameters", {"fixtureId": "foreign"}),
    ],
)
def test_latest_bad_transport_cannot_resurrect_an_older_good_capture(field, value):
    bad = capture(at="2026-09-09T20:00:02Z")
    bad[1][field] = value
    result = run([capture(), bad])
    assert result["reason"] == "LATEST_TRANSPORT_OR_INTEGRITY_REJECTED"
    assert result["conditional_scan"] is None


@pytest.mark.parametrize("raw", [b'{"hasOdds":false,"hasOdds":true}', b'{"p":NaN}', b'{"p":1e9999}', b"[]", b"broken"])
def test_bad_latest_payload_is_retained_as_abstention(raw):
    assert run([capture(), capture(raw=raw, at="2026-09-09T20:00:02Z")])["conditional_scan"] is None


def test_later_inactive_parent_blocks_earlier_active_children():
    original, _ = capture()
    obj = json.loads(original)
    obj["bookmakerOdds"]["bet365.bet.br"]["bookmakerIsActive"] = False
    result = run([capture(), capture(obj=obj, at="2026-09-09T20:00:02Z")])
    assert result["reason"] == "LATEST_API_PAIR_REJECTED"
    assert not result["api_audit"]["pair_api_state_admitted"]


@pytest.mark.parametrize("mutation", ["kickoff", "home", "competition"])
def test_frozen_identity_and_kickoff_are_required_even_with_matching_hash(mutation):
    raw, _ = capture()
    obj = json.loads(raw)
    key, value = {
        "kickoff": ("startTime", "2026-09-13T00:00:00Z"),
        "home": ("participant1Id", 2),
        "competition": ("tournamentId", 999),
    }[mutation]
    obj[key] = value
    result = run([capture(obj=obj)])
    assert result["conditional_scan"] is None and result["action"] == "ABSTAIN"


def test_future_capture_is_excluded_before_parsing_and_cannot_invalidate_known_past():
    result = run([capture(), capture(raw=b"not-yet-available", at="2026-09-09T20:00:03Z")])
    assert result["conditional_scan"] is not None
    assert result["capture_reviews"][1]["reason"] == "not_received_by_cutoff"


def test_unorderable_receipt_blocks_the_batch_instead_of_cherry_picking():
    bad = capture()
    bad[1]["received_at"] = "unknown"
    assert run([capture(), bad])["reason"] == "AMBIGUOUS_RECEIPT_CLOCK_NO_FALLBACK"


def test_equal_timestamps_do_not_choose_a_canonical_revision_by_hash_or_file_order():
    good, bad = capture(), capture()
    bad[1]["http_status"] = 503
    assert run([good, bad])["reason"] == "AMBIGUOUS_LATEST_CAPTURE_NO_FALLBACK"
    assert run([bad, good])["reason"] == "AMBIGUOUS_LATEST_CAPTURE_NO_FALLBACK"


def test_no_capture_and_stale_capture_have_explicit_denominators():
    assert run([])["reason"] == "NO_CAPTURE_RECEIVED_BY_CUTOFF"
    cfg = contract()
    cfg["decision_at"] = "2026-09-09T20:03:00Z"
    result = run(cfg=cfg)
    assert result["reason"] == "LATEST_API_RESPONSE_STALE"
    assert result["portfolio"]["abstentions"] == 1


@pytest.mark.parametrize(
    "mutation", ["cost_missing", "cost_nan", "unknown_field", "bool_bank", "after_kickoff", "same_team"]
)
def test_invalid_or_incomplete_assumptions_are_not_replaced_by_defaults(mutation):
    cfg = contract()
    if mutation == "cost_missing":
        del cfg["policy"]["cost_per_unit"]
    elif mutation == "cost_nan":
        cfg["policy"]["cost_per_unit"] = float("nan")
    elif mutation == "unknown_field":
        cfg["allow_execution"] = True
    elif mutation == "bool_bank":
        cfg["initial_bankroll_units"] = True
    elif mutation == "same_team":
        cfg["identity"]["participant2Id"] = 1
    else:
        cfg["decision_at"] = cfg["kickoff_at"]
    with pytest.raises((TypeError, ValueError)):
        run(cfg=cfg)


def test_inputs_are_not_mutated():
    rows, cfg = [capture()], contract()
    before = deepcopy((rows, cfg))
    run(rows, cfg)
    assert (rows, cfg) == before


def test_cli_hashes_inputs_emits_abstention_and_refuses_overwrite(tmp_path):
    raw, receipt = capture()
    c, r, p, out = [tmp_path / name for name in ("contract.json", "receipt.json", "capture.json", "run")]
    c.write_text(json.dumps(contract()), encoding="utf-8")
    r.write_text(json.dumps({"requests": [receipt]}), encoding="utf-8")
    p.write_bytes(raw)
    args = ["--contract", str(c), "--receipt", str(r), "--capture", str(p), "--output-dir", str(out)]
    assert main(args) == 0
    manifest = (out / "manifest.json").read_bytes()
    assert json.loads((out / "decision.json").read_text(encoding="utf-8"))["action"] == "ABSTAIN"
    assert main(args) == 2
    assert (out / "manifest.json").read_bytes() == manifest


def test_cli_preserves_later_failed_attempt_without_a_payload_file(tmp_path):
    raw, receipt = capture()
    failed = {**receipt, "status": "FAILED", "http_status": 503, "received_at": "2026-09-09T20:00:02Z"}
    for key in ("file", "sha256", "bytes"):
        del failed[key]
    c, r, p, out = [tmp_path / name for name in ("contract.json", "receipt.json", "capture.json", "run")]
    c.write_text(json.dumps(contract()), encoding="utf-8")
    r.write_text(json.dumps({"requests": [receipt, failed]}), encoding="utf-8")
    p.write_bytes(raw)
    assert main(["--contract", str(c), "--receipt", str(r), "--capture", str(p), "--output-dir", str(out)]) == 0
    result = json.loads((out / "decision.json").read_text(encoding="utf-8"))
    assert result["reason"] == "LATEST_TRANSPORT_OR_INTEGRITY_REJECTED"
    assert result["conditional_scan"] is None


def test_cli_refuses_an_incomplete_saved_capture_universe(tmp_path):
    raw, receipt = capture()
    c, r, p, out = [tmp_path / name for name in ("contract.json", "receipt.json", "capture.json", "run")]
    c.write_text(json.dumps(contract()), encoding="utf-8")
    missing = {**receipt, "file": "another_saved_capture.json", "received_at": "2026-09-09T20:00:02Z"}
    r.write_text(json.dumps({"requests": [receipt, missing]}), encoding="utf-8")
    p.write_bytes(raw)
    assert main(["--contract", str(c), "--receipt", str(r), "--capture", str(p), "--output-dir", str(out)]) == 2
    assert not out.exists()
