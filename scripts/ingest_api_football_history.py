"""Import API-Football 2022--2024 into the isolated shadow database."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.api_football_provider import ApiFootballProvider  # noqa: E402
from src.data.historical_expansion import (                       # noqa: E402
    API_FOOTBALL_TEAM_MAP, connect_shadow, coverage_report, ingest_api_football,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", nargs="+", type=int, default=[2022, 2023, 2024])
    parser.add_argument("--shadow-db", default=str(ROOT / "data" / "source_expansion.db"))
    parser.add_argument("--production-db", default=str(ROOT / "data" / "matches.db"))
    args = parser.parse_args()

    production = sqlite3.connect(args.production_db)
    known = {row[0] for row in production.execute("SELECT home_team FROM matches")} | \
            {row[0] for row in production.execute("SELECT away_team FROM matches")}
    # Clubes rebaixados podem não existir na janela atual do banco principal;
    # entram somente quando constam no mapa explícito e revisado acima.
    known |= set(API_FOOTBALL_TEAM_MAP.values())
    shadow = connect_shadow(args.shadow_db)
    provider = ApiFootballProvider()
    imported = 0
    for season in args.seasons:
        imported += ingest_api_football(
            shadow, provider.list_fixtures(season=season), known_teams=known)
    report = coverage_report(shadow, production)
    report["imported_this_run"] = imported
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
