from datetime import UTC, datetime, timedelta, timezone
from itertools import product

import pytest
from split_policy import DECISION_LEAD_HOURS, eligibility_for_paper, role_for

FREEZE = datetime(2026, 9, 7, 18, 0, tzinfo=UTC)
FUTURE = FREEZE + timedelta(days=7)


@pytest.mark.parametrize("season", range(2021, 2025))
def test_earlier_seasons_are_training_even_without_round(season):
    assert role_for(season, None) == "train"


def test_2025_is_calibration():
    assert role_for(2025, None) == "calibration"


@pytest.mark.parametrize("round_number", range(1, 39))
def test_every_official_2026_round_has_exact_role(round_number):
    expected = "test_exploratory" if round_number <= 19 else "paper_betting"
    assert role_for(2026, round_number) == expected


@pytest.mark.parametrize("bad_round", [None, 0, -1, 39, 100, 19.0, "19", True])
def test_2026_round_cannot_be_missing_coerced_or_outside_calendar(bad_round):
    with pytest.raises(ValueError, match="official integer round"):
        role_for(2026, bad_round)


@pytest.mark.parametrize("season", [2020, 2027, 1900])
def test_unselected_seasons_remain_outside_scope(season):
    assert role_for(season, None) == "out_of_scope"


@pytest.mark.parametrize("season", [True, "2026", 2026.0, None])
def test_season_is_not_silently_coerced(season):
    with pytest.raises(TypeError):
        role_for(season, 20)


def test_delayed_round_19_in_september_remains_test():
    role = role_for(2026, 19)
    assert role == "test_exploratory"
    assert eligibility_for_paper(role, "2026-09-30T21:00:00Z", FREEZE, True, True, True) == "OUT_OF_SCOPE"


@pytest.mark.parametrize("role", ["train", "calibration", "test_exploratory", "out_of_scope"])
def test_nonpaper_roles_cannot_emit_a_signal(role):
    assert eligibility_for_paper(role, FUTURE, FREEZE, True, True, True) == "OUT_OF_SCOPE"


@pytest.mark.parametrize("gates", list(product([False, True], repeat=3)))
def test_future_game_requires_every_gate(gates):
    expected = "PAPER_SIGNAL" if all(gates) else "NO_BET"
    assert eligibility_for_paper("paper_betting", FUTURE, FREEZE, *gates) == expected


@pytest.mark.parametrize("offset_seconds", [-86400, -1, 0, 1800, 3600])
@pytest.mark.parametrize("gates", [(True, True, True), (False, False, False)])
def test_past_or_exact_freeze_decision_never_becomes_prospective(offset_seconds, gates):
    kickoff = FREEZE + timedelta(seconds=offset_seconds)
    assert eligibility_for_paper("paper_betting", kickoff, FREEZE, *gates) == "REPLAY_ONLY"


def test_decision_lead_matches_frozen_one_hour_contract():
    assert DECISION_LEAD_HOURS == 1


def test_first_second_after_decision_boundary_can_be_a_paper_signal():
    kickoff = FREEZE + timedelta(hours=1, seconds=1)
    assert eligibility_for_paper("paper_betting", kickoff, FREEZE, True, True, True) == "PAPER_SIGNAL"


def test_unknown_kickoff_stays_pending_instead_of_getting_an_invented_date():
    assert eligibility_for_paper("paper_betting", None, FREEZE, True, True, True) == "PENDING_KICKOFF"


def test_unknown_kickoff_stays_pending_even_without_an_eligible_model():
    assert eligibility_for_paper("paper_betting", None, FREEZE, False, False, False) == "PENDING_KICKOFF"


def test_timezone_equivalent_kickoff_is_not_a_future_game():
    kickoff = FREEZE.astimezone(timezone(timedelta(hours=-3)))
    assert eligibility_for_paper("paper_betting", kickoff, FREEZE.isoformat(), True, True, True) == "REPLAY_ONLY"


def test_offset_comparison_uses_instants_and_accepts_utc_z():
    assert eligibility_for_paper(
        "paper_betting", "2026-09-07T17:00:00-03:00", "2026-09-07T18:00:00Z", True, True, True
    ) == "PAPER_SIGNAL"


@pytest.mark.parametrize(
    "bad_time",
    [
        "2026-09-07",
        "2026-09-07T18:00:00",
        "",
        "garbage",
        datetime(2026, 9, 7),  # noqa: DTZ001 -- intentionally invalid input
    ],
)
@pytest.mark.parametrize("field", ["freeze", "kickoff"])
def test_naive_and_invalid_timestamps_are_rejected(bad_time, field):
    kickoff, freeze = (bad_time, FREEZE) if field == "kickoff" else (FUTURE, bad_time)
    with pytest.raises(ValueError):
        eligibility_for_paper("paper_betting", kickoff, freeze, True, True, True)


@pytest.mark.parametrize("bad_time", [0, 1788804000, None])
def test_invalid_freeze_types_are_rejected(bad_time):
    with pytest.raises(TypeError):
        eligibility_for_paper("paper_betting", FUTURE, bad_time, True, True, True)


@pytest.mark.parametrize("gate_index", range(3))
@pytest.mark.parametrize("bad_gate", [1, "False", None])
def test_truthy_nonbooleans_cannot_unlock_paper_signal(gate_index, bad_gate):
    gates = [True, True, True]
    gates[gate_index] = bad_gate
    with pytest.raises(TypeError):
        eligibility_for_paper("paper_betting", FUTURE, FREEZE, *gates)


def test_unknown_role_fails_closed():
    with pytest.raises(ValueError):
        eligibility_for_paper("real_betting", FUTURE, FREEZE, True, True, True)
