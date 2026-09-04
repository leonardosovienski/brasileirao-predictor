"""evaluate_h14_prospective: gate de poder mecânico (falha fechado sem
métricas abaixo de n mínimo) e recusa a reescrever avaliação já feita."""

import json
from pathlib import Path

from brasileirao_predictor import db
from brasileirao_scripts import evaluate_h14_prospective as job

# bootstrap de bloco móvel exige n >= block_length (21) para poder reamostrar
MIN_N = 21


def _trials_json(path: Path, min_n: int = MIN_N) -> None:
    path.write_text(
        json.dumps([{"name": job.TRIAL, "params": {"min_n_avaliacao": min_n}}]),
        encoding="utf-8",
    )


def _seed_db_and_ledger(tmp_path: Path, n: int) -> tuple[Path, Path]:
    dbpath = tmp_path / "t.db"
    conn = db.connect(str(dbpath))
    ledger_path = tmp_path / "h14.jsonl"
    lines = []
    for i in range(n):
        eid = 100 + i
        home_score, away_score = (2, 0) if i % 2 else (0, 2)
        conn.execute(
            "INSERT INTO sofascore_matches (event_id, competition, season, date, home_team, away_team, "
            "home_score, away_score) VALUES (?, 'T', '2027', '2027-01-01', 'A', 'B', ?, ?)",
            (eid, home_score, away_score),
        )
        record = {
            "event_id": eid,
            "home": "A",
            "away": "B",
            "serving_v2": {"p_home": 0.6, "p_draw": 0.2, "p_away": 0.2},
            "climatology": {"p_home": 0.33, "p_draw": 0.34, "p_away": 0.33},
        }
        lines.append(json.dumps(record))
    conn.commit()
    conn.close()
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dbpath, ledger_path


def test_abaixo_do_n_minimo_nao_calcula_nada(tmp_path):
    dbpath, ledger_path = _seed_db_and_ledger(tmp_path, n=3)
    trials_path = tmp_path / "trials.json"
    _trials_json(trials_path, min_n=MIN_N)

    result = job.evaluate(trials_path=trials_path, ledger_path=ledger_path, db_path=dbpath)
    assert result["status"] == "AGUARDANDO_N"
    assert result["n"] == 3
    assert result["faltam"] == MIN_N - 3
    assert "primary_rps" not in result
    assert "guardrails" not in result


def test_no_n_minimo_calcula_e_reporta_veredito(tmp_path):
    dbpath, ledger_path = _seed_db_and_ledger(tmp_path, n=MIN_N)
    trials_path = tmp_path / "trials.json"
    _trials_json(trials_path, min_n=MIN_N)

    result = job.evaluate(trials_path=trials_path, ledger_path=ledger_path, db_path=dbpath)
    assert result["n"] == MIN_N
    assert result["status"] in {"COMPROVADA", "REFUTADA", "INCONCLUSIVA"}
    assert "primary_rps" in result
    assert result["capital_enabled"] is False


def test_main_recusa_sobrescrever_relatorio_existente(tmp_path, monkeypatch):
    dbpath, ledger_path = _seed_db_and_ledger(tmp_path, n=MIN_N)
    trials_path = tmp_path / "trials.json"
    _trials_json(trials_path, min_n=MIN_N)
    reports_dir = tmp_path / "reports"

    monkeypatch.setattr(job, "TRIALS_PATH", trials_path)
    monkeypatch.setattr(job, "LEDGER_PATH", ledger_path)
    monkeypatch.setattr(job, "REPORTS_DIR", reports_dir)
    # cfg["database"] absoluto: ROOT / <absoluto> resolve pro próprio absoluto (pathlib).
    monkeypatch.setattr(job, "load_config", lambda: {"database": str(dbpath)})

    assert job.main() == 0
    written = list(reports_dir.glob("h14_avaliacao_*.json"))
    assert len(written) == 1

    assert job.main() == 1  # segunda chamada: recusa sobrescrever
    assert len(list(reports_dir.glob("h14_avaliacao_*.json"))) == 1


def test_ignora_previsoes_sem_resultado_ainda(tmp_path):
    dbpath, ledger_path = _seed_db_and_ledger(tmp_path, n=MIN_N)
    # Acrescenta uma previsão de um evento SEM placar (jogo ainda não jogado).
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "event_id": 999,
                    "home": "C",
                    "away": "D",
                    "serving_v2": {"p_home": 0.5, "p_draw": 0.3, "p_away": 0.2},
                    "climatology": {"p_home": 0.33, "p_draw": 0.34, "p_away": 0.33},
                }
            )
            + "\n"
        )
    trials_path = tmp_path / "trials.json"
    _trials_json(trials_path, min_n=MIN_N)

    result = job.evaluate(trials_path=trials_path, ledger_path=ledger_path, db_path=dbpath)
    assert result["n"] == MIN_N  # não n+1 linhas do ledger
