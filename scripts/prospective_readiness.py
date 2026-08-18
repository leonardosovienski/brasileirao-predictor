"""Fail-closed readiness report for prospective H9 collection."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from src.data.bookmaker_stability import stability_report
from src.settings import Settings

ROOT = Path(__file__).resolve().parent.parent


def report() -> dict:
    snapshots = ROOT / "data" / "research" / "market_observations.jsonl"
    stability_path = ROOT / "data" / "research" / "bookmaker_stability.jsonl"
    rows = []
    if snapshots.exists():
        for line in snapshots.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    runs: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.get("retrieved_at") and row.get("bookmaker"):
            runs[row["retrieved_at"]].add(row["bookmaker"])
    common = sorted(set.intersection(*runs.values())) if runs else []
    stability = stability_report(stability_path)
    settings = Settings()
    api_football = bool(os.getenv("API_FOOTBALL_KEY") or settings.API_FOOTBALL_KEY)
    odds_api = bool(os.getenv("ODDS_API_KEY") or settings.THE_ODDS_API_KEY)
    trials_path = ROOT / "data" / "trials.json"
    trials = json.loads(trials_path.read_text(encoding="utf-8")) if trials_path.exists() else []
    h9_registered = any(row.get("name") == "h9-ou25-prospective-replication" for row in trials)
    persistence_valid = stability["recommendation"] == "BOOKMAKER_RECOMMENDATION_READY"
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "api_football_configured": api_football,
        "odds_api_configured": odds_api,
        "collection_runs": len(runs),
        "bookmakers_present_in_every_run": common,
        "stability": stability,
        "bookmaker_persistence_gate": "PASS" if persistence_valid else "PENDING",
        "h9_registered": h9_registered,
        "api_football_required_for_h9": False,
        "h9_can_emit": odds_api and persistence_valid and h9_registered,
        "capital_enabled": False,
    }


def main() -> None:
    print(json.dumps(report(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
