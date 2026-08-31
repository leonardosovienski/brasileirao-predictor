"""Import retrospective OU2.5 aggregates into an isolated research database.

This never writes ``matches.db``.  The Kaggle/OddsPortal data is retrospective
and may be used for exploratory replay, but never as prospective A1 evidence or
as named-bookmaker executable/CLV data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_URL = "https://www.kaggle.com/datasets/felipebandeiraramos/brazilian-soccer-odds-data"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    for suffix in (" futebol clube", " football club", " fc", " rj"):
        text = text.replace(suffix, "")
    compact = re.sub(r"[^a-z0-9]", "", text)
    aliases = {
        "americamg": "americamg",
        "americamineiro": "americamg",
        "amricamineiro": "americamg",
        "atleticomg": "atleticomg",
        "atleticomineiro": "atleticomg",
        "atlticomineiro": "atleticomg",
        "atleticogo": "atleticogo",
        "atleticogoianiense": "atleticogo",
        "atlticogoianiense": "atleticogo",
        "athletico": "athleticopr",
        "athleticopr": "athleticopr",
        "avai": "avai",
        "ava": "avai",
        "botafogorj": "botafogo",
        "bragantino": "bragantino",
        "redbullbragantino": "bragantino",
        "cear": "ceara",
        "chapecoensesc": "chapecoense",
        "cuiab": "cuiaba",
        "flamengorj": "flamengo",
        "gois": "goias",
        "grmio": "gremio",
        "saopaulo": "saopaulo",
        "sopaulo": "saopaulo",
        "vascodagama": "vasco",
    }
    return aliases.get(compact, compact)


def load_matches(path: Path) -> dict[tuple[str, str], list[tuple[date, int]]]:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            "SELECT event_id,date,home_team,away_team FROM matches "
            "WHERE substr(date,1,4) BETWEEN '2021' AND '2023' AND home_score IS NOT NULL"
        ).fetchall()
    matches: dict[tuple[str, str], list[tuple[date, int]]] = {}
    for event_id, day, home, away in rows:
        matches.setdefault((canonical(home), canonical(away)), []).append((date.fromisoformat(day), event_id))
    return matches


def import_backfill(source: Path, operational_db: Path, output: Path) -> dict:
    matches = load_matches(operational_db)
    output.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(output)
    conn.executescript(
        """
        DROP TABLE IF EXISTS ou25_historical_backfill;
        DROP TABLE IF EXISTS unmatched_rows;
        CREATE TABLE ou25_historical_backfill (
          event_id INTEGER PRIMARY KEY,
          source_match_date TEXT NOT NULL,
          operational_match_date TEXT NOT NULL,
          date_delta_days INTEGER NOT NULL CHECK (date_delta_days BETWEEN 0 AND 1),
          home_team_source TEXT NOT NULL, away_team_source TEXT NOT NULL,
          avg_over REAL NOT NULL, avg_under REAL NOT NULL,
          high_over REAL, high_under REAL, bookmaker_count INTEGER,
          price_semantics TEXT NOT NULL, source_url TEXT NOT NULL,
          source_sha256 TEXT NOT NULL, imported_at TEXT NOT NULL,
          contaminated INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE unmatched_rows (
          season TEXT, source_match_date TEXT, home_team_source TEXT,
          away_team_source TEXT, reason TEXT
        );
        """
    )
    source_hash = sha256(source)
    imported_at = datetime.now(UTC).isoformat()
    imported = missing_price = unmatched = 0
    by_season: dict[str, int] = {}
    with source.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            season = str(row["Season"])
            if season not in {"2021", "2022", "2023"}:
                continue
            day, month, year = row["Date"].split("/")
            match_date = f"{year}-{month}-{day}"
            source_day = date.fromisoformat(match_date)
            candidates = matches.get((canonical(row["Home"]), canonical(row["Away"])), [])
            near = [
                (abs((operational_day - source_day).days), operational_day, event_id)
                for operational_day, event_id in candidates
            ]
            near = [candidate for candidate in near if candidate[0] <= 1]
            selected_match = min(near) if len(near) == 1 else None
            event_id = selected_match[2] if selected_match else None
            if event_id is None:
                unmatched += 1
                conn.execute(
                    "INSERT INTO unmatched_rows VALUES (?,?,?,?,?)",
                    (season, match_date, row["Home"], row["Away"], "no_unique_team_match_within_one_day"),
                )
                continue
            try:
                avg_over, avg_under = float(row["AvgOver2.5"]), float(row["AvgUnder2.5"])
            except (TypeError, ValueError):
                missing_price += 1
                continue
            high_over = float(row["HighOver2.5"]) if row["HighOver2.5"] else None
            high_under = float(row["HighUnder2.5"]) if row["HighUnder2.5"] else None
            count = int(float(row["NumBookmakers2.5"])) if row["NumBookmakers2.5"] else None
            conn.execute(
                "INSERT INTO ou25_historical_backfill VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    match_date,
                    selected_match[1].isoformat(),
                    selected_match[0],
                    row["Home"],
                    row["Away"],
                    avg_over,
                    avg_under,
                    high_over,
                    high_under,
                    count,
                    "retrospective_oddsportal_aggregate_unknown_capture_time",
                    SOURCE_URL,
                    source_hash,
                    imported_at,
                    0,
                ),
            )
            imported += 1
            by_season[season] = by_season.get(season, 0) + 1
    conn.commit()
    conn.close()
    report = {
        "schema_version": "ou25-historical-backfill/2",
        "source_url": SOURCE_URL,
        "source_sha256": source_hash,
        "output_sha256": sha256(output),
        "price_semantics": "retrospective aggregate; capture time and named bookmaker unavailable",
        "allowed_use": "exploratory replay only",
        "prospective_a1_eligible": False,
        "clv_eligible": False,
        "capital_enabled": False,
        "imported": imported,
        "by_season": by_season,
        "unmatched": unmatched,
        "missing_price": missing_price,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "matches.db")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "research" / "ou25_backfill.sqlite")
    parser.add_argument("--report", type=Path, default=ROOT / "data" / "research" / "ou25_backfill_manifest.json")
    args = parser.parse_args()
    report = import_backfill(args.source, args.database, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
