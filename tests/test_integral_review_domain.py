"""Unsupported league simulation must abstain before opening any database."""

import pytest

from brasileirao_predictor import db, ingest, simulator


def test_league_simulator_rejects_before_database_connection(monkeypatch):
    monkeypatch.setattr(
        ingest, "load_config", lambda: {"database": "unused.db", "tournament_name": "Brasileirão Série A"}
    )

    def forbidden_connect(*args, **kwargs):
        raise AssertionError("unsupported_simulation_opened_database")

    monkeypatch.setattr(db, "connect", forbidden_connect)
    with pytest.raises(SystemExit, match="simulação de liga não implementada"):
        simulator.monte_carlo(n=1)
