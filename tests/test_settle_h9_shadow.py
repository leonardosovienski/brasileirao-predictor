"""settle_h9_shadow: re-resolução de identidade via histórico de cotação,
liquidação só quando o placar existe, e nunca liquida a mesma decisão 2x."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import settle_h9_shadow as job
from src import db
from src.research.h9_shadow import emit

KICKOFF = datetime(2027, 3, 1, 19, 0, tzinfo=UTC)


def _quote(source_event_id="e1", bookmaker="williamhill", selection="over", odds=1.9, captured=None):
    captured = captured or (KICKOFF - timedelta(minutes=100))
    return {
        "source_event_id": source_event_id,
        "bookmaker": bookmaker,
        "market": "ou2.5",
        "selection": selection,
        "decimal_odds": odds,
        "odds_captured_at": captured.isoformat(timespec="seconds"),
        "retrieved_at": captured.isoformat(timespec="seconds"),
        "home_team": "Casa",
        "away_team": "Fora",
        "kickoff_at": KICKOFF.isoformat(timespec="seconds"),
    }


def _write_quotes(path: Path, quotes: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(q) for q in quotes) + "\n", encoding="utf-8")


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    dbpath = tmp_path / "t.db"
    conn = db.connect(str(dbpath))
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, kickoff_at) "
        "VALUES (1, 'T', '2027', ?, 'Casa', 'Fora', ?)",
        (KICKOFF.date().isoformat(), KICKOFF.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(job, "load_config", lambda: {"database": str(dbpath)})

    market_obs_path = tmp_path / "market_observations.jsonl"
    ledger_path = tmp_path / "h9.jsonl"
    emit(
        prediction={
            "event_id": "e1",
            "kickoff_at": KICKOFF.isoformat(timespec="seconds"),
            "predicted_at": (KICKOFF - timedelta(minutes=90)).isoformat(timespec="seconds"),
            "p_over": 0.55,
        },
        quotes=[_quote(odds=2.0)],
        approved_bookmaker="williamhill",
        ledger=ledger_path,
    )
    return {"db_path": dbpath, "market_obs_path": market_obs_path, "ledger_path": ledger_path}


def _set_score(dbpath, home, away):
    conn = db.connect(str(dbpath))
    conn.execute("UPDATE sofascore_matches SET home_score=?, away_score=? WHERE event_id=1", (home, away))
    conn.commit()
    conn.close()


def test_no_open_decisions_returns_empty(tmp_path):
    outcomes = job.run(ledger_path=tmp_path / "empty.jsonl", market_obs_path=tmp_path / "mo.jsonl")
    assert outcomes == []


def test_pending_result_when_match_not_finished(ambiente):
    _write_quotes(ambiente["market_obs_path"], [_quote(odds=2.0)])
    outcomes = job.run(
        now=KICKOFF + timedelta(hours=3),
        db_path=ambiente["db_path"],
        market_obs_path=ambiente["market_obs_path"],
        ledger_path=ambiente["ledger_path"],
    )
    assert outcomes == [{"event_id": "e1", "status": "PENDING_RESULT"}]


def test_settles_once_result_and_closing_quote_exist(ambiente):
    _set_score(ambiente["db_path"], 2, 1)
    _write_quotes(
        ambiente["market_obs_path"],
        [_quote(odds=2.0), _quote(odds=1.8, captured=KICKOFF - timedelta(minutes=5))],
    )
    outcomes = job.run(
        now=KICKOFF + timedelta(hours=3),
        db_path=ambiente["db_path"],
        market_obs_path=ambiente["market_obs_path"],
        ledger_path=ambiente["ledger_path"],
    )
    assert len(outcomes) == 1
    assert outcomes[0]["status"] == "SETTLED"
    assert outcomes[0]["won"] is True  # 2+1 > 2.5
    assert outcomes[0]["closing_odds_same_book"] == pytest.approx(1.8)
    # segunda passada: decisao ja liquidada, nao aparece mais como aberta
    again = job.run(
        now=KICKOFF + timedelta(hours=4),
        db_path=ambiente["db_path"],
        market_obs_path=ambiente["market_obs_path"],
        ledger_path=ambiente["ledger_path"],
    )
    assert again == []


def test_quote_history_missing_is_reported(ambiente):
    # nenhuma cotacao gravada em market_observations.jsonl para 'e1' -> nao
    # da pra re-resolver a fixture (home/away/kickoff), fica pendente e VISIVEL
    outcomes = job.run(
        now=KICKOFF + timedelta(hours=3),
        db_path=ambiente["db_path"],
        market_obs_path=ambiente["market_obs_path"],
        ledger_path=ambiente["ledger_path"],
    )
    assert outcomes == [{"event_id": "e1", "status": "QUOTE_HISTORY_MISSING"}]
