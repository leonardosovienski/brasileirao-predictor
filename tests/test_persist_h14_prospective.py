"""persist_h14_prospective: janela pré-kickoff, climatologia prequential
estritamente PIT, e idempotência via o próprio ledger da H14."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from brasileirao_predictor import db
from brasileirao_scripts import persist_h14_prospective as job

KICKOFF = datetime(2027, 3, 1, 19, 0, tzinfo=UTC)
ELO_HOME, ELO_AWAY, HOME_ADV = 1550, 1450, 100.0
PARAMS = (0.2, 0.7, 1e-4, 0.0)

TRIAL_PARAMS = {
    "algorithm_version": "nbdc-normalized-elo-horizon-v2",
    "ensemble_xg_enabled": False,
    "retrain_every": 100,
}


def _trials_json(path: Path) -> None:
    path.write_text(json.dumps([{"name": job.TRIAL, "params": TRIAL_PARAMS}]), encoding="utf-8")


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    dbpath = tmp_path / "t.db"
    conn = db.connect(str(dbpath))
    db.save_elo(conn, [("Casa", ELO_HOME), ("Fora", ELO_AWAY)])
    db.save_params(
        conn,
        *PARAMS,
        0,
        "test-config",
        (KICKOFF - timedelta(hours=7)).isoformat(timespec="seconds"),
    )
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, kickoff_at) "
        "VALUES (1, 'T', '2027', ?, 'Casa', 'Fora', ?)",
        (KICKOFF.date().isoformat(), KICKOFF.isoformat(timespec="seconds")),
    )
    # Um jogo já concluído ANTES do kickoff avaliado — precisa contar na
    # climatologia. Insere via sofascore_matches + espelho matches, igual ao
    # pipeline real (completed_matches_with_kickoff lê os dois).
    prior_kickoff = KICKOFF - timedelta(days=7)
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, "
        "home_score, away_score, kickoff_at) VALUES (2, 'T', '2027', ?, 'X', 'Y', 2, 0, ?)",
        (prior_kickoff.date().isoformat(), prior_kickoff.isoformat(timespec="seconds")),
    )
    conn.execute(
        "INSERT INTO matches (event_id, date, home_team, away_team, home_score, away_score, tournament, neutral) "
        "VALUES (2, ?, 'X', 'Y', 2, 0, 'T', 0)",
        (prior_kickoff.date().isoformat(),),
    )
    conn.commit()
    conn.close()

    trials_path = tmp_path / "trials.json"
    _trials_json(trials_path)
    ledger_path = tmp_path / "h14.jsonl"

    monkeypatch.setattr(job, "load_config", lambda: {"database": str(dbpath), "elo": {"home_advantage": HOME_ADV}})

    return {"db_path": dbpath, "trials_path": trials_path, "ledger_path": ledger_path}


def test_persiste_dentro_da_janela_pre_kickoff(ambiente):
    now = KICKOFF - timedelta(hours=1)
    outcomes = job.run(
        now=now, trials_path=ambiente["trials_path"], ledger_path=ambiente["ledger_path"], db_path=ambiente["db_path"]
    )
    assert outcomes == [{"event_id": 1, "home": "Casa", "away": "Fora", "status": "PERSISTED"}]
    rows = [json.loads(line) for line in ambiente["ledger_path"].read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["event_id"] == 1
    assert row["serving_v2"]["p_home"] + row["serving_v2"]["p_draw"] + row["serving_v2"]["p_away"] == pytest.approx(
        1.0, abs=1e-6
    )
    assert row["climatology"]["n_prior"] == 1  # só o jogo com kickoff anterior


def test_fora_da_janela_nao_persiste(tmp_path, monkeypatch):
    # Cache do modelo salvo bem mais cedo (KICKOFF-40h) pra que `now` possa
    # ficar fora da janela de HORIZON=24h e ainda assim dentro de
    # MAX_MODEL_CACHE_AGE=12h em relação ao cache.
    dbpath = tmp_path / "t.db"
    conn = db.connect(str(dbpath))
    db.save_elo(conn, [("Casa", ELO_HOME), ("Fora", ELO_AWAY)])
    db.save_params(conn, *PARAMS, 0, "test-config", (KICKOFF - timedelta(hours=40)).isoformat(timespec="seconds"))
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, kickoff_at) "
        "VALUES (1, 'T', '2027', ?, 'Casa', 'Fora', ?)",
        (KICKOFF.date().isoformat(), KICKOFF.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    trials_path = tmp_path / "trials.json"
    _trials_json(trials_path)
    ledger_path = tmp_path / "h14.jsonl"
    monkeypatch.setattr(job, "load_config", lambda: {"database": str(dbpath), "elo": {"home_advantage": HOME_ADV}})

    now = KICKOFF - timedelta(hours=38)  # fora de HORIZON=24h; cache com 2h de idade
    outcomes = job.run(now=now, trials_path=trials_path, ledger_path=ledger_path, db_path=dbpath)
    assert outcomes == []
    assert not ledger_path.exists() or ledger_path.read_text(encoding="utf-8") == ""


def test_apos_kickoff_nao_persiste(ambiente):
    now = KICKOFF + timedelta(minutes=1)
    outcomes = job.run(
        now=now, trials_path=ambiente["trials_path"], ledger_path=ambiente["ledger_path"], db_path=ambiente["db_path"]
    )
    assert outcomes == []


def test_idempotente_nao_duplica(ambiente):
    now = KICKOFF - timedelta(hours=1)
    job.run(
        now=now, trials_path=ambiente["trials_path"], ledger_path=ambiente["ledger_path"], db_path=ambiente["db_path"]
    )
    outcomes = job.run(
        now=now, trials_path=ambiente["trials_path"], ledger_path=ambiente["ledger_path"], db_path=ambiente["db_path"]
    )
    assert outcomes == []
    rows = ambiente["ledger_path"].read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1


def test_climatologia_ignora_jogo_com_kickoff_posterior(ambiente, monkeypatch):
    # Adiciona um segundo jogo concluído, mas DEPOIS do kickoff avaliado —
    # não pode vazar para dentro da climatologia (Regra do bloco de kickoff).
    conn = db.connect(str(ambiente["db_path"]))
    future_kickoff = KICKOFF + timedelta(days=1)
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, "
        "home_score, away_score, kickoff_at) VALUES (3, 'T', '2027', ?, 'X', 'Y', 5, 0, ?)",
        (future_kickoff.date().isoformat(), future_kickoff.isoformat(timespec="seconds")),
    )
    conn.execute(
        "INSERT INTO matches (event_id, date, home_team, away_team, home_score, away_score, tournament, neutral) "
        "VALUES (3, ?, 'X', 'Y', 5, 0, 'T', 0)",
        (future_kickoff.date().isoformat(),),
    )
    conn.commit()
    conn.close()

    now = KICKOFF - timedelta(hours=1)
    job.run(
        now=now, trials_path=ambiente["trials_path"], ledger_path=ambiente["ledger_path"], db_path=ambiente["db_path"]
    )
    row = json.loads(ambiente["ledger_path"].read_text(encoding="utf-8").splitlines()[0])
    assert row["climatology"]["n_prior"] == 1  # não os 2 disponíveis no banco


def test_fingerprint_muda_com_algorithm_version(ambiente):
    fp1 = job.code_fingerprint(TRIAL_PARAMS, "cfg-a", HOME_ADV)
    fp2 = job.code_fingerprint({**TRIAL_PARAMS, "algorithm_version": "outro"}, "cfg-a", HOME_ADV)
    assert fp1 != fp2


def test_sem_cache_de_modelo_falha_alto(ambiente):
    empty_db = ambiente["db_path"].parent / "empty.db"
    conn = db.connect(str(empty_db))
    db.save_elo(conn, [("Casa", ELO_HOME), ("Fora", ELO_AWAY)])
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, kickoff_at) "
        "VALUES (1, 'T', '2027', ?, 'Casa', 'Fora', ?)",
        (KICKOFF.date().isoformat(), KICKOFF.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    now = KICKOFF - timedelta(hours=1)
    with pytest.raises(RuntimeError, match="cache de modelo ausente"):
        job.run(now=now, trials_path=ambiente["trials_path"], ledger_path=ambiente["ledger_path"], db_path=empty_db)
