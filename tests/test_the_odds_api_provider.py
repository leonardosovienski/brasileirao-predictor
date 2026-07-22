from datetime import datetime, timezone

import pytest

from predictor_core.data.contracts import DataUnavailableError
from src.data.the_odds_api_provider import TheOddsApiProvider


def test_normalizes_explicit_bookmaker_and_pre_event_quote():
    payload = [{"id":"evt", "commence_time":"2026-08-01T20:00:00Z", "home_team":"Bahia", "away_team":"Santos", "bookmakers":[{"key":"pinnacle", "last_update":"2026-08-01T19:00:00Z", "markets":[{"key":"totals", "outcomes":[{"name":"Over", "point":2.5, "price":2.1}, {"name":"Under", "point":2.5, "price":1.8}]}]}]}]
    rows = TheOddsApiProvider(api_key="test", get_json=lambda _: payload).fetch_ou25(retrieved_at=datetime(2026, 8, 1, tzinfo=timezone.utc))
    assert {(r["bookmaker"], r["selection"]) for r in rows} == {("pinnacle", "over"), ("pinnacle", "under")}
    assert rows[0]["canonical_match_id"] == "the_odds_api:evt"


def test_rejects_aggregate_without_bookmaker_or_post_kickoff_quote():
    payload = [{"id":"evt", "commence_time":"2026-08-01T20:00:00Z", "bookmakers":[{"last_update":"2026-08-01T19:00:00Z", "markets":[]}, {"key":"x", "last_update":"2026-08-01T21:00:00Z", "markets":[]}]}]
    assert TheOddsApiProvider(api_key="test", get_json=lambda _: payload).fetch_ou25() == []


def test_requires_key_without_network(monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    with pytest.raises(DataUnavailableError, match="ODDS_API_KEY"):
        TheOddsApiProvider(get_json=lambda _: pytest.fail("network")).fetch_ou25()


def test_transport_error_is_sanitized_even_when_url_contains_key(monkeypatch):
    provider = TheOddsApiProvider(api_key="secret-value")
    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: (_ for _ in ()).throw(OSError("https://x/?apiKey=secret-value")))
    with pytest.raises(DataUnavailableError) as exc:
        provider.fetch_ou25()
    assert "secret-value" not in str(exc.value)
