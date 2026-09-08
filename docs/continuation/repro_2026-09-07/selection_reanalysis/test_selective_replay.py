"""Adversarial tests on synthetic events only; never load historical results."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

import selective_replay as replay


@pytest.fixture
def plan():
    result = json.loads(Path(__file__).with_name("analysis_plan.json").read_text(encoding="utf-8"))
    result["calibration"]["min_games_per_market"] = 3
    result["bootstrap"]["replicates"] = 64
    return result


def synthetic(event_id, kickoff, goals=(2, 0), *, probability=0.60):
    stamp = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
    decision = stamp - timedelta(hours=1)
    event = {
        "event_id": event_id,
        "date": stamp.date().isoformat(),
        "kickoff": stamp.isoformat(),
        "result": {"home_goals": goals[0], "away_goals": goals[1]},
        "odds": {"1x2": [2.0, 3.6, 4.0], "ou25": [1.9, 2.0], "btts": [1.9, 2.0]},
    }
    forecast = {
        "event_id": event_id,
        "decision_at": decision.isoformat(),
        "training_cutoff_at": (decision - timedelta(hours=48)).isoformat(),
        "p_1x2": [0.5, 0.26, 0.24],
        "p_over25": probability,
        "p_btts": 0.4,
    }
    return event, forecast


def sample():
    return [
        synthetic("past-1", "2022-12-01T18:00:00+00:00", (2, 0), probability=0.45),
        synthetic("past-2", "2022-12-05T18:00:00+00:00", (0, 0), probability=0.35),
        synthetic("past-3", "2022-12-10T18:00:00+00:00", (0, 3), probability=0.65),
        synthetic("decision-1", "2023-01-10T18:00:00+00:00", (2, 0)),
        synthetic("decision-2", "2023-01-25T18:00:00+00:00", (1, 2)),
        synthetic("future", "2024-08-20T18:00:00+00:00", (4, 1)),
    ]


def prepare(pairs, plan):
    return replay.prepare_rows([e for e, _ in pairs], [f for _, f in pairs], plan)[0]


def picks_of(decisions, event_id):
    return {d["policy"]: d["pick"] for d in decisions if d["event_id"] == event_id}


def test_calibration_excludes_cutoff_equality_and_later_results(plan):
    pairs = sample()
    cutoff = datetime(2023, 1, 8, 17, tzinfo=timezone.utc)
    pairs += [synthetic("at-cutoff", cutoff.isoformat(), (99, 0))]
    pairs += [synthetic("after-cutoff", (cutoff + timedelta(seconds=1)).isoformat(), (0, 99))]
    fits = replay.fit_calibration(prepare(pairs, plan), cutoff, minimum=3)
    for fit in fits.values():
        assert fit["n"] == 3
        assert fit["status"] == "OK"
        assert replay.dt(fit["latest_training_kickoff"]) < cutoff


def test_future_result_and_price_mutations_do_not_change_prior_picks(plan):
    pairs = sample()
    cutoff = datetime(2023, 1, 8, 17, tzinfo=timezone.utc)
    pairs += [synthetic("at-cutoff", cutoff.isoformat(), (1, 1))]
    baseline, base_fits = replay.run_decisions(prepare(pairs, plan), plan)
    changed = copy.deepcopy(pairs)
    for event, forecast in changed:
        if replay.dt(event["kickoff"]) >= cutoff:
            event["result"] = {"home_goals": 8, "away_goals": 7}
        if event["event_id"] == "future":
            event["odds"] = {"1x2": [1.5, 4.0, 6.0], "ou25": [2.0, 1.9], "btts": [2.0, 1.9]}
            forecast["p_over25"] = 0.12
    mutated, changed_fits = replay.run_decisions(prepare(changed, plan), plan)
    assert picks_of(baseline, "decision-1") == picks_of(mutated, "decision-1")
    # Both decisions are in January: the calibration remains frozen all month.
    assert picks_of(baseline, "decision-2") == picks_of(mutated, "decision-2")
    assert base_fits[0] == changed_fits[0]


def test_same_kickoff_input_order_does_not_change_decisions(plan):
    pairs = sample() + [synthetic("same-time", "2023-01-10T18:00:00+00:00", (0, 3))]
    first, fits_first = replay.run_decisions(prepare(pairs, plan), plan)
    second, fits_second = replay.run_decisions(prepare(list(reversed(pairs)), plan), plan)
    assert first == second
    assert fits_first == fits_second


@pytest.mark.parametrize("bad", [None, [], [1.9], [1.9, None], [True, 2], [float("nan"), 2], [float("inf"), 2], [1.0, 2], [51.0, 1.002], [5.0, 5.0], [1.2, 1.2], ["bad", 2]])
def test_incomplete_or_invalid_odds_reject_only_affected_market(plan, bad):
    pair = synthetic("target", "2023-01-10T18:00:00+00:00")
    pair[0]["odds"]["ou25"] = bad
    rows = prepare([pair], plan)
    assert "ou25" not in rows[0]["markets"]
    assert set(rows[0]["markets"]) == {"1x2", "btts"}


@pytest.mark.parametrize("bad", [[0.6, 0.4], [0.6, 0.4, 0.1], [-0.1, 0.5, 0.6], [float("nan"), 0.5, 0.5], [float("inf"), 0.0, 0.0]])
def test_invalid_probability_vectors_fail_closed(bad):
    with pytest.raises(ValueError):
        replay.validate_probabilities(bad, 3)


def test_calibration_preserves_joint_simplex_and_complements(plan):
    rows = prepare(sample(), plan)
    target = next(r for r in rows if r["event_id"] == "decision-1")
    fits = replay.fit_calibration(rows, target["cutoff"], minimum=3)
    for market, data in target["markets"].items():
        p = replay.corrected(data["p"], data["q"], fits[market])
        assert p is not None
        assert len(p) == (3 if market == "1x2" else 2)
        assert np.isfinite(p).all()
        assert np.all((p >= 0) & (p <= 1))
        assert np.isclose(p.sum(), 1, atol=1e-12, rtol=0)


def test_insufficient_calibration_cannot_emit_calibrated_pick(plan):
    rows = prepare(sample(), plan)
    target = next(r for r in rows if r["event_id"] == "decision-1")
    fits = replay.fit_calibration(rows, target["cutoff"], minimum=4)
    assert all(fit["status"] == "INSUFFICIENT_HISTORY" for fit in fits.values())
    assert replay.choose(target, "calibrated_residual", fits, plan) is None
    assert replay.choose(target, "learned_market_blend", fits, plan) is None


def test_maximum_one_pick_and_deterministic_tie_break(plan):
    row = {"event_id": "tie", "markets": {
        "ou25": {"p": np.array([0.8, 0.2]), "q": np.array([0.5, 0.5]), "odds": np.array([1.9, 1.9])},
        "btts": {"p": np.array([0.8, 0.2]), "q": np.array([0.5, 0.5]), "odds": np.array([1.9, 1.9])},
    }}
    pick = replay.choose(row, "confidence_70", {}, plan)
    assert pick["market"] == "btts"
    assert pick["selection"] == 0
    decisions, _ = replay.run_decisions(prepare(sample(), plan), plan)
    keys = [(d["event_id"], d["policy"]) for d in decisions]
    assert len(keys) == len(set(keys))
    assert all(d["stake_units"] in (0, 1) for d in decisions)


def test_confidence_filter_does_not_claim_positive_ev(plan):
    row = {"event_id": "favorite", "markets": {"1x2": {
        "p": np.array([0.7, 0.2, 0.1]), "q": np.array([0.75, 0.15, 0.1]), "odds": np.array([1.3, 5.0, 8.0])}}}
    pick = replay.choose(row, "confidence_70", {}, plan)
    assert pick["estimated_net_ev"] == pytest.approx(-0.11)
    assert replay.choose(row, "raw_ev", {}, plan) is None


def test_pnl_cost_and_fixed_decision_stress_monotonicity(plan):
    decisions, _ = replay.run_decisions(prepare(sample(), plan), plan)
    for decision in decisions:
        if decision["pick"] is not None:
            assert decision["pnl_units"] == pytest.approx(decision["won"] * decision["pick"]["odds"] - 1 - plan["additional_cost_per_unit"])
    summaries = replay.summarize(decisions, plan)
    for entry in summaries.values():
        stresses = entry["stress_fixed_decisions_no_reselection"]
        lookup = {(s["additional_cost"], s["odds_reduction"]): s["profit_units"] for s in stresses}
        assert lookup[(0.02, 0.0)] == pytest.approx(entry["overall"]["profit_units"])
        assert lookup[(0.05, 0.0)] <= lookup[(0.02, 0.0)] + 1e-12
        assert lookup[(0.02, 0.03)] <= lookup[(0.02, 0.01)] + 1e-12


def test_no_bet_has_zero_profit_undefined_roi_and_interval(plan):
    decisions, _ = replay.run_decisions(prepare(sample(), plan), plan)
    summary = replay.summarize(decisions, plan)["no_bet"]["overall"]
    assert summary["bets"] == 0
    assert summary["profit_units"] == 0
    assert summary["roi"] is None
    assert summary["hit_rate"] is None
    assert summary["roi_ci95_descriptive"] is None


def test_sparse_bets_cannot_have_degenerate_confidence_interval(plan):
    tiny = copy.deepcopy(plan)
    tiny["policies"] = ["confidence_60"]
    rows = prepare([synthetic("only", "2023-01-10T18:00:00+00:00")], tiny)
    decisions, _ = replay.run_decisions(rows, tiny)
    assert replay.bootstrap(decisions, tiny)["confidence_60"]["roi_ci95_descriptive"] is None


def test_bootstrap_preserves_paired_arms_and_empty_calendar_weeks(plan):
    paired_plan = copy.deepcopy(plan)
    paired_plan["policies"] = ["arm_a", "arm_b"]
    decisions = []
    monday = datetime(2023, 1, 2, 12, tzinfo=timezone.utc)
    # Four inactive weeks must remain part of the calendar, not disappear.
    for week in [*range(6), *range(10, 16)]:
        for game in range(4):
            timestamp = monday + timedelta(weeks=week, hours=game)
            pnl = 0.9 if (week + game) % 3 == 0 else -1.1
            for policy, profit in (("arm_a", pnl), ("arm_b", -pnl - 0.2)):
                decisions.append({"event_id": f"{week}-{game}", "decision_at": timestamp.isoformat(), "policy": policy, "pnl_units": profit, "stake_units": 1})
    result = replay.bootstrap(decisions, paired_plan)
    assert result["arm_a"]["calendar_weeks"] == 16
    assert result["arm_a"]["active_weeks"] == 12
    a_low, a_high = result["arm_a"]["roi_ci95_descriptive"]
    b_low, b_high = result["arm_b"]["roi_ci95_descriptive"]
    assert b_low == pytest.approx(-a_high - 0.2)
    assert b_high == pytest.approx(-a_low - 0.2)
    assert replay.bootstrap(list(reversed(decisions)), paired_plan) == result


def test_yearly_accounting_uses_decision_year_and_reconciles(plan):
    pairs = sample()[:3]
    new_year = synthetic("new-year", "2023-01-01T02:00:00+00:00")
    # The admitted source date discrepancy must not omit this decision.
    new_year[0]["date"] = "2022-12-31"
    pairs.append(new_year)
    annual_plan = copy.deepcopy(plan)
    annual_plan["decision_evaluation_years"] = [2023]
    decisions, _ = replay.run_decisions(prepare(pairs, annual_plan), annual_plan)
    for entry in replay.summarize(decisions, annual_plan).values():
        assert sum(year["events"] for year in entry["by_year"].values()) == entry["overall"]["events"]
        assert sum(year["profit_units"] for year in entry["by_year"].values()) == pytest.approx(entry["overall"]["profit_units"])


@pytest.mark.parametrize("timestamp", ["2023-01-10T18:00:00", "2023-01-10"])
def test_naive_timestamps_are_rejected(timestamp):
    with pytest.raises(ValueError):
        replay.dt(timestamp)


def test_future_training_cutoff_rejected(plan):
    pair = synthetic("target", "2023-01-10T18:00:00+00:00")
    pair[1]["training_cutoff_at"] = "2023-01-08T17:00:01+00:00"
    with pytest.raises(ValueError):
        prepare([pair], plan)


def test_duplicate_events_and_forecasts_rejected(plan):
    event, forecast = synthetic("duplicate", "2023-01-10T18:00:00+00:00")
    with pytest.raises(ValueError):
        replay.prepare_rows([event, event], [forecast], plan)
    with pytest.raises(ValueError):
        replay.prepare_rows([event], [forecast, forecast], plan)


def test_2026_kickoff_cannot_be_hidden_by_date_field(plan):
    pair = synthetic("forbidden", "2026-01-01T18:00:00+00:00")
    pair[0]["date"] = "2025-12-31"
    with pytest.raises(ValueError):
        prepare([pair], plan)


def test_large_date_kickoff_mismatch_rejected(plan):
    pair = synthetic("mismatch", "2023-01-10T18:00:00+00:00")
    pair[0]["date"] = "2023-01-01"
    with pytest.raises(ValueError):
        prepare([pair], plan)


@pytest.mark.parametrize("goals", [True, -1, 0.5, None, "2"])
def test_invalid_goal_labels_fail_closed(plan, goals):
    pair = synthetic("invalid-goal", "2023-01-10T18:00:00+00:00")
    pair[0]["result"]["home_goals"] = goals
    with pytest.raises(ValueError):
        prepare([pair], plan)
