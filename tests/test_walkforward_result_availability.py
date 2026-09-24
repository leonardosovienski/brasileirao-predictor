"""BR-F004 (walk-forward): a calibração de um bloco só usa resultado já disponível.

O corte antigo era por DATA UTC (`r[0] < first_date`): um jogo de 23:00Z do dia anterior
entrava na calibração do bloco que começa 00:30Z, com o placar final de um jogo que ainda
estava em andamento. O mesmo valia para a fração de gols do 1º tempo.
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

from brasileirao_scripts import backtest_walkforward as w


def _rows() -> list[tuple]:
    """Bloco 0 (burn-in, nunca testado) = 190 jogos; o bloco 1 começa 00:30Z do dia D.

    O último jogo do burn-in começa 23:00Z do dia D-1: em 00:30Z ele ainda está em andamento.
    Blocos têm 19 rodadas x 10 jogos = 190 e nunca partem uma data.
    """
    rows = []
    start = datetime.datetime(2021, 1, 1, 19, 0, tzinfo=datetime.UTC)
    for i in range(189):
        kickoff = start + datetime.timedelta(days=i)
        rows.append(
            (kickoff.date().isoformat(), f"T{i % 10}", f"T{(i + 3) % 10}", 1, 0, "Brasileirão", 0, kickoff.isoformat())
        )
    late = datetime.datetime(2021, 7, 19, 23, 0, tzinfo=datetime.UTC)
    rows.append((late.date().isoformat(), "IN_PROGRESS_H", "IN_PROGRESS_A", 9, 0, "Brasileirão", 0, late.isoformat()))
    first = datetime.datetime(2021, 7, 20, 0, 30, tzinfo=datetime.UTC)
    for i in range(200):
        kickoff = first + datetime.timedelta(days=i)
        rows.append(
            (kickoff.date().isoformat(), f"T{i % 10}", f"T{(i + 4) % 10}", 0, 0, "Brasileirão", 0, kickoff.isoformat())
        )
    return rows


def test_calibracao_do_bloco_exclui_jogo_em_andamento() -> None:
    rows = _rows()
    cfg = {
        "model": {"max_goals": 7, "goal_half_life_days": None, "calibration_window_years": 4},
        "elo": {},
        "backtest": {"walk_forward_window_rounds": 19},
    }
    fitted: list[list] = []

    def compute_ratings(ordered_rows, _cfg):
        return {}, [(0.0, row[3], row[4]) for row in ordered_rows]

    def fit_goal_model(history, sample_weights=None):
        fitted.append(list(history))
        return (0.0, 0.3, 0.1, 0.0)

    conn = MagicMock()
    conn.execute.return_value = []
    with (
        patch.object(w.db, "completed_matches_with_kickoff", return_value=rows),
        patch.object(w.ratings, "compute_ratings", side_effect=compute_ratings),
        patch.object(w, "_load_odds", return_value={"present": True}),
        patch.object(w, "_load_ext_index", return_value={}),
        patch.object(w, "_load_flat_markets", return_value={}),
        patch.object(w, "_load_lines", return_value={}),
        patch.object(w, "_find_odds", return_value=None),
        patch.object(w.model, "fit_goal_model", side_effect=fit_goal_model),
        patch.object(w.model, "predict_match", return_value={"lambda_a": 1.0, "lambda_b": 1.0}),
    ):
        w.run_walkforward(cfg, conn)
    assert fitted, "nenhum bloco calibrado"
    # Bloco 1 (primeiro kickoff 00:30Z): o jogo em andamento (9 x 0) não pode estar na calibração.
    assert (9, 0) not in {(h[1], h[2]) for h in fitted[0]}
    assert len(fitted[0]) == 189
    # Bloco 2: o mesmo jogo já terminou há meses e entra (a guarda não cobra pedágio à toa).
    assert (9, 0) in {(h[1], h[2]) for h in fitted[1]}


def test_fracao_do_primeiro_tempo_so_usa_resultado_disponivel() -> None:
    cut = datetime.datetime(2021, 7, 20, 0, 30, tzinfo=datetime.UTC)
    rows_ht = [
        (datetime.datetime(2021, 1, 1, 19, 0, tzinfo=datetime.UTC) + datetime.timedelta(days=i), 2, 1, 1, 0)
        for i in range(60)
    ]
    rows_ht.append((datetime.datetime(2021, 7, 19, 23, 0, tzinfo=datetime.UTC), 9, 0, 9, 0))
    frac, n = w._ht_fraction(rows_ht, cut)
    assert n == 60
    assert frac == 1 / 3
