"""Regression for canonical match rows carrying a kickoff timestamp."""

import datetime
from unittest.mock import MagicMock, patch

from brasileirao_scripts import backtest_walkforward as w


def test_walkforward_preserves_kickoff_and_aligns_ratings() -> None:
    rows = []
    for i in range(400):
        day = (datetime.date(2021, 1, 1) + datetime.timedelta(days=i // 2)).isoformat()
        kickoff = day + ("T19:00:00Z" if i % 2 == 0 else "T17:00:00Z")
        rows.append((day, "A", "B", 1, 0, "Brasileirão", 0, kickoff))
    cfg = {
        "model": {"max_goals": 7, "goal_half_life_days": 120},
        "elo": {},
        "backtest": {"walk_forward_window_rounds": 19},
    }

    def compute_ratings(ordered_rows, _cfg):
        assert all(len(row) == 8 for row in ordered_rows)
        keys = w.ratings.temporal_keys(ordered_rows)
        assert keys == sorted(keys)
        return {}, [(1.0, 0.0) for _ in ordered_rows]

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
        patch.object(w.model, "fit_goal_model", return_value=object()),
        patch.object(w.model, "predict_match", return_value={"lambda_a": 1.0, "lambda_b": 1.0}) as predict,
    ):
        assert w.run_walkforward(cfg, conn) == ([], [], 2)
        assert predict.call_count == 210
