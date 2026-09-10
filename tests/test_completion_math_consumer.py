import math
import sqlite3
import sys

import numpy as np
import pytest
from pydantic import ValidationError
from test_prediction_protocol import NOW, candidate

from brasileirao_predictor import event_models, market_pricer
from brasileirao_predictor.prediction_protocol import assess_prediction_readiness


def test_total_negative_binomial_is_sum_of_two_team_distributions():
    home, away, probs = event_models.predict_event(
        1900, 1500, {"a": 0.0, "b": 1.0, "alpha": 0.5, "distribution": "nbinom"}
    )
    expected_zero = (1 + 0.5 * home) ** -2 * (1 + 0.5 * away) ** -2
    assert probs["under_0.5"] == pytest.approx(expected_zero, abs=1e-12)


@pytest.mark.parametrize(
    "grid", [np.array([[-0.1, 0.2], [0.3, 0.6]]), np.ones((2, 2)), np.array([[math.nan]]), np.empty((0, 0))]
)
def test_market_pricer_rejects_invalid_probability_measures(grid):
    with pytest.raises(ValueError):
        market_pricer.result_1x2(grid)


@pytest.mark.parametrize("line", [math.nan, math.inf, 0.3, True])
def test_handicap_rejects_unsupported_or_invalid_lines(line):
    with pytest.raises(ValueError):
        market_pricer.asian_handicap(np.array([[0.3, 0.2], [0.2, 0.3]]), line)


def test_prediction_protocol_rejects_negative_live_score():
    from datetime import timedelta

    with pytest.raises(ValidationError):
        assess_prediction_readiness(
            candidate(
                prediction_kind="LIVE",
                kickoff_at=NOW - timedelta(minutes=10),
                live_observed_at=NOW,
                observed_minute=10,
                current_score=(-1, 0),
            )
        )


@pytest.mark.parametrize("period", [False, True])
def test_full_prediction_cli_cannot_succeed_after_audit_log_failure(monkeypatch, period):
    from brasileirao_predictor import prediction_log
    from brasileirao_scripts import prever

    conn = sqlite3.connect(":memory:")
    conn.executescript("""CREATE TABLE current_elo(team TEXT, elo REAL);
        INSERT INTO current_elo VALUES ('A',1500),('B',1500);
        CREATE TABLE model_parameters(id INTEGER,param_a REAL,param_b REAL,param_alpha REAL,param_rho REAL);
        INSERT INTO model_parameters VALUES(1,0.2,0.7,0.1,-0.03);
        CREATE TABLE matches(date TEXT,home_team TEXT,away_team TEXT,home_score INTEGER);
        INSERT INTO matches VALUES('2026-10-01','A','B',NULL);""")
    monkeypatch.setattr(prever, "build", lambda cfg: (conn, {"A": 1500, "B": 1500}, (0.2, 0.7, 0.1, -0.03)))
    monkeypatch.setattr(prever, "load_config", lambda: {"elo": {"home_advantage": 0}, "model": {"max_goals": 8}})
    monkeypatch.setattr(sys, "argv", ["prever", "A", "B", "--json"] + (["--primeiro-tempo"] if period else []))

    def failed_log(*args, **kwargs):
        raise OSError("synthetic disk full")

    monkeypatch.setattr(prediction_log, "log_prediction", failed_log)
    monkeypatch.setattr(prediction_log, "log_period_prediction", failed_log)
    with pytest.raises(RuntimeError, match="audit log"):
        prever.main()
