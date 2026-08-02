"""API-Football secondary source for controlled historical expansion.

The free plan currently exposes seasons 2022--2024.  This adapter is opt-in,
read-only, and marks every record as shadow-only; callers must not mix its
output into production predictions or settlement without a separate gate.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from predictor_core.data.contracts import DataUnavailableError

BASE = "https://v3.football.api-sports.io"
BRASILEIRAO_SERIE_A_ID = 71
FREE_SEASONS = frozenset({2022, 2023, 2024})


class ApiFootballProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        get_json: Callable[[str, dict[str, str]], Any] | None = None,
    ):
        self.api_key = api_key or os.environ.get("API_FOOTBALL_KEY")
        self.timeout = timeout
        self._get_json = get_json or self._http_get_json

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise DataUnavailableError("API_FOOTBALL_KEY ausente")
        return {
            "x-apisports-key": self.api_key,
            "User-Agent": "brasileirao-predictor-source-audit/1.0",
        }

    def _http_get_json(self, url: str, headers: dict[str, str]) -> Any:
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except (OSError, ValueError) as exc:
            raise DataUnavailableError(f"API-Football indisponível: {exc}") from exc

    def _request(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = f"{BASE}/{path}?{urlencode(params)}"
        payload = self._get_json(url, self._headers())
        if not isinstance(payload, dict):
            raise DataUnavailableError("API-Football retornou payload inválido")
        errors = payload.get("errors")
        if errors:
            detail = (
                "; ".join(f"{key}: {value}" for key, value in errors.items())
                if isinstance(errors, dict)
                else str(errors)
            )
            raise DataUnavailableError(f"API-Football recusou a consulta: {detail}")
        rows = payload.get("response")
        if not isinstance(rows, list):
            raise DataUnavailableError("API-Football retornou resposta inválida")
        return rows

    def brasileirao_seasons(self) -> list[int]:
        rows = self._request("leagues", {"id": BRASILEIRAO_SERIE_A_ID})
        if (
            len(rows) != 1
            or rows[0].get("league", {}).get("name") != "Serie A"
            or rows[0].get("country", {}).get("name") != "Brazil"
        ):
            raise DataUnavailableError("API-Football não confirmou o Brasileirão Série A")
        return sorted(int(item["year"]) for item in rows[0].get("seasons", []) if item.get("year") is not None)

    def list_fixtures(self, *, season: int, observed_at: datetime | None = None) -> list[dict[str, Any]]:
        if season not in FREE_SEASONS:
            raise DataUnavailableError(f"temporada {season} fora da janela grátis da API-Football (2022-2024)")
        observed = observed_at or datetime.now(UTC)
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("observed_at deve conter timezone")
        observed = observed.astimezone(UTC)
        raw_rows = self._request(
            "fixtures",
            {
                "league": BRASILEIRAO_SERIE_A_ID,
                "season": season,
            },
        )
        rows = []
        for item in raw_rows:
            fixture = item.get("fixture") or {}
            teams = item.get("teams") or {}
            home = teams.get("home") or {}
            away = teams.get("away") or {}
            try:
                scheduled = datetime.fromisoformat(str(fixture["date"]).replace("Z", "+00:00"))
                event_id = str(fixture["id"])
                if scheduled.tzinfo is None or not home.get("name") or not away.get("name"):
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                continue
            goals = item.get("goals") or {}
            rows.append(
                {
                    "source": "api_football",
                    "source_event_id": event_id,
                    "source_league_id": BRASILEIRAO_SERIE_A_ID,
                    "season": season,
                    "scheduled_at": scheduled.astimezone(UTC).isoformat(timespec="seconds"),
                    "observed_at": observed.isoformat(timespec="seconds"),
                    "home_team": home["name"],
                    "away_team": away["name"],
                    "home_goals": goals.get("home"),
                    "away_goals": goals.get("away"),
                    "status": (fixture.get("status") or {}).get("short"),
                    "shadow_only": True,
                }
            )
        return sorted(rows, key=lambda row: (row["scheduled_at"], row["source_event_id"]))
