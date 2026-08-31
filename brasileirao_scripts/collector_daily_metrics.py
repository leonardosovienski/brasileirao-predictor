"""Calcula métricas diárias do ensaio econômico A1."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from brasileirao_predictor.collector_a1 import TeamAliases, compute_daily_metrics, event_id

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    today = datetime.now(UTC).date().isoformat()
    heartbeat = ROOT / "data" / "collector_state" / "metrics_heartbeat.json"
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    heartbeat.write_text(
        json.dumps({"checked_at": datetime.now(UTC).isoformat(), "date": today, "capital_enabled": False}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    snapshot_path = ROOT / "data" / "odds_snapshots" / f"{today}.jsonl"
    fixtures_path = ROOT / "data" / "collector_state" / "fixtures.json"
    snapshots = (
        [json.loads(line) for line in snapshot_path.read_text(encoding="utf-8").splitlines()]
        if snapshot_path.exists()
        else []
    )
    if not snapshots:
        print(json.dumps({"status": "NOT_STARTED_NO_SNAPSHOTS", "date": today, "capital_enabled": False}))
        return 0
    aliases = TeamAliases(ROOT / "data" / "team_aliases.json")
    expected: set[str] = set()
    if fixtures_path.exists():
        for fixture in json.loads(fixtures_path.read_text(encoding="utf-8"))["fixtures"]:
            home = aliases.resolve(str(fixture.get("participant1Name", ""))).canonical
            away = aliases.resolve(str(fixture.get("participant2Name", ""))).canonical
            if home and away:
                expected.add(event_id(home, away, str(fixture["startTime"])))
    log_path = ROOT / "data" / "collector_metrics" / "collector_daily_log.jsonl"
    latest_mode = "economic"
    if log_path.exists() and log_path.stat().st_size:
        last_log = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
        latest_mode = "full" if last_log.get("mode") == "full" else "economic"
    metrics = compute_daily_metrics(snapshots, expected, mode=latest_mode)
    output = ROOT / "data" / "collector_metrics" / f"{today}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
