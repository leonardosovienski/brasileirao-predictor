import copy
import sqlite3

import pytest

from extract_inputs import eligible_ids, materialize, query_rows, validate_schedule

AS_OF = "2026-09-07T22:00:00+00:00"


def fixture(event_id=1, round_number=20, kickoff="2026-09-01T22:00:00+00:00"):
    return {
        "event_id": event_id, "cbf_ref": event_id, "season": 2026,
        "round": round_number,
        "role": "test_exploratory" if round_number <= 19 else "paper_betting",
        "home_team": "Home", "away_team": "Away", "kickoff_at": kickoff,
        "superseded_event_ids": [],
    }


def source(event_id=1):
    return {
        "event_id": event_id, "date": "2026-09-01", "s_date": "2026-09-01",
        "kickoff_at": "2026-09-01T22:00:00+00:00",
        "s_home": "Home", "s_away": "Away", "home_team": "Home", "away_team": "Away",
        "s_home_score": 2, "s_away_score": 1, "home_score": 2, "away_score": 1,
        "superseded_by_event_id": None, "result_observed_at": None,
        "odds_home": 2.0, "odds_draw": 3.0, "odds_away": 4.0,
        "odds_over": 1.9, "odds_under": 1.9, "odds_btts_yes": 1.8,
        "odds_btts_no": 2.0, "neutral": 0,
    }


def run(row=None, item=None):
    return materialize([item or fixture()], [row or source()], AS_OF, 48, expected_size=1)[0]


def test_concordant_completed_game_and_all_prices():
    result = run()
    assert result["completion_state"] == "COMPLETED"
    assert result["result"]["home_goals"] == 2
    assert result["odds"]["1x2"] == [2.0, 3.0, 4.0]
    assert result["odds_execution_attested"] is False


@pytest.mark.parametrize("bad", [-1, 1.5, True, "2"])
def test_invalid_scores_not_settled(bad):
    row = source()
    row["home_score"] = bad
    assert run(row)["completion_state"] == "REJECTED_INVALID_RESULT"


def test_conflicting_score_sources_not_settled():
    row = source()
    row["s_home_score"] = 3
    result = run(row)
    assert result["completion_state"] == "REJECTED_RESULT_CONFLICT"
    assert result["result"] is None
    assert result["odds"]["1x2"] == [None, None, None]


def test_missing_score_not_assumed_finished_from_date():
    row = source()
    row["home_score"] = None
    assert run(row)["completion_state"] == "PENDING_RESULT"


@pytest.mark.parametrize("observed", ["2026-09-08T00:00:00+00:00", "invalid", "2026-09-01T00:00:00"])
def test_future_or_invalid_result_observation_excluded(observed):
    row = source()
    row["result_observed_at"] = observed
    assert run(row)["completion_state"] == "RESULT_UNAVAILABLE_AS_OF"


def test_result_timestamp_exact_asof_allowed():
    row = source()
    row["result_observed_at"] = AS_OF
    assert run(row)["completion_state"] == "COMPLETED"


def test_all_pending_fixtures_retained_and_not_queried():
    scheduled = [fixture(1), fixture(2, kickoff="2026-09-07T00:00:00+00:00"), fixture(3, kickoff=None)]
    assert eligible_ids(scheduled, AS_OF, 48) == [1]
    output = materialize(scheduled, [source()], AS_OF, 48, expected_size=3)
    assert len(output) == 3
    assert [r["completion_state"] for r in output] == ["COMPLETED", "PENDING_COMPLETION_BUFFER", "PENDING_KICKOFF"]


def test_first_turn_role_follows_round_even_if_postponed():
    item = fixture(round_number=18)
    assert run(item=item)["role"] == "test_exploratory"


def test_duplicate_or_unexpected_database_identity_rejected():
    with pytest.raises(ValueError, match="Unexpected or duplicate"):
        materialize([fixture()], [source(), source()], AS_OF, 48, expected_size=1)
    with pytest.raises(ValueError, match="Unexpected or duplicate"):
        materialize([fixture()], [source(2)], AS_OF, 48, expected_size=1)


def test_superseded_alias_cannot_be_used():
    row = source()
    row["superseded_by_event_id"] = 99
    assert run(row)["completion_state"] == "REJECTED_SUPERSEDED_IDENTITY"
    item = fixture()
    item["superseded_event_ids"] = [1]
    with pytest.raises(ValueError, match="superseded"):
        validate_schedule([item], expected_size=1)


@pytest.mark.parametrize("field,value,state", [
    ("s_home", "Other", "REJECTED_TEAM_MISMATCH"),
    ("home_team", "Other", "REJECTED_MATCHES_TEAM_MISMATCH"),
    ("kickoff_at", "2026-09-01T20:00:00+00:00", "REJECTED_KICKOFF_MISMATCH"),
])
def test_identity_metadata_mismatch_rejected(field, value, state):
    row = source()
    row[field] = value
    assert run(row)["completion_state"] == state


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 1.0, 0, "2.0", True])
def test_invalid_odds_missing_without_inventing_price(bad):
    row = source()
    row["odds_home"] = bad
    output = run(row)
    assert output["completion_state"] == "COMPLETED"
    assert output["odds"]["1x2"] == [None, 3.0, 4.0]


def test_round_role_corruption_rejected():
    item = fixture()
    item["role"] = "train"
    with pytest.raises(ValueError, match="Role"):
        validate_schedule([item], expected_size=1)


def test_duplicate_canonical_identity_rejected():
    item = fixture()
    with pytest.raises(ValueError, match="Duplicate"):
        validate_schedule([item, copy.deepcopy(item)], expected_size=2)


def test_sql_filters_exact_ids_and_future_before_fetch(tmp_path):
    path = tmp_path / "only_synthetic.sqlite"
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE sofascore_matches (
        event_id INTEGER, date TEXT, kickoff_at TEXT, home_team TEXT, away_team TEXT,
        home_score INTEGER, away_score INTEGER, superseded_by_event_id INTEGER,
        result_observed_at TEXT, odds_home REAL, odds_draw REAL, odds_away REAL,
        odds_over REAL, odds_under REAL, odds_btts_yes REAL, odds_btts_no REAL)""")
    c.execute("""CREATE TABLE matches (event_id INTEGER, date TEXT, home_team TEXT,
        away_team TEXT, home_score INTEGER, away_score INTEGER, tournament TEXT,
        city TEXT, neutral INTEGER)""")
    for eid, date, kickoff in [(1,"2026-09-01","2026-09-01T22:00:00+00:00"),
                               (2,"2026-09-01","2026-09-01T22:00:00+00:00"),
                               (3,"2026-09-07","2026-09-07T22:00:00+00:00"),
                               (4,"2025-09-01","2025-09-01T22:00:00+00:00"),
                               (5,"2026-09-01","2026-09-01T22:00:00+00:00")]:
        c.execute("INSERT INTO sofascore_matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  [eid,date,kickoff,"Home","Away",2,1,None,"2026-09-08T00:00:00+00:00" if eid == 5 else None,2,3,4,1.9,1.9,1.8,2])
        c.execute("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?)", [eid,date,"Home","Away",2,1,"League",None,0])
    c.commit()
    c.close()
    before = path.read_bytes()
    result = query_rows(path, [1, 3, 4, 5], AS_OF, 48)
    assert [r["event_id"] for r in result] == [1]
    assert path.read_bytes() == before


def test_empty_allowlist_does_not_open_database(tmp_path):
    assert query_rows(tmp_path / "does-not-exist.sqlite", [], AS_OF, 48) == []
