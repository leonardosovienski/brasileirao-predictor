from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest
from predictor_core.data.contracts import DataUnavailableError

from src.data.api_football_provider import ApiFootballProvider


def test_api_football_normalizes_historical_fixture_and_hides_key():
    seen = {}
    payload = {
        "errors": {},
        "response": [
            {
                "fixture": {"id": 123, "date": "2024-07-25T21:00:00Z", "status": {"short": "FT"}},
                "teams": {"home": {"name": "Bahia"}, "away": {"name": "Flamengo"}},
                "goals": {"home": 1, "away": 2},
            }
        ],
    }

    def fake(url, headers):
        seen.update(headers)
        seen["query"] = parse_qs(urlparse(url).query)
        return payload

    provider = ApiFootballProvider(api_key="synthetic-test-key", get_json=fake)
    rows = provider.list_fixtures(season=2024, observed_at=datetime(2026, 7, 20, tzinfo=UTC))
    assert seen["x-apisports-key"] == "synthetic-test-key"
    assert seen["query"] == {"league": ["71"], "season": ["2024"]}
    assert rows[0]["home_team"] == "Bahia"
    assert rows[0]["home_goals"] == 1
    assert rows[0]["shadow_only"] is True
    assert "synthetic-test-key" not in repr(rows)


def test_api_football_rejects_season_outside_free_window_without_request():
    provider = ApiFootballProvider(api_key="synthetic", get_json=lambda *_: pytest.fail("não deveria consultar"))
    with pytest.raises(DataUnavailableError, match="2022-2024"):
        provider.list_fixtures(season=2026)


def test_api_football_surfaces_provider_errors():
    provider = ApiFootballProvider(
        api_key="synthetic",
        get_json=lambda *_: {"errors": {"plan": "season not available"}, "response": []},
    )
    with pytest.raises(DataUnavailableError, match="plan: season not available"):
        provider.brasileirao_seasons()


def test_api_football_requires_environment_secret(monkeypatch):
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    with pytest.raises(DataUnavailableError, match="API_FOOTBALL_KEY"):
        ApiFootballProvider(get_json=lambda *_: {}).brasileirao_seasons()


def test_api_football_validates_league_and_filters_malformed_fixtures():
    league = {
        "errors": {},
        "response": [
            {
                "league": {"name": "Serie A"},
                "country": {"name": "Brazil"},
                "seasons": [{"year": 2024}, {"year": None}, {"year": 2022}],
            }
        ],
    }
    provider = ApiFootballProvider(api_key="synthetic", get_json=lambda *_: league)
    assert provider.brasileirao_seasons() == [2022, 2024]

    malformed = {"errors": {}, "response": [{"fixture": {}}, {"fixture": {"id": 1, "date": "bad"}}]}
    provider = ApiFootballProvider(api_key="synthetic", get_json=lambda *_: malformed)
    assert provider.list_fixtures(season=2024, observed_at=datetime.now(UTC)) == []


@pytest.mark.parametrize("payload", [[], {"response": None}, {"errors": "quota"}])
def test_api_football_rejects_invalid_provider_payloads(payload):
    provider = ApiFootballProvider(api_key="synthetic", get_json=lambda *_: payload)
    with pytest.raises(DataUnavailableError):
        provider.brasileirao_seasons()


def test_api_football_rejects_naive_observation_time():
    provider = ApiFootballProvider(api_key="synthetic", get_json=lambda *_: {"errors": {}, "response": []})
    with pytest.raises(ValueError, match="timezone"):
        provider.list_fixtures(season=2024, observed_at=datetime(2026, 1, 1))
