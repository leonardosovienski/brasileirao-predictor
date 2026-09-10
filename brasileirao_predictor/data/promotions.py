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


def _integer(value: Any, field: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{field} must be an integer")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value.strip()


def _load_payload(path: str | Path) -> dict[str, Any]:
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate metadata key")
            value[key] = item
        return value

    payload = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(payload, dict) or payload.get("schema_version") != "promotions-brasileirao/v1":
        raise ValueError("unsupported promotions schema_version")
    return payload


def _sources(payload: dict[str, Any], collection: str, season_field: str) -> dict[int, str]:
    sources = payload.get(collection, [])
    if not isinstance(sources, list):
        raise ValueError("sources must be a list")
    by_season = {}
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("source must be an object")
        season = _integer(source.get(season_field), season_field)
        url = _text(source.get("url"), "url")
        if season in by_season:
            raise ValueError("duplicate source season")
        if not url.startswith("https://www.cbf.com.br/"):
            raise ValueError("official source URL required; URL presence is not source authentication")
        by_season[season] = url
    return by_season


def load_promotions(path: str | Path) -> list[Promotion]:
    payload = _load_payload(path)
    source_by_season = _sources(payload, "sources", "serie_b_season")
    promotions: list[Promotion] = []
    seen: set[tuple[int, str]] = set()
    positions: dict[int, set[int]] = {}
    for raw in payload.get("entries", []):
        if not isinstance(raw, dict):
            raise ValueError("promotion entry must be an object")
        season_a = _integer(raw.get("serie_a_season"), "serie_a_season")
        season_b = _integer(raw.get("serie_b_season"), "serie_b_season")
        position = _integer(raw.get("position"), "position")
        team_id = _text(raw.get("team_id"), "team_id")
        team_name = _text(raw.get("team_name"), "team_name")
        if season_a != season_b + 1 or not team_id or not team_name or position not in range(1, 5):
            raise ValueError(f"invalid promotion entry: {raw!r}")
        key = (season_a, team_id)
        if key in seen:
            raise ValueError(f"duplicate promotion entry: {key}")
        if position in positions.get(season_a, set()):
            raise ValueError("duplicate promotion position")
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
    payload = _load_payload(path)
    source_by_season = _sources(payload, "relegation_sources", "serie_a_season")
    entries: list[Relegation] = []
    positions: dict[int, set[int]] = {}
    seen: set[tuple[int, str]] = set()
    for raw in payload.get("relegations", []):
        if not isinstance(raw, dict):
            raise ValueError("relegation entry must be an object")
        season = _integer(raw.get("serie_a_season"), "serie_a_season")
        position = _integer(raw.get("position"), "position")
        team_id = _text(raw.get("team_id"), "team_id")
        team_name = _text(raw.get("team_name"), "team_name")
        if (season, team_id) in seen or position in positions.get(season, set()):
            raise ValueError("duplicate relegation team or position")
        source = source_by_season.get(season, "")
        if position not in range(17, 21) or not source.startswith("https://www.cbf.com.br/"):
            raise ValueError(f"invalid relegation entry: {raw!r}")
        positions.setdefault(season, set()).add(position)
        seen.add((season, team_id))
        entries.append(Relegation(season, position, team_id, team_name, source))
    if not entries or any(values != {17, 18, 19, 20} for values in positions.values()):
        raise ValueError("each Serie A season requires relegation positions 17-20")
    return sorted(entries, key=lambda item: (item.serie_a_season, item.position))
