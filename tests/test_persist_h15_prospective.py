"""persist_h15_prospective: cadência de refit independente por braço (10 vs.
100 jogos concluídos desde o último refit), janela pré-kickoff e
idempotência via o próprio ledger da H15."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from brasileirao_predictor import db
from brasileirao_scripts import persist_h15_prospective as job

# cron_update_models.compute() ancora o Elo em date.today() (relógio real da
# máquina, não recebe `now` como parâmetro) — os jogos concluídos sintéticos
# têm que terminar antes de hoje de verdade, então as datas são relativas ao
# momento em que o teste roda, não fixas.
_TODAY = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
KICKOFF = _TODAY + timedelta(days=2, hours=7)
HOME_ADV = 100.0

TRIAL_PARAMS = {"algorithm_version": "nbdc-normalized-elo-horizon-v2"}

CFG = {
    "elo": {
        "initial_rating": 1500,
        "home_advantage": HOME_ADV,
        "window_years": 6,
        "form_half_life_years": 4.0,
        "k_factors": {"default": 30},
    },
    "model": {"calibration_window_years": 4, "goal_half_life_days": None, "max_goals": 12},
}


def _trials_json(path: Path) -> None:
    path.write_text(json.dumps([{"name": job.TRIAL, "params": TRIAL_PARAMS}]), encoding="utf-8")


def _seed_matches(conn, n: int, start: datetime, *, id_base: int = 1000) -> None:
    """n jogos concluídos, alternando placares, com kickoff crescente antes de KICKOFF."""
    for i in range(n):
        eid = id_base + i
        kickoff = start + timedelta(days=i)
        home_score, away_score = (2, 0) if i % 3 else (1, 1)
        conn.execute(
            "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, "
            "home_score, away_score, kickoff_at) VALUES (?, 'T', '2027', ?, ?, ?, ?, ?, ?)",
            (
                eid,
                kickoff.date().isoformat(),
                f"Time{i % 4}",
                f"Time{(i + 1) % 4}",
                home_score,
                away_score,
                kickoff.isoformat(timespec="seconds"),
            ),
        )
        conn.execute(
            "INSERT INTO matches (event_id, date, home_team, away_team, home_score, away_score, tournament, neutral) "
            "VALUES (?, ?, ?, ?, ?, ?, 'T', 0)",
            (eid, kickoff.date().isoformat(), f"Time{i % 4}", f"Time{(i + 1) % 4}", home_score, away_score),
        )
    conn.commit()


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    dbpath = tmp_path / "t.db"
    conn = db.connect(str(dbpath))
    _seed_matches(conn, 15, KICKOFF - timedelta(days=100))
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, kickoff_at) "
        "VALUES (1, 'T', '2027', ?, 'Time0', 'Time1', ?)",
        (KICKOFF.date().isoformat(), KICKOFF.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()

    trials_path = tmp_path / "trials.json"
    _trials_json(trials_path)
    ledger_path = tmp_path / "h15.jsonl"
    state_dir = tmp_path / "state"
    arms = tuple(job.Arm(a.name, a.retrain_every) for a in job.ARMS)
    for arm in arms:
        monkeypatch.setattr(
            job.Arm, "state_path", property(lambda self, _dir=state_dir: _dir / f"h15_state_{self.name}.json")
        )

    monkeypatch.setattr(job, "load_config", lambda: dict(CFG, database=str(dbpath)))

    return {"db_path": dbpath, "trials_path": trials_path, "ledger_path": ledger_path, "arms": arms}


def test_primeiro_refit_acontece_para_os_dois_bracos(ambiente):
    now = KICKOFF - timedelta(hours=1)
    outcomes = job.run(
        now=now,
        trials_path=ambiente["trials_path"],
        ledger_path=ambiente["ledger_path"],
        arms=ambiente["arms"],
        db_path=ambiente["db_path"],
    )
    assert outcomes == [{"event_id": 1, "home": "Time0", "away": "Time1", "status": "PERSISTED"}]
    for arm in ambiente["arms"]:
        assert arm.state_path.exists()
        state = json.loads(arm.state_path.read_text(encoding="utf-8"))
        assert state["n_matches_at_refit"] == 15

    rows = [json.loads(line) for line in ambiente["ledger_path"].read_text(encoding="utf-8").splitlines()]
    row = rows[0]
    assert "treatment_refit10" in row and "control_refit100" in row
    assert row["treatment_refit10"]["n_matches_at_refit"] == 15
    assert row["control_refit100"]["n_matches_at_refit"] == 15


def test_braco_10_refita_antes_do_braco_100(ambiente):
    now1 = KICKOFF - timedelta(hours=2)
    job.run(
        now=now1,
        trials_path=ambiente["trials_path"],
        ledger_path=ambiente["ledger_path"],
        arms=ambiente["arms"],
        db_path=ambiente["db_path"],
    )

    # 12 jogos novos concluídos: cruza o limiar de 10 (treatment refita),
    # não cruza o de 100 (control mantém o estado antigo).
    conn = db.connect(str(ambiente["db_path"]))
    _seed_matches(conn, 12, KICKOFF - timedelta(days=200), id_base=2000)
    conn.execute("DELETE FROM sofascore_matches WHERE event_id = 1")
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, kickoff_at) "
        "VALUES (2, 'T', '2027', ?, 'Time0', 'Time1', ?)",
        ((KICKOFF + timedelta(days=1)).date().isoformat(), (KICKOFF + timedelta(days=1)).isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()

    now2 = KICKOFF + timedelta(days=1) - timedelta(hours=1)
    job.run(
        now=now2,
        trials_path=ambiente["trials_path"],
        ledger_path=ambiente["ledger_path"],
        arms=ambiente["arms"],
        db_path=ambiente["db_path"],
    )

    treatment_state = json.loads(
        next(a for a in ambiente["arms"] if a.name == "treatment_refit10").state_path.read_text(encoding="utf-8")
    )
    control_state = json.loads(
        next(a for a in ambiente["arms"] if a.name == "control_refit100").state_path.read_text(encoding="utf-8")
    )
    assert treatment_state["n_matches_at_refit"] == 27
    assert control_state["n_matches_at_refit"] == 15  # não cruzou 100 desde o último refit


def test_idempotente_nao_duplica(ambiente):
    now = KICKOFF - timedelta(hours=1)
    job.run(
        now=now,
        trials_path=ambiente["trials_path"],
        ledger_path=ambiente["ledger_path"],
        arms=ambiente["arms"],
        db_path=ambiente["db_path"],
    )
    outcomes = job.run(
        now=now,
        trials_path=ambiente["trials_path"],
        ledger_path=ambiente["ledger_path"],
        arms=ambiente["arms"],
        db_path=ambiente["db_path"],
    )
    assert outcomes == []
    rows = ambiente["ledger_path"].read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1


def test_fora_da_janela_nao_persiste(ambiente):
    now = KICKOFF - timedelta(hours=30)
    outcomes = job.run(
        now=now,
        trials_path=ambiente["trials_path"],
        ledger_path=ambiente["ledger_path"],
        arms=ambiente["arms"],
        db_path=ambiente["db_path"],
    )
    assert outcomes == []


def test_fingerprint_estavel_entre_refits(ambiente):
    now1 = KICKOFF - timedelta(hours=2)
    job.run(
        now=now1,
        trials_path=ambiente["trials_path"],
        ledger_path=ambiente["ledger_path"],
        arms=ambiente["arms"],
        db_path=ambiente["db_path"],
    )
    row1 = json.loads(ambiente["ledger_path"].read_text(encoding="utf-8").splitlines()[0])
    fp1 = row1["treatment_refit10"]["code_fingerprint"]

    conn = db.connect(str(ambiente["db_path"]))
    _seed_matches(conn, 12, KICKOFF - timedelta(days=200), id_base=2000)
    conn.execute("DELETE FROM sofascore_matches WHERE event_id = 1")
    conn.execute(
        "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, kickoff_at) "
        "VALUES (2, 'T', '2027', ?, 'Time0', 'Time1', ?)",
        ((KICKOFF + timedelta(days=1)).date().isoformat(), (KICKOFF + timedelta(days=1)).isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    now2 = KICKOFF + timedelta(days=1) - timedelta(hours=1)
    job.run(
        now=now2,
        trials_path=ambiente["trials_path"],
        ledger_path=ambiente["ledger_path"],
        arms=ambiente["arms"],
        db_path=ambiente["db_path"],
    )
    row2 = json.loads(ambiente["ledger_path"].read_text(encoding="utf-8").splitlines()[1])
    fp2 = row2["treatment_refit10"]["code_fingerprint"]
    assert fp1 == fp2  # o refit mudou os params, não a identidade do desenho
