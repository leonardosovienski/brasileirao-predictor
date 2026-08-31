from datetime import UTC, date, datetime

import pytest
from predictor_core.data.contracts import DataUnavailableError

from brasileirao_predictor.data.sportmonks_provider import SportmonksProvider


def test_sportmonks_uses_raw_authorization_and_hides_token():
    seen = {}
    payload = {
        "data": [
            {
                "id": 9,
                "starting_at": "2026-07-25T21:00:00Z",
                "state_id": 1,
                "participants": [
                    {"name": "Bahia", "meta": {"location": "home"}},
                    {"name": "Flamengo", "meta": {"location": "away"}},
                ],
            }
        ]
    }

    def fake(_url, headers):
        seen.update(headers)
        return payload

    provider = SportmonksProvider(token="synthetic-test-token", get_json=fake)
    rows = provider.list_fixtures(
        league_id=71,
        from_date=date(2026, 7, 25),
        to_date=date(2026, 7, 26),
        observed_at=datetime(2026, 7, 20, tzinfo=UTC),
    )
    assert seen["Authorization"] == "synthetic-test-token"
    assert "synthetic-test-token" not in repr(rows)
    assert rows[0]["shadow_only"] is True


def test_sportmonks_reports_league_outside_subscription():
    payload = {"data": [{"id": 271, "name": "Superliga", "country": {"name": "Denmark"}}]}
    provider = SportmonksProvider(token="synthetic", get_json=lambda *_: payload)
    with pytest.raises(DataUnavailableError, match="não coberta"):
        provider.require_league("Serie A", "Brazil")


def test_sportmonks_requires_environment_secret(monkeypatch):
    monkeypatch.delenv("SPORTMONKS_API_TOKEN", raising=False)
    with pytest.raises(DataUnavailableError, match="SPORTMONKS_API_TOKEN"):
        SportmonksProvider(get_json=lambda *_: {}).accessible_leagues()


def test_sportmonks_resolves_unique_league_and_filters_invalid_rows():
    leagues = {
        "data": [
            {"id": 71, "name": "Serie A", "country": {"name": "Brazil"}},
            {"id": None, "name": "invalid"},
        ]
    }
    provider = SportmonksProvider(token="synthetic", get_json=lambda *_: leagues)
    assert provider.require_league("Serie A", "Brazil") == 71

    fixtures = {"data": [{"id": 1, "starting_at": "bad", "participants": []}, {}]}
    provider = SportmonksProvider(token="synthetic", get_json=lambda *_: fixtures)
    assert (
        provider.list_fixtures(
            league_id=71,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 2),
            observed_at=datetime.now(UTC),
        )
        == []
    )


@pytest.mark.parametrize("payload", [[], {}, {"data": None}])
def test_sportmonks_rejects_invalid_payloads(payload):
    provider = SportmonksProvider(token="synthetic", get_json=lambda *_: payload)
    with pytest.raises(DataUnavailableError):
        provider.accessible_leagues()


def test_sportmonks_rejects_naive_observation_time():
    provider = SportmonksProvider(token="synthetic", get_json=lambda *_: {"data": []})
    with pytest.raises(ValueError, match="timezone"):
        provider.list_fixtures(
            league_id=71,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 2),
            observed_at=datetime(2026, 1, 1),
        )
