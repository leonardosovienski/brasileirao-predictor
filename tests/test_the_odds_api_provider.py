from datetime import UTC, datetime

import pytest
from predictor_core.data.contracts import DataUnavailableError

from src.data.the_odds_api_provider import TheOddsApiProvider


def test_normalizes_explicit_bookmaker_and_pre_event_quote():
    payload = [
        {
            "id": "evt",
            "commence_time": "2026-08-01T20:00:00Z",
            "home_team": "Bahia",
            "away_team": "Santos",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "last_update": "2026-08-01T19:00:00Z",
                    "markets": [
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "point": 2.5, "price": 2.1},
                                {"name": "Under", "point": 2.5, "price": 1.8},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    rows = TheOddsApiProvider(api_key="test", get_json=lambda _: payload).fetch_ou25(
        retrieved_at=datetime(2026, 8, 1, tzinfo=UTC)
    )
    assert {(r["bookmaker"], r["selection"]) for r in rows} == {
        ("pinnacle", "over"),
        ("pinnacle", "under"),
    }


def test_normalizes_1x2_and_multiple_total_lines():
    payload = [
        {
            "id": "evt",
            "commence_time": "2026-08-10T20:00:00Z",
            "home_team": "Bahia",
            "away_team": "Flamengo",
            "bookmakers": [
                {
                    "key": "book",
                    "last_update": "2026-08-10T10:00:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Bahia", "price": 3.0},
                                {"name": "Draw", "price": 3.2},
                                {"name": "Flamengo", "price": 2.4},
                            ],
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "price": 1.8, "point": 2.5},
                                {"name": "Under", "price": 2.1, "point": 2.5},
                                {"name": "Over", "price": 2.4, "point": 3.5},
                                {"name": "Under", "price": 1.6, "point": 3.5},
                            ],
                        },
                    ],
                }
            ],
        }
    ]
    provider = TheOddsApiProvider(api_key="x", get_json=lambda _: payload)
    rows = provider.fetch_markets(retrieved_at=datetime(2026, 8, 10, 11, tzinfo=UTC))
    assert {(row["market"], row["selection"]) for row in rows} == {
        ("1x2", "home"),
        ("1x2", "draw"),
        ("1x2", "away"),
        ("ou2.5", "over"),
        ("ou2.5", "under"),
        ("ou3.5", "over"),
        ("ou3.5", "under"),
    }


def test_normalizes_event_scoped_first_half_totals():
    payload = {
        "id": "evt",
        "commence_time": "2026-08-10T20:00:00Z",
        "home_team": "Bahia",
        "away_team": "Flamengo",
        "bookmakers": [
            {
                "key": "book",
                "last_update": "2026-08-10T10:00:00Z",
                "markets": [
                    {
                        "key": "totals_h1",
                        "last_update": "2026-08-10T10:05:00Z",
                        "outcomes": [
                            {"name": "Over", "price": 2.05, "point": 1.5},
                            {"name": "Under", "price": 1.75, "point": 1.5},
                        ],
                    }
                ],
            }
        ],
    }
    provider = TheOddsApiProvider(api_key="x", get_json=lambda _: payload)
    rows = provider.fetch_event_markets("evt", retrieved_at=datetime(2026, 8, 10, 11, tzinfo=UTC))
    assert {(row["market"], row["selection"]) for row in rows} == {
        ("ou1.5_1h", "over"),
        ("ou1.5_1h", "under"),
    }
    assert {row["odds_captured_at"] for row in rows} == {"2026-08-10T10:05:00+00:00"}
    assert rows[0]["canonical_match_id"] == "the_odds_api:evt"


def test_rejects_aggregate_without_bookmaker_or_post_kickoff_quote():
    payload = [
        {
            "id": "evt",
            "commence_time": "2026-08-01T20:00:00Z",
            "bookmakers": [
                {"last_update": "2026-08-01T19:00:00Z", "markets": []},
                {"key": "x", "last_update": "2026-08-01T21:00:00Z", "markets": []},
            ],
        }
    ]
    assert TheOddsApiProvider(api_key="test", get_json=lambda _: payload).fetch_ou25() == []


def test_requires_key_without_network(monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    with pytest.raises(DataUnavailableError, match="ODDS_API_KEY"):
        TheOddsApiProvider(get_json=lambda _: pytest.fail("network")).fetch_ou25()


def test_transport_error_is_sanitized_even_when_url_contains_key(monkeypatch):
    provider = TheOddsApiProvider(api_key="secret-value")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(OSError("https://x/?apiKey=secret-value")),
    )
    with pytest.raises(DataUnavailableError) as exc:
        provider.fetch_ou25()
    assert "secret-value" not in str(exc.value)


def test_rejects_invalid_featured_market_requests_without_network():
    provider = TheOddsApiProvider(api_key="x", get_json=lambda _: pytest.fail("network"))
    with pytest.raises(ValueError, match="h2h/totals"):
        provider.fetch_markets(markets=("totals_h1",))
    with pytest.raises(ValueError, match="timezone"):
        provider.fetch_markets(retrieved_at=datetime(2026, 8, 10))


def test_rejects_invalid_event_market_requests_without_network(monkeypatch):
    provider = TheOddsApiProvider(api_key="x", get_json=lambda _: pytest.fail("network"))
    with pytest.raises(ValueError, match="event_id"):
        provider.fetch_event_markets(" ")
    with pytest.raises(ValueError, match="nao suportado"):
        provider.fetch_event_markets("evt", markets=("totals",))
    with pytest.raises(ValueError, match="timezone"):
        provider.fetch_event_markets("evt", retrieved_at=datetime(2026, 8, 10))

    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    with pytest.raises(DataUnavailableError, match="ODDS_API_KEY"):
        TheOddsApiProvider(get_json=lambda _: pytest.fail("network")).fetch_event_markets("evt")


def test_rejects_invalid_payload_shapes():
    provider = TheOddsApiProvider(api_key="x", get_json=lambda _: {})
    with pytest.raises(DataUnavailableError, match="payload inválido"):
        provider.fetch_markets()

    provider = TheOddsApiProvider(api_key="x", get_json=lambda _: [])
    with pytest.raises(DataUnavailableError, match="payload de evento invalido"):
        provider.fetch_event_markets("evt")
