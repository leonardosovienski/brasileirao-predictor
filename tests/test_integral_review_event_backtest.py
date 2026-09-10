"""Legacy event replay must preserve fixture/date blocks and abstain on unsupported lines."""

from copy import deepcopy

import pytest

from brasileirao_predictor import backtest_event as engine


def row(i, day, line=8.5):
    return {
        "event_id": i,
        "date": day,
        "home": f"h{i}",
        "away": f"a{i}",
        "line": line,
        "elo_home": 1500,
        "elo_away": 1500,
        "home_event": i,
        "away_event": 1,
        "total_events": i + 1,
        "open_a": 2.0,
        "open_b": 2.0,
        "close_a": 2.0,
        "close_b": 2.0,
    }


def run(monkeypatch, rows, probs=None):
    trained = []
    monkeypatch.setattr(engine, "load_config", lambda: {"elo": {}})
    monkeypatch.setattr(engine, "load_event_data", lambda *a, **kw: deepcopy(rows))

    def fit(history, *a, **kw):
        trained.extend(history)
        return {"a": 0.0, "b": 0.0}

    monkeypatch.setattr(engine, "fit_event_model", fit)
    monkeypatch.setattr(engine, "predict_event", lambda *a: (4.0, 4.0, {"over_8.5": 0.6} if probs is None else probs))
    return engine.backtest_event("corners", conn=object()), trained


def test_split_cannot_train_on_any_outcome_from_first_test_day(monkeypatch):
    rows = [row(i, "2030-01-01" if i <= 3 else "2030-01-02" if i <= 6 else "2030-01-03") for i in range(1, 8)]
    _, trained = run(monkeypatch, rows)
    assert {r["home_event"] for r in trained} == {1, 2, 3}


def test_multiple_price_lines_do_not_reweight_training_targets(monkeypatch):
    rows = [row(i, f"2030-01-0{i}") for i in range(1, 6)]
    rows.insert(1, {**rows[0], "line": 9.5})
    _, trained = run(monkeypatch, rows)
    assert len([r for r in trained if r["home_team"] == "h1"]) == 1


@pytest.mark.parametrize("line,probs", [(8.0, {"over_8.0": 0.6}), (8.5, {})])
def test_unsupported_line_or_missing_probability_abstains(monkeypatch, line, probs):
    rows = [row(i, f"2030-01-0{i}", line) for i in range(1, 6)]
    result, _ = run(monkeypatch, rows, probs)
    assert result["n_trades"] == 0
    assert result.get("abstentions") == [{"event_id": 5, "line": line, "reason": "unsupported_line_or_probability"}]


def test_one_day_cannot_supply_both_training_and_evaluation(monkeypatch):
    result, trained = run(monkeypatch, [row(i, "2030-01-01") for i in range(1, 6)])
    assert not trained
    assert result["reason"] == "no_prior_training_day"
    assert result["n_trades"] == 0


def test_conflicting_targets_for_one_event_are_rejected(monkeypatch):
    rows = [row(i, f"2030-01-0{i}") for i in range(1, 6)]
    rows.append({**rows[0], "home_event": 999})
    with pytest.raises(ValueError, match="conflicting_event_training_identity"):
        run(monkeypatch, rows)


@pytest.mark.parametrize("bad_odd", [0.0, 1.0, float("nan"), float("inf"), True])
def test_invalid_odds_cannot_be_settled_as_a_trade(monkeypatch, bad_odd):
    rows = [row(i, f"2030-01-0{i}") for i in range(1, 6)]
    rows[-1]["open_a"] = bad_odd
    result, _ = run(monkeypatch, rows)
    assert result["n_trades"] == 0
    assert result["abstentions"][0]["reason"] == "invalid_decimal_odds"
