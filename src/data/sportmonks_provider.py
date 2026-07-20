"""Sportmonks secondary source, opt-in and read-only.

The adapter is restricted to coverage audits. It never feeds predictions,
shadow ledgers, settlement, or scientific gates.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
import os
from typing import Any, Callable
import urllib.request

from predictor_core.data.contracts import DataUnavailableError

BASE = "https://api.sportmonks.com/v3/football"


class SportmonksProvider:
    def __init__(self, *, token: str | None = None, timeout: float = 30.0,
                 get_json: Callable[[str, dict[str, str]], Any] | None = None):
        self.token = token or os.environ.get("SPORTMONKS_TOKEN")
        self.timeout = timeout
        self._get_json = get_json or self._http_get_json

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise DataUnavailableError("SPORTMONKS_TOKEN ausente")
        # Sportmonks aceita o token bruto no Authorization; Bearer retorna 401.
        return {"Authorization": self.token,
                "User-Agent": "brasileirao-predictor-source-audit/1.0"}

    def _http_get_json(self, url: str, headers: dict[str, str]) -> Any:
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except (OSError, ValueError) as exc:
            raise DataUnavailableError(f"Sportmonks indisponível: {exc}") from exc

    def accessible_leagues(self) -> list[dict[str, Any]]:
        payload = self._get_json(f"{BASE}/leagues?include=country&per_page=100",
                                 self._headers())
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise DataUnavailableError("Sportmonks retornou ligas inválidas")
        return [{"source_league_id": int(row["id"]), "name": row.get("name"),
                 "country": (row.get("country") or {}).get("name")}
                for row in rows if row.get("id") is not None]

    def require_league(self, name: str, country: str) -> int:
        matches = [row for row in self.accessible_leagues()
                   if row["name"] == name and row["country"] == country]
        if len(matches) != 1:
            raise DataUnavailableError(
                f"liga não coberta pelo plano Sportmonks: {name} ({country})")
        return matches[0]["source_league_id"]

    def list_fixtures(self, *, league_id: int, from_date: date, to_date: date,
                      observed_at: datetime | None = None) -> list[dict[str, Any]]:
        observed = observed_at or datetime.now(timezone.utc)
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("observed_at deve conter timezone")
        observed = observed.astimezone(timezone.utc)
        url = (f"{BASE}/fixtures/between/{from_date.isoformat()}/{to_date.isoformat()}"
               f"?filters=fixtureLeagues:{int(league_id)}&include=participants")
        payload = self._get_json(url, self._headers())
        raw_rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(raw_rows, list):
            raise DataUnavailableError("Sportmonks retornou fixtures inválidos")
        rows = []
        for fixture in raw_rows:
            participants = fixture.get("participants") or []
            home = next((p for p in participants
                         if (p.get("meta") or {}).get("location") == "home"), None)
            away = next((p for p in participants
                         if (p.get("meta") or {}).get("location") == "away"), None)
            try:
                scheduled = datetime.fromisoformat(
                    str(fixture["starting_at"]).replace("Z", "+00:00"))
                if scheduled.tzinfo is None or home is None or away is None:
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                continue
            rows.append({
                "source": "sportmonks", "source_event_id": str(fixture["id"]),
                "source_league_id": int(league_id),
                "scheduled_at": scheduled.astimezone(timezone.utc).isoformat(timespec="seconds"),
                "observed_at": observed.isoformat(timespec="seconds"),
                "home_team": home.get("name"), "away_team": away.get("name"),
                "state_id": fixture.get("state_id"), "shadow_only": True,
            })
        return sorted(rows, key=lambda row: (row["scheduled_at"], row["source_event_id"]))
