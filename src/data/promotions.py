"""Validated access metadata for promoted Serie A clubs."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Promotion:
    serie_a_season: int
    serie_b_season: int
    position: int
    team_id: str
    team_name: str
    source_url: str


@dataclass(frozen=True)
class Relegation:
    serie_a_season: int
    position: int
    team_id: str
    team_name: str
    source_url: str


def load_promotions(path: str | Path) -> list[Promotion]:
    payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "promotions-brasileirao/v1":
        raise ValueError("unsupported promotions schema_version")
    source_by_season = {int(item["serie_b_season"]): str(item["url"]) for item in payload.get("sources", [])}
    promotions: list[Promotion] = []
    seen: set[tuple[int, str]] = set()
    positions: dict[int, set[int]] = {}
    for raw in payload.get("entries", []):
        season_a = int(raw["serie_a_season"])
        season_b = int(raw["serie_b_season"])
        position = int(raw["position"])
        team_id = str(raw["team_id"]).strip()
        team_name = str(raw["team_name"]).strip()
        if season_a != season_b + 1 or not team_id or not team_name or position not in range(1, 5):
            raise ValueError(f"invalid promotion entry: {raw!r}")
        key = (season_a, team_id)
        if key in seen:
            raise ValueError(f"duplicate promotion entry: {key}")
        source_url = source_by_season.get(season_b, "")
        if not source_url.startswith("https://www.cbf.com.br/"):
            raise ValueError(f"missing official source for Serie B {season_b}")
        seen.add(key)
        positions.setdefault(season_a, set()).add(position)
        promotions.append(Promotion(season_a, season_b, position, team_id, team_name, source_url))
    if not promotions:
        raise ValueError("promotion dataset is empty")
    invalid_seasons = {season: values for season, values in positions.items() if values != {1, 2, 3, 4}}
    if invalid_seasons:
        raise ValueError(f"each Serie A season requires final Serie B positions 1-4: {invalid_seasons}")
    return sorted(promotions, key=lambda item: (item.serie_a_season, item.position))


def load_relegations(path: str | Path) -> list[Relegation]:
    payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    source_by_season = {int(item["serie_a_season"]): str(item["url"]) for item in payload["relegation_sources"]}
    entries: list[Relegation] = []
    positions: dict[int, set[int]] = {}
    for raw in payload.get("relegations", []):
        season = int(raw["serie_a_season"])
        position = int(raw["position"])
        source = source_by_season.get(season, "")
        if position not in range(17, 21) or not source.startswith("https://www.cbf.com.br/"):
            raise ValueError(f"invalid relegation entry: {raw!r}")
        positions.setdefault(season, set()).add(position)
        entries.append(Relegation(season, position, str(raw["team_id"]), str(raw["team_name"]), source))
    if not entries or any(values != {17, 18, 19, 20} for values in positions.values()):
        raise ValueError("each Serie A season requires relegation positions 17-20")
    return sorted(entries, key=lambda item: (item.serie_a_season, item.position))
