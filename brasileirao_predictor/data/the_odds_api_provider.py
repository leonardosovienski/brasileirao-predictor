"""The Odds API adapter: explicit bookmaker provenance for prospective odds."""

from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from predictor_core.data.contracts import DataUnavailableError

BASE = "https://api.the-odds-api.com/v4"
SOURCE = "the_odds_api"
ADAPTER_VERSION = "the-odds-api/1"
SPORT = "soccer_brazil_campeonato"


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else None


class TheOddsApiProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        regions: str = "eu",
        timeout: float = 30.0,
        get_json: Callable[[str], Any] | None = None,
    ):
        self.api_key, self.regions, self.timeout = (
            api_key or os.environ.get("ODDS_API_KEY"),
            regions,
            timeout,
        )
        self._get_json = get_json or self._http_get_json

    def _http_get_json(self, url: str) -> Any:
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "brasileirao-predictor/1.0"}),
                timeout=self.timeout,
            ) as response:
                return json.loads(response.read())
        except (OSError, ValueError) as exc:
            # urllib errors can embed the request URL, including apiKey.
            raise DataUnavailableError("The Odds API indisponível ou recusou a consulta") from exc

    def fetch_markets(
        self,
        *,
        markets: tuple[str, ...] = ("h2h", "totals"),
        retrieved_at: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch featured markets while preserving bookmaker-level provenance.

        Additional markets (for example ``totals_h1``) are event-scoped in The
        Odds API and intentionally use :meth:`fetch_event_markets` instead.
        """
        if not self.api_key:
            raise DataUnavailableError("ODDS_API_KEY ausente")
        if not markets or any(market not in {"h2h", "totals"} for market in markets):
            raise ValueError("markets deve conter apenas h2h/totals")
        now = retrieved_at or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("retrieved_at deve conter timezone")
        query = urlencode(
            {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": ",".join(markets),
                "oddsFormat": "decimal",
            }
        )
        payload = self._get_json(f"{BASE}/sports/{SPORT}/odds?{query}")
        if not isinstance(payload, list):
            raise DataUnavailableError("The Odds API retornou payload inválido")
        raw_hash = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        rows: list[dict[str, Any]] = []
        for event in payload:
            kickoff = _utc(event.get("commence_time"))
            event_id = event.get("id")
            if not kickoff or not isinstance(event_id, str):
                continue
            for book in event.get("bookmakers", []):
                bookmaker, captured = book.get("key"), _utc(book.get("last_update"))
                if not isinstance(bookmaker, str) or not bookmaker or not captured or captured >= kickoff:
                    continue
                for market in book.get("markets", []):
                    market_key = market.get("key")
                    if market_key not in markets:
                        continue
                    for outcome in market.get("outcomes", []):
                        price = outcome.get("price")
                        if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 1:
                            continue
                        name = outcome.get("name")
                        point = outcome.get("point")
                        if market_key == "totals":
                            if name not in ("Over", "Under") or not isinstance(point, (int, float)):
                                continue
                            canonical_market = f"ou{float(point):g}"
                            selection = name.lower()
                        else:
                            if name == event.get("home_team"):
                                selection = "home"
                            elif name == event.get("away_team"):
                                selection = "away"
                            elif name == "Draw":
                                selection = "draw"
                            else:
                                continue
                            canonical_market = "1x2"
                        rows.append(
                            {
                                "source": SOURCE,
                                "source_event_id": event_id,
                                "bookmaker": bookmaker,
                                "market": canonical_market,
                                "selection": selection,
                                "line": float(point) if isinstance(point, (int, float)) else None,
                                "decimal_odds": float(price),
                                "odds_captured_at": captured.isoformat(timespec="seconds"),
                                "retrieved_at": now.astimezone(UTC).isoformat(timespec="seconds"),
                                "canonical_match_id": f"{SOURCE}:{event_id}",
                                "raw_payload_hash": raw_hash,
                                "adapter_version": ADAPTER_VERSION,
                                "data_quality_status": "PROSPECTIVE_ELIGIBLE",
                                "kickoff_at": kickoff.isoformat(timespec="seconds"),
                                "home_team": event.get("home_team"),
                                "away_team": event.get("away_team"),
                            }
                        )
        return rows

    def fetch_event_markets(
        self,
        event_id: str,
        *,
        markets: tuple[str, ...] = ("totals_h1",),
        retrieved_at: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch event-scoped additional markets such as first-half totals."""
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id obrigatorio")
        if not markets or any(market not in {"totals_h1", "h2h_3_way_h1"} for market in markets):
            raise ValueError("mercado adicional nao suportado")
        # Reuse the same normalizer by wrapping the event endpoint response.
        if not self.api_key:
            raise DataUnavailableError("ODDS_API_KEY ausente")
        now = retrieved_at or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("retrieved_at deve conter timezone")
        query = urlencode(
            {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": ",".join(markets),
                "oddsFormat": "decimal",
            }
        )
        payload = self._get_json(f"{BASE}/sports/{SPORT}/events/{event_id}/odds?{query}")
        if not isinstance(payload, dict):
            raise DataUnavailableError("The Odds API retornou payload de evento invalido")
        return self._normalize_additional_event(payload, now=now, markets=markets)

    def _normalize_additional_event(
        self, event: dict[str, Any], *, now: datetime, markets: tuple[str, ...]
    ) -> list[dict[str, Any]]:
        kickoff = _utc(event.get("commence_time"))
        event_id = event.get("id")
        if not kickoff or not isinstance(event_id, str):
            return []
        raw_hash = hashlib.sha256(
            json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        rows = []
        for book in event.get("bookmakers", []):
            bookmaker = book.get("key")
            for market in book.get("markets", []):
                market_key = market.get("key")
                if market_key not in markets:
                    continue
                captured = _utc(market.get("last_update") or book.get("last_update"))
                if not isinstance(bookmaker, str) or not captured or captured >= kickoff:
                    continue
                for outcome in market.get("outcomes", []):
                    price, name, point = outcome.get("price"), outcome.get("name"), outcome.get("point")
                    if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 1:
                        continue
                    if market_key == "totals_h1":
                        if name not in ("Over", "Under") or not isinstance(point, (int, float)):
                            continue
                        canonical_market, selection = f"ou{float(point):g}_1h", name.lower()
                    else:
                        mapping = {event.get("home_team"): "home", "Draw": "draw", event.get("away_team"): "away"}
                        selection = mapping.get(name)
                        if selection is None:
                            continue
                        canonical_market = "1x2_1h"
                    rows.append(
                        {
                            "source": SOURCE,
                            "source_event_id": event_id,
                            "bookmaker": bookmaker,
                            "market": canonical_market,
                            "selection": selection,
                            "line": float(point) if isinstance(point, (int, float)) else None,
                            "decimal_odds": float(price),
                            "odds_captured_at": captured.isoformat(timespec="seconds"),
                            "retrieved_at": now.astimezone(UTC).isoformat(timespec="seconds"),
                            "canonical_match_id": f"{SOURCE}:{event_id}",
                            "raw_payload_hash": raw_hash,
                            "adapter_version": ADAPTER_VERSION,
                            "data_quality_status": "PROSPECTIVE_ELIGIBLE",
                            "kickoff_at": kickoff.isoformat(timespec="seconds"),
                            "home_team": event.get("home_team"),
                            "away_team": event.get("away_team"),
                        }
                    )
        return rows

    def fetch_ou25(self, *, retrieved_at: datetime | None = None) -> list[dict[str, Any]]:
        """Compatibility facade for the frozen H3/H5 cohort."""
        return [
            row
            for row in self.fetch_markets(markets=("totals",), retrieved_at=retrieved_at)
            if row["market"] == "ou2.5"
        ]
