from urllib.parse import parse_qs, urlsplit

import pytest
from predictor_core.data.contracts import DataUnavailableError

from brasileirao_predictor.data.api_football_provider import ApiFootballProvider
from brasileirao_predictor.data.sportmonks_provider import SportmonksProvider


def test_missing_pagination_does_not_prove_complete_coverage():
    provider = SportmonksProvider(token="synthetic", get_json=lambda *_: {"data": []})
    with pytest.raises(DataUnavailableError, match="paginação"):
        provider.accessible_leagues()


def test_cursor_is_encoded_and_does_not_follow_external_next_page():
    seen = []

    def get(url, _headers):
        seen.append(url)
        query = parse_qs(urlsplit(url).query)
        if len(seen) == 1:
            assert query["per_page"] == ["50"]
            return {
                "data": [],
                "pagination": {
                    "current_page": 1,
                    "has_more": True,
                    "next_cursor": "a&x=2",
                    "next_page": "https://invalid.example/token",
                },
            }
        assert "per_page" not in query
        assert query["cursor"] == ["a&x=2"]
        assert urlsplit(url).hostname == "api.sportmonks.com"
        return {
            "data": [{"id": 1, "name": "Serie A", "country": {"name": "Brazil"}}],
            "pagination": {"current_page": 1, "has_more": False},
        }

    provider = SportmonksProvider(token="synthetic", get_json=get, max_pages=2)
    assert provider.require_league("Serie A", "Brazil") == 1
    assert len(seen) == 2


def test_budget_is_enforced_without_an_extra_request():
    calls = []

    def get(*_):
        calls.append(1)
        return {"data": [], "pagination": {"current_page": 1, "has_more": True}}

    with pytest.raises(DataUnavailableError, match="orçamento"):
        SportmonksProvider(token="synthetic", get_json=get).accessible_leagues()
    assert len(calls) == 1


def test_provider_error_cannot_echo_credentials():
    provider = ApiFootballProvider(
        api_key="synthetic-private-value",
        get_json=lambda *_: {"errors": {"key": "synthetic-private-value"}, "response": []},
    )
    with pytest.raises(DataUnavailableError) as exc:
        provider.brasileirao_seasons()
    assert "synthetic-private-value" not in str(exc.value)
