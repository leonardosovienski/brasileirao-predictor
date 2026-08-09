"""Rebuild sanitized smoke summaries from append-only market observations."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from src.data.bitemporal_store import BitemporalObservation, append, connect
from src.data.bookmaker_stability import append_smoke, summarize_smoke

ROOT = Path(__file__).resolve().parent.parent
MARKETS = ROOT / "data" / "research" / "market_observations.jsonl"
STABILITY = ROOT / "data" / "research" / "bookmaker_stability.jsonl"
PIT = ROOT / "data" / "research" / "prospective.db"


def main() -> None:
    runs: dict[str, list[dict]] = defaultdict(list)
    for line in MARKETS.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("retrieved_at"):
            runs[row["retrieved_at"]].append(row)
    for rows in runs.values():
        append_smoke(STABILITY, summarize_smoke(rows))
    connection = connect(PIT)
    written = 0
    quarantined = 0
    try:
        for rows in runs.values():
            for row in rows:
                try:
                    observation = BitemporalObservation(
                        entity_type="odds_snapshot",
                        entity_id=(
                            f"{row['source_event_id']}|{row['bookmaker']}|{row['market']}|"
                            f"{row['selection']}|{row.get('line')}"
                        ),
                        source=row["source"],
                        event_at=datetime.fromisoformat(row["kickoff_at"]),
                        published_at=datetime.fromisoformat(row["odds_captured_at"]),
                        ingested_at=datetime.fromisoformat(row["retrieved_at"]),
                        payload=row,
                        charter_id="brasileirao-the-odds-api-v1",
                    )
                except ValueError:
                    quarantined += 1
                    continue
                written += append(connection, observation)
    finally:
        connection.close()
    print(
        json.dumps(
            {
                "runs": len(runs),
                "pit_rows_written": written,
                "causality_quarantined": quarantined,
                "ledger": str(STABILITY),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
