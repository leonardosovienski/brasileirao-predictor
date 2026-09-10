import hashlib
import json

import pytest

from brasileirao_predictor.data.odds_api_snapshot import decode_snapshot


def fixture():
    return {
        "id": "e1",
        "sport_key": "soccer_brazil_campeonato",
        "home_team": "A",
        "away_team": "B",
        "commence_time": "2024-01-01T20:00:00Z",
        "bookmakers": [
            {
                "key": "book",
                "last_update": "2024-01-01T10:00:00Z",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "A", "price": 2.0},
                            {"name": "Draw", "price": 3.0},
                            {"name": "B", "price": 4.0},
                        ],
                    }
                ],
            }
        ],
    }


def decode(payload, *, received="2024-01-01T11:00:00Z", event_id=None):
    raw = json.dumps(payload).encode()
    return decode_snapshot(
        raw, received_at=received, expected_sha256=hashlib.sha256(raw).hexdigest(), expected_event_id=event_id
    )


def test_named_complete_quote_remains_observation_with_distinct_clocks():
    out = decode([fixture()])
    event = out["events"][0]
    market = event["bookmakers"][0]["markets"][0]
    assert event["source_event_id"] == "e1" and event["received_before_kickoff"]
    assert market["complete"] and market["last_changed_at"] != market["received_at"]
    assert market["published_at"] is None
    assert out["execution"] == "ABSTAIN" and not out["economic_evidence_eligible"]


def test_old_change_received_after_kickoff_is_not_prospective():
    out = decode([fixture()], received="2024-01-02T00:00:00Z")
    assert not out["events"][0]["received_before_kickoff"]
    assert out["execution"] == "ABSTAIN"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda e: e.update(sport_key="another_league"),
        lambda e: e.update(away_team="A"),
        lambda e: e["bookmakers"][0].update(last_update="2024-01-01T12:00:00Z"),
        lambda e: e["bookmakers"].append(e["bookmakers"][0].copy()),
        lambda e: e["bookmakers"][0]["markets"][0]["outcomes"].append({"name": "A", "price": 9}),
        lambda e: e["bookmakers"][0]["markets"][0]["outcomes"][0].update(price=True),
        lambda e: e["bookmakers"][0]["markets"][0]["outcomes"][0].update(point=2.5),
        lambda e: e["bookmakers"][0]["markets"][0].update(last_update="2024-01-01T12:00:00Z"),
    ],
)
def test_invalid_latest_response_is_preserved_as_invalid_without_salvaged_events(mutation):
    event = fixture()
    mutation(event)
    out = decode([event])
    assert out["observation_status"] == "INVALID_RESPONSE"
    assert out["rejections"] and out["events"] == []


def test_missing_legs_and_empty_receipts_are_not_discarded():
    event = fixture()
    event["bookmakers"][0]["markets"][0]["outcomes"].pop()
    out = decode([event])
    assert not out["events"][0]["bookmakers"][0]["markets"][0]["complete"]
    assert decode([])["observation_status"] == "VALID_EMPTY"


def test_event_endpoint_must_match_requested_identity():
    with pytest.raises(ValueError, match="identity"):
        decode(fixture(), event_id="different")
    assert decode(fixture(), event_id="e1")["events"][0]["source_event_id"] == "e1"


def test_hash_duplicate_json_and_nonfinite_number_guards():
    for raw in (b'{"id":1,"id":2}', b"[NaN]"):
        with pytest.raises(ValueError):
            decode_snapshot(raw, received_at="2024-01-01T11:00:00Z", expected_sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError, match="SHA256"):
        decode_snapshot(b"[]", received_at="2024-01-01T11:00:00Z", expected_sha256="0" * 64)


def test_legacy_false_eligibility_is_reproduced_without_changing_protected_adapter():
    from datetime import UTC, datetime

    from brasileirao_predictor.data.the_odds_api_provider import TheOddsApiProvider

    payload = [fixture()]
    legacy = TheOddsApiProvider(api_key="synthetic", get_json=lambda _: payload).fetch_markets(
        markets=("h2h",), retrieved_at=datetime(2024, 1, 2, tzinfo=UTC)
    )
    assert legacy[0]["data_quality_status"] == "PROSPECTIVE_ELIGIBLE"
    current = decode(payload, received="2024-01-02T00:00:00Z")
    assert not current["events"][0]["received_before_kickoff"]
    assert not current["economic_evidence_eligible"]
