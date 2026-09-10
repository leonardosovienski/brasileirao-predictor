"""CPL regressions: actual consumer consistency, temporal conflicts and source loss."""

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from brasileirao_predictor import display, model, predict
from brasileirao_predictor.data.bitemporal_store import BitemporalObservation, append, as_known_at, connect
from brasileirao_predictor.data.sportmonks_provider import SportmonksProvider


def test_show_logs_and_displays_one_calculation_and_one_dated_quote(monkeypatch):
    from brasileirao_predictor import prediction_log

    calls, dates, logged = [], [], []
    original = model.predict_match

    def prediction(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    def quote(conn, home, away, match_date=None):
        dates.append(match_date)
        return None

    monkeypatch.setattr(model, "predict_match", prediction)
    monkeypatch.setattr(predict, "_market_probs", quote)
    monkeypatch.setattr(prediction_log, "log_prediction", lambda *a, **kw: logged.append((a, kw)))
    monkeypatch.setattr(predict, "emit_event", lambda *a, **kw: None)
    data = predict.show(
        "A",
        "B",
        {"A": 1500, "B": 1550},
        (0.2, 0.7, 0.1, -0.03),
        {"elo": {"home_advantage": 0}, "model": {"max_goals": 8}, "backtest": {}},
        True,
        conn=object(),
        match_date="2024-07-05",
        quiet=True,
    )
    assert len(calls) == 1
    assert dates == ["2024-07-05"]
    assert data["core"]["p_win"] == logged[0][0][6]["p_win"]
    assert data["meta"]["match_date"] == logged[0][1]["match_date"]


def test_bitemporal_conflicting_versions_have_no_arbitrary_hash_winner(tmp_path):
    conn = connect(tmp_path / "conflict.db")
    for goals in (1, 2):
        append(
            conn,
            BitemporalObservation(
                "match_result",
                "e1",
                "synthetic",
                datetime(2020, 1, 1, tzinfo=UTC),
                datetime(2020, 1, 2, tzinfo=UTC),
                datetime(2020, 1, 3, tzinfo=UTC),
                {"goals": goals},
                "cpl",
            ),
        )
    with pytest.raises(ValueError, match="conflict"):
        as_known_at(conn, "match_result", datetime(2020, 1, 4, tzinfo=UTC))


def test_sportmonks_partial_page_cannot_claim_absent_league():
    calls = []

    def transport(url, headers):
        calls.append(url)
        page = int(parse_qs(urlsplit(url).query).get("page", ["1"])[0])
        return {
            "data": [{"id": page, "name": "Serie A" if page == 2 else "Other", "country": {"name": "Brazil"}}],
            "pagination": {"current_page": page, "has_more": page == 1},
        }

    provider = SportmonksProvider(token="synthetic", get_json=transport)
    # Default budget remains one request; it must report incomplete coverage.
    from predictor_core.data.contracts import DataUnavailableError

    with pytest.raises(DataUnavailableError, match="pag|incomplet"):
        provider.require_league("Serie A", "Brazil")
    assert len(calls) == 1


def test_display_does_not_certify_economic_confidence_from_config_only():
    confidence = display._confidence(
        {"market": {"source": "synthetic"}},
        {"edge_ou25": {"Over": 0.06, "Under": -0.10}},
        {"backtest": {"min_edge": 0.04, "max_edge": 0.08}},
    )
    assert confidence["level"] != "ALTA"
