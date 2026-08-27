import pytest

from src.a1_recommendation import RecommendationInput, assess_recommendation


def candidate(**changes):
    values = {
        "event_probability": 0.55,
        "soft_odds": 2.0,
        "probability_uncertainty": 0.01,
        "friction_rate": 0.01,
        "data_quality": 1.0,
        "reference_complete": True,
        "soft_complete": True,
        "executable": True,
        "reference_stale": False,
    }
    values.update(changes)
    return RecommendationInput(**values)


def test_probability_and_indication_are_separate() -> None:
    result = assess_recommendation(candidate())
    assert result.outcome_probability_pct == 55.0
    assert result.indication_score == 10
    assert result.score_cap == 10
    assert result.action == "SHADOW_OBSERVE"
    assert result.capital_enabled is False


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"reference_complete": False}, "reference_incomplete"),
        ({"soft_complete": False}, "soft_market_incomplete"),
        ({"executable": False}, "not_executable"),
        ({"reference_stale": True}, "reference_stale"),
        ({"probability_uncertainty": 0.1}, "conservative_net_ev_not_positive"),
    ],
)
def test_hard_gates_force_no_bet(change, reason) -> None:
    result = assess_recommendation(candidate(**change))
    assert result.indication_score == 0
    assert result.action == "NO_BET"
    assert reason in result.reasons


def test_unconfirmed_shadow_cannot_look_like_ninety_percent() -> None:
    result = assess_recommendation(candidate(evidence_stage="SHADOW", event_probability=0.7, soft_odds=2.0))
    assert result.indication_score == 40
    assert result.score_cap == 40


def test_only_positive_clv_interval_can_reach_high_score() -> None:
    result = assess_recommendation(
        candidate(
            evidence_stage="CLV_CONFIRMED",
            clv_ci95_lower=0.01,
            event_probability=0.6,
            soft_odds=2.0,
            probability_uncertainty=0.01,
        )
    )
    assert result.indication_score == 100
    assert result.action == "SHADOW_CANDIDATE"


def test_claimed_confirmation_without_positive_clv_is_capped() -> None:
    result = assess_recommendation(candidate(evidence_stage="CLV_CONFIRMED", clv_ci95_lower=0.0))
    assert result.indication_score == 40
    assert "clv_ci95_lower_not_positive" in result.reasons


def test_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError):
        candidate(soft_odds=1.0)
