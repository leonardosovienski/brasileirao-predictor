"""h10_fadiga_walkforward: diferencial de descanso, fatiamento em blocos,
bootstrap pareado e registro de trial nova (com atestado)."""

import json
import random
from datetime import date, timedelta

import pytest

from brasileirao_predictor import db
from brasileirao_predictor.ingest import load_config as _real_load_config
from brasileirao_scripts import h10_fadiga_walkforward as h10

TEAMS = ["Alfa", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot"]


def _synthetic_rows(n_games: int, *, seed: int = 7, start: date = date(2024, 1, 1)) -> list[tuple]:
    rng = random.Random(seed)
    rows = []
    seen: set[tuple[str, str, str]] = set()
    d = start
    i = 0
    while i < n_games:
        home, away = rng.sample(TEAMS, 2)
        key = (d.isoformat(), home, away)
        if key in seen:
            d += timedelta(days=1)
            continue
        seen.add(key)
        hs, aws = rng.randint(0, 3), rng.randint(0, 3)
        rows.append((d.isoformat(), home, away, hs, aws, "Brasileirão Série A", 0))
        i += 1
        if i % 3 == 0:  # agrupa jogos em "rodadas" de ~3, datas avançam devagar
            d += timedelta(days=1)
    return rows


def _cfg(block_games: int, *, database: str = "unused") -> dict:
    # reaproveita o config.yaml real (elo/model completos) e só troca o que
    # o teste precisa controlar — evita reinventar (e esquecer) chaves que
    # ratings.compute_ratings/fit_goal_model exigem.
    cfg = _real_load_config()
    cfg = {**cfg, "database": database}
    cfg["model"] = {**cfg["model"], "calibration_window_years": 10}
    cfg["backtest"] = {**cfg.get("backtest", {}), "walk_forward_window_rounds": block_games // h10.GAMES_PER_ROUND or 1}
    return cfg


def test_rest_days_diff_debut_and_cap_and_sign():
    rows = [
        ("2026-01-01", "A", "B", 1, 0, "T", 0),
        ("2026-01-03", "A", "C", 1, 0, "T", 0),  # A jogou ha 2 dias; C estreia
        ("2026-01-20", "A", "B", 1, 0, "T", 0),  # A descansou 17d (capado), B tambem
    ]
    diffs = h10.rest_days_diff(rows)
    assert diffs[0] == pytest.approx(h10.CAP_DAYS - h10.CAP_DAYS)  # ambos estreiam
    assert diffs[1] == pytest.approx(2.0 - h10.CAP_DAYS)  # A com 2d de descanso vs C estreante (CAP)
    assert diffs[2] == pytest.approx(0.0)  # ambos descansaram >= CAP -> diferenca zero


def test_outcome_index():
    assert h10.outcome_index(2, 1) == 0
    assert h10.outcome_index(1, 1) == 1
    assert h10.outcome_index(0, 2) == 2


def test_run_walkforward_produces_paired_series_of_equal_length(monkeypatch):
    monkeypatch.setattr(h10, "MIN_CAL_GAMES", 10)
    block_games = 15
    rows = _synthetic_rows(45)
    rest = h10.rest_days_diff(rows)
    cfg = _cfg(block_games)
    result = h10.run_walkforward(cfg, rows, rest, block_games)
    assert result["n"] == 30  # 2 blocos avaliados de 15 jogos
    assert result["n_blocks_used"] == 2
    assert len(result["rps_base"]) == len(result["rps_fadiga"]) == result["n"]
    assert all(0.0 <= v <= 2.0 for v in result["rps_base"] + result["rps_fadiga"])


def test_run_walkforward_exits_when_base_too_small(monkeypatch):
    rows = _synthetic_rows(10)
    with pytest.raises(SystemExit):
        h10.run_walkforward(_cfg(15), rows, h10.rest_days_diff(rows), 15)


def test_paired_bootstrap_gain_tight_ci_around_constant_gain():
    rps_base = [0.5] * 40
    rps_fadiga = [0.4] * 40  # ganho constante de 0.1 em todo jogo
    mean_gain, lo, hi = h10.paired_bootstrap_gain(rps_base, rps_fadiga)
    assert mean_gain == pytest.approx(0.1)
    assert lo == pytest.approx(0.1, abs=1e-9)
    assert hi == pytest.approx(0.1, abs=1e-9)


def test_main_registers_a_new_trial_with_attestation(tmp_path, monkeypatch):
    dbpath = tmp_path / "t.db"
    conn = db.connect(str(dbpath))
    for d, home, away, hs, aws, tour, neutral in _synthetic_rows(60):
        conn.execute(
            "INSERT INTO matches (date, home_team, away_team, home_score, away_score, tournament, neutral) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (d, home, away, hs, aws, tour, neutral),
        )
    conn.commit()
    conn.close()

    trials_path = tmp_path / "trials.json"
    trials_path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(h10, "TRIALS", trials_path)
    monkeypatch.setattr(h10, "MIN_CAL_GAMES", 10)
    # cfg["database"] absoluto -> `ROOT / cfg["database"]` resolve pro proprio
    # absoluto (pathlib descarta o lado esquerdo do "/" quando o direito e'
    # absoluto), sem precisar mockar db.connect.
    monkeypatch.setattr(h10, "load_config", lambda: _cfg(20, database=str(dbpath)))
    monkeypatch.setattr("sys.argv", ["h10_fadiga_walkforward.py", "--cutoff", "2026-12-31"])

    exit_code = h10.main()
    assert exit_code == 0

    trials = json.loads(trials_path.read_text(encoding="utf-8"))
    assert len(trials) == 1
    trial = trials[0]
    assert trial["name"] == h10.TRIAL_NAME
    assert trial["metric"] == "rps"
    assert trial["status"] in ("comprovada", "refutada")
    assert trial["params"]["feature"] == "rest_days_diff_capped"

    # rodar de novo com os MESMOS params atualiza (nao levanta ValueError de N+1)
    exit_code_2 = h10.main()
    assert exit_code_2 == 0
    trials_again = json.loads(trials_path.read_text(encoding="utf-8"))
    assert len(trials_again) == 1  # update, nao trial nova
