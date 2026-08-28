from datetime import UTC, datetime, timedelta

from src.research.ou25_nested_replay import anchor_to_market_prequential


def _rows(n=40):
    start = datetime(2021, 1, 1, tzinfo=UTC)
    return [
        {
            "event_id": str(index),
            "kickoff_at": (start + timedelta(days=index)).isoformat(),
            "season": "2021",
            "p_over": 0.8,
            "actual_over": index % 2,
            "offered_odds_ou25": (2.0, 2.0),
        }
        for index in range(n)
    ]


def test_anchor_selects_market_when_model_is_worse():
    transformed, report = anchor_to_market_prequential(_rows(), minimum_history=20, block_size=10)
    assert all(fold["selected_model_weight"] == 0.0 for fold in report["folds"])
    assert all(row["p_over"] == 0.5 for row in transformed[20:])
    assert report["anchored_brier"] < report["model_brier"]


def test_anchor_does_not_split_simultaneous_kickoff_group():
    rows = _rows(n=40)
    kickoff = (datetime(2021, 1, 1, tzinfo=UTC) + timedelta(days=19)).isoformat()
    for index in range(18, 22):
        rows[index]["kickoff_at"] = kickoff
    _transformed, report = anchor_to_market_prequential(rows, minimum_history=20, block_size=10)
    assert report["folds"]
    assert report["folds"][0]["train_n"] == 18
    assert report["folds"][0]["test_n"] == 10
    assert report["folds"][0]["test_min_kickoff"] == kickoff


def test_anchor_excludes_invalid_price_pairs():
    rows = _rows(n=40)
    rows[25]["offered_odds_ou25"] = (51.0, 1.002)
    transformed, report = anchor_to_market_prequential(rows, minimum_history=20, block_size=10)
    assert len(transformed) == 39
    assert report["evaluated_n"] == 19
    assert all(row["event_id"] != "25" for row in transformed)


def test_future_labels_do_not_change_first_anchor_weight():
    rows = _rows()
    first = anchor_to_market_prequential(rows, minimum_history=20, block_size=10)[1]
    changed = [dict(row) for row in rows]
    for row in changed[20:]:
        row["actual_over"] = 1 - row["actual_over"]
    second = anchor_to_market_prequential(changed, minimum_history=20, block_size=10)[1]
    assert first["folds"][0]["selected_model_weight"] == second["folds"][0]["selected_model_weight"]
