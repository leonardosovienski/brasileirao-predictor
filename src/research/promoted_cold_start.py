"""Pre-registered-style contracts for a future promoted-team cold-start trial."""

from dataclasses import dataclass
from statistics import mean

import numpy as np
from predictor_core.measurement.metrics import brier, log_loss, rps

from src.data.promotions import Promotion


@dataclass(frozen=True)
class PromotedEntry:
    season: int
    team_id: str
    prior_seasons_absent: int
    entry_rating_estimate: float
    provenance: str


def build_entries(
    promotions: list[Promotion],
    entry_ratings: dict[tuple[int, str], float],
    *,
    as_of_season: int,
    participation_seasons: dict[str, set[int]] | None = None,
) -> list[PromotedEntry]:
    """Join point-in-time entry ratings; never infer a missing rating as zero."""
    prior_seasons: dict[str, list[int]] = {}
    entries: list[PromotedEntry] = []
    for promotion in sorted(promotions, key=lambda item: (item.serie_a_season, item.position)):
        if promotion.serie_a_season > as_of_season:
            continue
        key = (promotion.serie_a_season, promotion.team_id)
        if key not in entry_ratings:
            raise ValueError(f"missing point-in-time entry rating: {key}")
        if participation_seasons is None or promotion.team_id not in participation_seasons:
            raise ValueError(f"missing Serie A participation history: {promotion.team_id}")
        past = [season for season in participation_seasons[promotion.team_id] if season < promotion.serie_a_season]
        absent = promotion.serie_a_season - max(past) - 1 if past else promotion.serie_a_season - 2017
        entries.append(
            PromotedEntry(
                season=promotion.serie_a_season,
                team_id=promotion.team_id,
                prior_seasons_absent=max(0, absent),
                entry_rating_estimate=float(entry_ratings[key]),
                provenance=f"{promotion.source_url}#point-in-time-rating",
            )
        )
        prior_seasons.setdefault(promotion.team_id, []).append(promotion.serie_a_season)
    validate_entries(entries)
    return entries


def validate_entries(entries: list[PromotedEntry], *, minimum_training_seasons: int = 3) -> None:
    if not entries:
        raise ValueError("promoted cold-start trial requires explicit promotion metadata")
    seasons = {entry.season for entry in entries}
    if len(seasons) < minimum_training_seasons:
        raise ValueError(f"promoted cold-start trial requires at least {minimum_training_seasons} historical seasons")
    seen: set[tuple[int, str]] = set()
    for entry in entries:
        key = (entry.season, entry.team_id)
        if key in seen:
            raise ValueError(f"duplicate promoted entry: {key}")
        seen.add(key)
        if not entry.team_id or not entry.provenance:
            raise ValueError("promoted entries require canonical team_id and provenance")
        if entry.prior_seasons_absent < 0 or not 500 <= entry.entry_rating_estimate <= 2500:
            raise ValueError(f"invalid promoted entry: {key}")


def leave_one_season_out_priors(entries: list[PromotedEntry]) -> dict[int, float]:
    """Derive each season's empirical prior strictly from earlier seasons."""
    validate_entries(entries)
    out: dict[int, float] = {}
    for season in sorted({entry.season for entry in entries}):
        training = [entry.entry_rating_estimate for entry in entries if entry.season < season]
        if training:
            out[season] = mean(training)
    if not out:
        raise ValueError("no season has strictly earlier promoted-team training data")
    return out


def protocol_status(entries: list[PromotedEntry]) -> dict[str, object]:
    try:
        priors = leave_one_season_out_priors(entries)
    except ValueError as exc:
        return {"status": "BLOCKED_MISSING_PROMOTION_METADATA", "reason": str(exc), "serving_changed": False}
    return {"status": "READY_FOR_PREQUENTIAL_BACKTEST", "season_priors": priors, "serving_changed": False}


