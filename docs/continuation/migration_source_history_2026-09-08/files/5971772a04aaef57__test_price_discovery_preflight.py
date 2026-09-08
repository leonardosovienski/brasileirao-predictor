from __future__ import annotations

import builtins
import io
import json
import sqlite3
from pathlib import Path

import pytest
import requests

from brasileirao_scripts import price_discovery_preflight as preflight


def test_economic_t10_can_be_missed_with_ideal_15_minute_ticks() -> None:
    missing = []
    for phase in range(15):
        rows = preflight.simulate_schedule("economic", phase)
        labels = {row["label"] for row in rows}
        assert {"T-1440m", "T-360m", "T-60m"} <= labels
        if "T-10m" not in labels:
            missing.append(phase)
        else:
            t10 = next(row for row in rows if row["label"] == "T-10m")
            assert 0 < t10["minutes_before_kickoff"] <= 10
        assert all(row["minutes_before_kickoff"] > 0 for row in rows)
    assert missing == [0, 1, 2, 3, 4]


def test_full_mode_deduplicates_hourly_despite_15_minute_ticks() -> None:
    for phase in range(15):
        rows = preflight.simulate_schedule("full", phase)
        assert len(rows) == len({row["label"] for row in rows})
        offsets = [row["minutes_before_kickoff"] for row in rows]
        # Ignore the initial partial hour; all subsequent captures are hourly.
        assert {left - right for left, right in zip(offsets[1:], offsets[2:], strict=False)} == {60}
        assert all(row["label"].startswith("F-") for row in rows)


def test_preflight_reads_only_versioned_contracts_and_never_uses_io_services(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real_read_text = Path.read_text
    real_open = io.open
    reads: list[Path] = []

    def guarded_open(file: object, mode: str = "r", *args: object, **kwargs: object) -> object:
        assert Path(file) in {preflight.SCHEMA, preflight.POLICY}
        assert mode in {"r", "rb"}
        return real_open(file, mode, *args, **kwargs)

    def guarded_read(path: Path, *args: object, **kwargs: object) -> str:
        assert path in {preflight.SCHEMA, preflight.POLICY}
        reads.append(path)
        return real_read_text(path, *args, **kwargs)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("preflight must not access runtime, network, databases or write files")

    monkeypatch.setattr(Path, "read_text", guarded_read)
    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(io, "open", guarded_open)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    assert preflight.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert reads == [preflight.SCHEMA, preflight.POLICY]
    assert report["status"] == "SYNTHETIC_PREFLIGHT_ONLY"
    assert report["observed_provider_coverage"] is None
    assert report["real_cohort_read"] is report["capital_enabled"] is False
    assert report["simulation"]["phases_missing_t10"] == [0, 1, 2, 3, 4]
    support = report["declared_support"]
    assert set(support["time_fields"]) == {"captured_at", "kickoff_at"}
    assert {"source_price_updated_at", "response_received_at", "available_stake"} <= set(
        support["execution_fields_absent"]
    )
    assert "closing_odds" in support["forbidden_labels"]
    assert all(row["full_max_captures_per_utc_hour"] == 1 for row in report["simulation"]["phases"])
