from pathlib import Path

from src.data.bookmaker_stability import append_smoke, stability_report, summarize_smoke


def _row(key, executed, coverage=10, seen=10, lag=10):
    return {
        "executed_at": executed,
        "bookmaker_key": key,
        "events_seen": seen,
        "events_with_totals": coverage,
        "valid_quotes": coverage * 2,
        "update_lag_seconds": lag,
    }


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
        stamp = f"2026-01-0{day}T00:00:00+00:00"
        rows += [_row("pinnacle", stamp), _row("thinbook", stamp, coverage=1)]
    append_smoke(ledger, rows)
    states = {r["bookmaker_key"]: r["classification"] for r in stability_report(ledger)["bookmakers"]}
    assert states == {"pinnacle": "BOOKMAKER_STABLE", "thinbook": "BOOKMAKER_INSUFFICIENT_COVERAGE"}
    assert stability_report(ledger)["recommended_bookmaker"] == "pinnacle"


def test_smoke_uses_retrieval_time_not_bookmaker_update_time():
    rows = [
        {
            "retrieved_at": "2026-01-01T01:00:00+00:00",
            "odds_captured_at": f"2026-01-01T00:0{minute}:00+00:00",
            "bookmaker": "pinnacle",
            "source_event_id": str(minute),
            "market": "ou2.5",
        }
        for minute in range(2)
    ]
    smoke = summarize_smoke(rows)
    assert len(smoke) == 1
    assert smoke[0]["executed_at"] == "2026-01-01T01:00:00+00:00"
    assert smoke[0]["events_with_totals"] == 2


def test_three_smokes_inside_24_hours_remain_pending(tmp_path: Path):
    ledger = tmp_path / "smokes.jsonl"
    append_smoke(
        ledger,
        [_row("pinnacle", f"2026-01-01T0{hour}:00:00+00:00") for hour in range(3)],
    )
    report = stability_report(ledger)
    assert report["smokes"] == 3
    assert report["recommendation"] == "BOOKMAKER_STABILITY_PENDING"
