import json
from pathlib import Path

from src.data.bookmaker_stability import append_smoke, stability_report


def _row(key, executed, coverage=10, seen=10, lag=10):
    return {"executed_at":executed, "bookmaker_key":key, "events_seen":seen, "events_with_totals":coverage, "valid_quotes":coverage * 2, "update_lag_seconds":lag}


def test_append_only_and_exchange_is_not_recommended(tmp_path: Path):
    ledger = tmp_path / "smokes.jsonl"
    append_smoke(ledger, [_row("matchbook", "2026-01-01T00:00:00+00:00")])
    append_smoke(ledger, [_row("matchbook", "2026-01-02T00:00:00+00:00")])
    assert len(ledger.read_text().splitlines()) == 2
    assert stability_report(ledger)["bookmakers"][0]["classification"] == "BOOKMAKER_REJECTED"


def test_stable_and_insufficient_coverage_are_deterministic(tmp_path: Path):
    ledger = tmp_path / "smokes.jsonl"
    rows = []
    for day in range(1, 4):
        stamp = f"2026-01-0{day}T00:00:00+00:00"; rows += [_row("pinnacle", stamp), _row("thinbook", stamp, coverage=1)]
    append_smoke(ledger, rows)
    states = {r["bookmaker_key"]:r["classification"] for r in stability_report(ledger)["bookmakers"]}
    assert states == {"pinnacle":"BOOKMAKER_STABLE", "thinbook":"BOOKMAKER_INSUFFICIENT_COVERAGE"}
