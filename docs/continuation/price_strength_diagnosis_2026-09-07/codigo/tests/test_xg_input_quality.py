"""Regressions for provider identity, zero ambiguity and reported coverage."""

import itertools
import sqlite3

import pytest

from brasileirao_predictor.data.missingness_audit import xg_coverage
from brasileirao_predictor.data.xg_quality import classify_xg_pair
from brasileirao_predictor.ingest_sofascore import parse_xg


def payload(*items, period="ALL"):
    return {"statistics": [{"period": period, "groups": [{"statisticsItems": list(items)}]}]}


def item(home="1.2", away="0.7", **extra):
    return {"name": "Expected goals", "home": home, "away": away, **extra}


def test_xgot_cannot_substitute_for_expected_goals():
    other = item("2.9", "3.8", name="Expected goals on target")
    assert parse_xg(payload(other)) == (None, None)
    for order in itertools.permutations([other, item()]):
        assert parse_xg(payload(*order)) == (1.2, 0.7)


def test_conflicting_full_match_xg_is_rejected_in_every_order():
    for order in itertools.permutations([item(), item("2.1")]):
        assert parse_xg(payload(*order)) == (None, None)
    assert parse_xg(payload(item(), item())) == (1.2, 0.7)


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -0.1, "nan", "-1", {}, []])
def test_invalid_xg_never_becomes_a_provider_observation(value):
    assert parse_xg(payload(item(value))) == (None, None)


@pytest.mark.parametrize("value", [None, [], {"statistics": None}, {"statistics": [None]}, {"statistics": "bad"}])
def test_malformed_payload_is_missing_without_crashing(value):
    assert parse_xg(value) == (None, None)


def test_period_identity_and_real_zero_are_preserved():
    assert parse_xg(payload(item(), period="1ST")) == (None, None)
    assert parse_xg(payload(item("0", "0"))) == (0.0, 0.0)
    assert parse_xg(payload(item("0", "1.2"))) == (0.0, 1.2)
    assert parse_xg(payload(item(key="expectedGoalsOnTarget"))) == (None, None)
    assert parse_xg(payload(item(key="expectedGoals"))) == (1.2, 0.7)


@pytest.mark.parametrize(
    ("pair", "expected"),
    [
        ((None, None), "MISSING_PAIR"),
        ((1, None), "PARTIAL_PAIR"),
        ((0, 0), "ZERO_PAIR_UNATTESTED"),
        ((0, 1), "NUMERIC_PAIR"),
        ((1.2, 0.7), "NUMERIC_PAIR"),
        (("0", 1), "INVALID_PAIR"),
        ((True, 1), "INVALID_PAIR"),
        ((-1, 1), "INVALID_PAIR"),
        ((float("inf"), 1), "INVALID_PAIR"),
        ((float("nan"), 1), "INVALID_PAIR"),
    ],
)
def test_pair_classification_preserves_zero_ambiguity(pair, expected):
    assert classify_xg_pair(*pair) == expected


def test_presence_does_not_claim_numeric_quality_or_attested_coverage():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE sofascore_matches (season, home_score, away_score, home_xg, away_xg)")
    conn.executemany(
        "INSERT INTO sofascore_matches VALUES (?,?,?,?,?)",
        [
            ("2021", 3, 2, 0, 0),
            ("2021", 0, 0, 0, 0),
            ("2022", 0, 0, 0, 1),
            ("2022", 1, 0, None, 1),
            ("2022", 1, 0, -1, 1),
            ("2022", 1, 0, "not-xg", 1),
            ("2022", None, None, 1, 1),
        ],
    )
    result = xg_coverage(conn)
    assert result["total"]["played"] == 6
    assert result["total"]["paired_xg_present"] == 5
    assert result["total"]["paired_xg_numeric"] == 3
    assert result["total"]["zero_pair_unattested"] == 2
    assert result["total"]["numeric_nonzero_pair"] == 1
    assert result["total"]["invalid_pair"] == 2
    assert result["total"]["partial_pair"] == 1
    assert result["source_provenance_attested"] is False
    assert result["seasons"][0]["all_reported_pairs_zero"] is True
    # The audit is read-only and does not decide whether a zero is factual.
    assert conn.execute("SELECT COUNT(*) FROM sofascore_matches WHERE home_xg=0 AND away_xg=0").fetchone()[0] == 2
    conn.close()
