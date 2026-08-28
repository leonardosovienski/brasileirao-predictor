import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from src.research.ou25_nested_replay import FilterParameters, _metrics, holm_adjust, nested_walk_forward, score_row


def _panel(n=520, seed=8):
    rng = np.random.default_rng(seed)
    base = datetime(2021, 1, 1, tzinfo=UTC)
    rows = []
    for i in range(n):
        p = float(np.clip(0.5 + 0.14 * np.sin(i / 23) + rng.normal(0, 0.025), 0.12, 0.88))
        market_p = float(np.clip(p + rng.normal(0, 0.04), 0.15, 0.85))
        margin = 1.05
        oo, ou = margin / market_p, margin / (1 - market_p)
        rows.append(
            {
                "event_id": str(i),
                "kickoff_at": (base + timedelta(days=i)).isoformat(),
                "season": str(2021 + i // 190),
                "p_over": p,
                "actual_over": int(rng.random() < p),
                "offered_odds_ou25": (oo, ou),
                "closing_odds_ou25": (oo * 0.99, ou * 0.99),
            }
        )
    return rows


def _configs():
    return [
        FilterParameters(edge, 0.5, 1.3, 3.5, side)
        for edge in (-0.20, -0.10, 0.0)
        for side in ("both", "over", "under")
    ]


def test_holm_is_monotone_and_not_below_raw():
    raw = {"a": 0.01, "b": 0.03, "c": 0.2}
    adjusted = holm_adjust(raw)
    assert all(adjusted[k] >= raw[k] for k in raw)
    assert adjusted["a"] <= adjusted["b"] <= adjusted["c"]


def test_outer_fold_has_strict_temporal_boundary_and_operational_caps():
    result = nested_walk_forward(_panel(), _configs(), minimum_train=260, block_size=65, seed=19)
    assert result["capital_enabled"] is False
    assert result["strength_cap_without_prospective_a1"] == 40
    assert result["contaminated_seasons"] == ["2024", "2025", "2026"]
    assert result["outer_folds"]
    assert all(f["train_max_kickoff"] < f["test_min_kickoff"] for f in result["outer_folds"])
    assert len(result["tested_combinations"]) == len(_configs()) * len(result["outer_folds"])
    assert all(p["indication_strength_0_100"] <= 40 for p in result["picks"])
    assert all(p["strength_cap_reason"] == "NO_PROSPECTIVE_A1_EVIDENCE" for p in result["picks"])
    json.dumps(result, allow_nan=False)


def test_future_labels_cannot_change_past_fold_selection():
    rows = _panel()
    original = nested_walk_forward(rows, _configs(), minimum_train=260, block_size=65, seed=22)
    changed = [dict(r) for r in rows]
    for row in changed[325:]:
        row["actual_over"] = 1 - row["actual_over"]
    mutated = nested_walk_forward(changed, _configs(), minimum_train=260, block_size=65, seed=22)
    assert original["outer_folds"][0]["selected_config_id"] == mutated["outer_folds"][0]["selected_config_id"]
    first_original = [p for p in original["picks"] if p["outer_fold"] == 1]
    first_mutated = [p for p in mutated["picks"] if p["outer_fold"] == 1]
    assert [p["event_id"] for p in first_original] == [p["event_id"] for p in first_mutated]


def test_replay_is_deterministic_across_repeated_simulations():
    one = nested_walk_forward(_panel(seed=44), _configs(), minimum_train=260, block_size=65, seed=99)
    two = nested_walk_forward(_panel(seed=44), _configs(), minimum_train=260, block_size=65, seed=99)
    one.pop("generated_at")
    two.pop("generated_at")
    assert one == two


def test_empty_and_singleton_metrics_do_not_claim_estimable_interval():
    assert _metrics([], seed=1)["roi_ci95_lower"] is None
    singleton = [{"profit": 1.0, "season": "2023", "side": "over", "odd": 2.0, "clv": None}]
    assert _metrics(singleton, seed=1)["roi_ci95_lower"] is None


def test_clv_uses_devigged_closing_pair():
    row = _panel(n=1)[0]
    row["p_over"] = 0.8
    row["offered_odds_ou25"] = (2.0, 1.8)
    row["closing_odds_ou25"] = (1.8, 2.0)
    params = FilterParameters(-1.0, 1.0, 1.1, 5.0, "over", 0.9, 0.0)
    pick = score_row(row, params, _panel(n=100), uncertainty_by_side={"over": 0.0, "under": 0.0})
    assert pick is not None
    close_over_probability = (1 / 1.8) / (1 / 1.8 + 1 / 2.0)
    assert pick["clv"] == pytest.approx(2.0 * close_over_probability - 1)