def evaluate_empirical_prior(entries: list[PromotedEntry], *, baseline_rating: float = 1500.0) -> dict[str, object]:
    """Prequentially compare the historical promoted prior with the neutral Elo baseline."""
    priors = leave_one_season_out_priors(entries)
    paired: list[tuple[float, float]] = []
    for entry in entries:
        if entry.season not in priors:
            continue
        empirical_error = abs(priors[entry.season] - entry.entry_rating_estimate)
        baseline_error = abs(baseline_rating - entry.entry_rating_estimate)
        paired.append((empirical_error, baseline_error))
    if len(paired) < 8:
        return {"status": "BLOCKED_DATA", "n": len(paired), "serving_changed": False}
    empirical_mae = mean(item[0] for item in paired)
    baseline_mae = mean(item[1] for item in paired)
    return {
        "status": "GO_CANDIDATE" if empirical_mae < baseline_mae else "NO_GO",
        "n": len(paired),
        "empirical_mae": empirical_mae,
        "baseline_mae": baseline_mae,
        "mae_gain": baseline_mae - empirical_mae,
        "serving_changed": False,
    }


@dataclass(frozen=True)
class ColdStartMatch:
    season: int
    team_id: str
    match_number: int
    opponent_rating: float
    home: bool
    goals_for: int
    goals_against: int


def _probabilities(rating: float, match: ColdStartMatch, *, home_advantage: float, draw_rate: float) -> list[float]:
    advantage = home_advantage if match.home else -home_advantage
    win_share = 1.0 / (1.0 + 10 ** (-((rating + advantage) - match.opponent_rating) / 400.0))
    decisive = 1.0 - draw_rate
    return [decisive * (1.0 - win_share), draw_rate, decisive * win_share]


def evaluate_first_matches(
    entries: list[PromotedEntry],
    matches: list[ColdStartMatch],
    *,
    first_n: int = 10,
    baseline_rating: float = 1500.0,
    home_advantage: float = 65.0,
    draw_rate: float = 0.27,
    base_k: float = 20.0,
) -> dict[str, object]:
    """Prequential first-N comparison of neutral Elo versus empirical prior + dynamic K."""
    priors = leave_one_season_out_priors(entries)
    entry_keys = {(entry.season, entry.team_id) for entry in entries}
    selected = sorted(
        [match for match in matches if (match.season, match.team_id) in entry_keys and match.match_number <= first_n],
        key=lambda match: (match.season, match.match_number, match.team_id),
    )
    if len(selected) < 30:
        return {"status": "BLOCKED_DATA", "n": len(selected), "serving_changed": False}
    control_ratings: dict[tuple[int, str], float] = {}
    treatment_ratings: dict[tuple[int, str], float] = {}
    control_probs: list[list[float]] = []
    treatment_probs: list[list[float]] = []
    outcomes: list[int] = []
    for match in selected:
        key = (match.season, match.team_id)
        if match.season not in priors:
            continue
        control = control_ratings.setdefault(key, baseline_rating)
        treatment = treatment_ratings.setdefault(key, priors[match.season])
        control_probs.append(_probabilities(control, match, home_advantage=home_advantage, draw_rate=draw_rate))
        treatment_probs.append(_probabilities(treatment, match, home_advantage=home_advantage, draw_rate=draw_rate))
        outcome = 2 if match.goals_for > match.goals_against else 1 if match.goals_for == match.goals_against else 0
        outcomes.append(outcome)
        score = 1.0 if outcome == 2 else 0.5 if outcome == 1 else 0.0
        control_expectation = control_probs[-1][2] + 0.5 * control_probs[-1][1]
        treatment_expectation = treatment_probs[-1][2] + 0.5 * treatment_probs[-1][1]
        control_ratings[key] += base_k * (score - control_expectation)
        dynamic_k = base_k * (1.0 + max(0, first_n - match.match_number) / first_n)
        treatment_ratings[key] += dynamic_k * (score - treatment_expectation)
    if len(outcomes) < 30:
        return {"status": "BLOCKED_DATA", "n": len(outcomes), "serving_changed": False}
    metrics = {
        "rps_delta": rps(treatment_probs, outcomes) - rps(control_probs, outcomes),
        "brier_delta": brier(treatment_probs, outcomes) - brier(control_probs, outcomes),
        "log_loss_delta": log_loss(treatment_probs, outcomes) - log_loss(control_probs, outcomes),
    }
    finite = all(np.isfinite(value) for value in metrics.values())
    candidate = finite and metrics["rps_delta"] < 0 and metrics["log_loss_delta"] <= 0
    return {
        "status": "GO_CANDIDATE" if candidate else "NO_GO",
        "n": len(outcomes),
        "first_n": first_n,
        "metrics": metrics,
        "serving_changed": False,
    }
