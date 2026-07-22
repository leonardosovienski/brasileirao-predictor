"""The Odds API adapter: explicit bookmaker provenance for prospective odds."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from typing import Any, Callable
from urllib.parse import urlencode
import urllib.request

from predictor_core.data.contracts import DataUnavailableError

BASE = "https://api.the-odds-api.com/v4"
SOURCE = "the_odds_api"
ADAPTER_VERSION = "the-odds-api/1"
SPORT = "soccer_brazil_campeonato"


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str): return None
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


class TheOddsApiProvider:
    def __init__(self, *, api_key: str | None = None, regions: str = "eu", timeout: float = 30.0, get_json: Callable[[str], Any] | None = None):
        self.api_key, self.regions, self.timeout = api_key or os.environ.get("ODDS_API_KEY"), regions, timeout
        self._get_json = get_json or self._http_get_json

    def _http_get_json(self, url: str) -> Any:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "brasileirao-predictor/1.0"}), timeout=self.timeout) as response:
                return json.loads(response.read())
        except (OSError, ValueError) as exc:
            raise DataUnavailableError(f"The Odds API indisponível: {exc}") from exc

    def fetch_ou25(self, *, retrieved_at: datetime | None = None) -> list[dict[str, Any]]:
        if not self.api_key: raise DataUnavailableError("ODDS_API_KEY ausente")
        now = retrieved_at or datetime.now(timezone.utc)
        if now.tzinfo is None: raise ValueError("retrieved_at deve conter timezone")
        query = urlencode({"apiKey": self.api_key, "regions": self.regions, "markets": "totals", "oddsFormat": "decimal"})
        payload = self._get_json(f"{BASE}/sports/{SPORT}/odds?{query}")
        if not isinstance(payload, list): raise DataUnavailableError("The Odds API retornou payload inválido")
        raw_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        rows: list[dict[str, Any]] = []
        for event in payload:
            kickoff = _utc(event.get("commence_time"))
            event_id = event.get("id")
            if not kickoff or not isinstance(event_id, str): continue
            for book in event.get("bookmakers", []):
                bookmaker, captured = book.get("key"), _utc(book.get("last_update"))
                if not isinstance(bookmaker, str) or not bookmaker or not captured or captured >= kickoff: continue
                for market in book.get("markets", []):
                    if market.get("key") != "totals": continue
                    for outcome in market.get("outcomes", []):
                        if outcome.get("point") != 2.5 or outcome.get("name") not in ("Over", "Under"): continue
                        price = outcome.get("price")
                        if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 1: continue
                        rows.append({"source": SOURCE, "source_event_id": event_id, "bookmaker": bookmaker, "market": "ou2.5", "selection": outcome["name"].lower(), "decimal_odds": float(price), "odds_captured_at": captured.isoformat(timespec="seconds"), "retrieved_at": now.astimezone(timezone.utc).isoformat(timespec="seconds"), "canonical_match_id": f"{SOURCE}:{event_id}", "raw_payload_hash": raw_hash, "adapter_version": ADAPTER_VERSION, "data_quality_status": "PROSPECTIVE_ELIGIBLE", "kickoff_at": kickoff.isoformat(timespec="seconds"), "home_team": event.get("home_team"), "away_team": event.get("away_team")})
        return rows
