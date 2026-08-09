"""Collect market and lineup vintages for residual research; never emits picks."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from predictor_core.data.contracts import DataUnavailableError

from src.data.api_football_provider import ApiFootballProvider
from src.data.bitemporal_store import BitemporalObservation, append, connect
from src.data.bookmaker_stability import append_smoke, summarize_smoke
from src.data.lineup_archive import persist_lineups
from src.data.market_anchor import persist_market_observations
from src.data.the_odds_api_provider import TheOddsApiProvider

ROOT = Path(__file__).resolve().parent.parent
MARKETS = ROOT / "data" / "research" / "market_observations.jsonl"
LINEUPS = ROOT / "data" / "research" / "lineup_observations.jsonl"
STABILITY = ROOT / "data" / "research" / "bookmaker_stability.jsonl"
PIT = ROOT / "data" / "research" / "prospective.db"


def collect(*, first_half: bool, lineup_fixtures: list[str]) -> dict[str, int]:
    odds = TheOddsApiProvider()
    featured = odds.fetch_markets()
    market_rows = list(featured)
    if first_half:
        for event_id in sorted({row["source_event_id"] for row in featured}):
            market_rows.extend(odds.fetch_event_markets(event_id))
    markets_written = persist_market_observations(MARKETS, market_rows)
    if featured:
        append_smoke(STABILITY, summarize_smoke(featured))
        connection = connect(PIT)
        try:
            for row in featured:
                append(
                    connection,
                    BitemporalObservation(
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
                    ),
                )
        finally:
            connection.close()

    lineup_rows = []
    if lineup_fixtures:
        lineups = ApiFootballProvider()
        for fixture_id in lineup_fixtures:
            lineup_rows.extend(lineups.fixture_lineups(fixture_id))
    lineups_written = persist_lineups(LINEUPS, lineup_rows)
    return {"market_rows": markets_written, "lineup_rows": lineups_written}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--first-half",
        action="store_true",
        help="also query event-scoped totals_h1 markets (uses additional API credits)",
    )
    parser.add_argument(
        "--lineup-fixture",
        action="append",
        default=[],
        help="API-Football fixture id; repeat for multiple fixtures",
    )
    args = parser.parse_args()
    try:
        result = collect(first_half=args.first_half, lineup_fixtures=args.lineup_fixture)
    except DataUnavailableError as exc:
        parser.error(str(exc))
    print(f"COLLECTION_ONLY: {result['market_rows']} market rows; {result['lineup_rows']} lineup rows")


if __name__ == "__main__":
    main()
