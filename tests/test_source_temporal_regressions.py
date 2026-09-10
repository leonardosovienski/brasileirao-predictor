from datetime import UTC, date, datetime

import pytest

from brasileirao_predictor.data.api_football_provider import ApiFootballProvider
from brasileirao_predictor.data.market_anchor import consensus_anchor
from brasileirao_predictor.data.sportmonks_provider import SportmonksProvider
from brasileirao_predictor.research.residual_features import lineup_state_asof


def test_lineup_published_before_cut_but_received_after_is_excluded():
    rows = [
        {
            "source_event_id": "e",
            "source": "synthetic",
            "team_id": "t",
            "player_id": "p",
            "role": "starter",
            "content_hash": "h",
            "published_at": "2024-01-01T10:00:00Z",
            "ingested_at": "2024-01-01T12:00:00Z",
        }
    ]
    assert lineup_state_asof(rows, event_id="e", asof="2024-01-01T11:00:00Z") == {}


def test_lineup_without_receipt_is_not_point_in_time_evidence():
    rows = [
        {
            "source_event_id": "e",
            "team_id": "t",
            "player_id": "p",
            "role": "starter",
            "content_hash": "h",
            "published_at": "2024-01-01T10:00:00Z",
        }
    ]
    assert lineup_state_asof(rows, event_id="e", asof="2024-01-01T11:00:00Z") == {}


def test_consensus_cannot_pool_different_fixtures():
    rows = [
        {
            "source_event_id": event,
            "market": "1x2",
            "bookmaker": book,
            "line": None,
            "odds_captured_at": "2024-01-01T10:00:00Z",
            "selection": selection,
            "decimal_odds": odd,
        }
        for event, book in (("e1", "a"), ("e2", "b"))
        for selection, odd in (("home", 2.0), ("draw", 3.0), ("away", 4.0))
    ]
    with pytest.raises(ValueError):
        consensus_anchor(rows, market="1x2")


def test_api_lineup_does_not_fabricate_publisher_timestamp():
    payload = {
        "errors": {},
        "response": [{"team": {"id": 1, "name": "A"}, "startXI": [{"player": {"id": 2, "name": "P"}}]}],
    }
    row = ApiFootballProvider(api_key="synthetic", get_json=lambda *_: payload).fixture_lineups(
        "123", observed_at=datetime(2024, 1, 1, tzinfo=UTC)
    )[0]
    assert row["published_at"] is None
    assert row["ingested_at"] == "2024-01-01T00:00:00+00:00"


def test_sportmonks_naive_start_is_utc_only_under_explicit_timezone_contract():
    urls = []
    fixture = {
        "id": 9,
        "league_id": 71,
        "starting_at": "2024-01-01 18:00:00",
        "participants": [{"name": "A", "meta": {"location": "home"}}, {"name": "B", "meta": {"location": "away"}}],
    }

    def transport(url, _headers):
        urls.append(url)
        return {"data": [fixture], "timezone": "UTC", "pagination": {"has_more": False, "current_page": 1}}

    rows = SportmonksProvider(token="synthetic", get_json=transport).list_fixtures(
        league_id=71, from_date=date(2024, 1, 1), to_date=date(2024, 1, 2), observed_at=datetime(2024, 1, 1, tzinfo=UTC)
    )
    assert len(rows) == 1
    assert rows[0]["scheduled_at"] == "2024-01-01T18:00:00+00:00"
    assert "timezone=UTC" in urls[0]
