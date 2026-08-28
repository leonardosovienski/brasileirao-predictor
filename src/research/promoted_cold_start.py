"""Pre-registered-style contracts for a future promoted-team cold-start trial."""

from dataclasses import dataclass
from statistics import mean

from src.data.promotions import Promotion


@dataclass(frozen=True)
class PromotedEntry:
    season: int
    team_id: str
    prior_seasons_absent: int
    entry_rating_estimate: float
    provenance: str


def build_entries(
    promotions: list[Promotion], entry_ratings: dict[tuple[int, str], float], *, as_of_season: int
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
        past = prior_seasons.get(promotion.team_id, [])
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
