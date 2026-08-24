"""Métricas de coorte prospectiva e gate estritamente consultivo."""

from __future__ import annotations

import math
import random
import statistics as st
from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

from predictor_core.contracts import registry as registry_module
from predictor_core.measurement.stats import probabilistic_sharpe_ratio

from src.research.prospective_validation.contracts import PaperPick, PaperSettlement

CapitalGate = Literal["CAPITAL_GATE: LOCKED", "CAPITAL_GATE: ELIGIBLE_FOR_REVIEW"]


@dataclass(frozen=True)
class CohortPolicy:
    min_matured: int
    declared_trials: int
    historical_trial_sharpes: tuple[float | None, ...] = ()
    dsr_gate: float = 0.95
    bootstrap_iterations: int = 2000
    bootstrap_seed: int = 20260824

    def __post_init__(self) -> None:
        if self.min_matured < 1 or self.declared_trials < 1 or not 0 < self.dsr_gate <= 1:
            raise ValueError("invalid cohort policy")
        if self.bootstrap_iterations < 100:
            raise ValueError("bootstrap_iterations must be >= 100")


def required_sample_size(
    mean_odds: float, *, target_roi: float = 0.05, power: float = 0.80, alpha: float = 0.05
) -> int:
    """Amostra normal aproximada sob uma aposta binária com odd média informada."""
    if mean_odds <= 1 + target_roi or target_roi <= 0 or not 0 < power < 1 or not 0 < alpha < 1:
        raise ValueError("invalid power-analysis parameters")
    win_probability = (1 + target_roi) / mean_odds
    win_return, loss_return = mean_odds - 1, -1.0
    variance = win_probability * (win_return - target_roi) ** 2
    variance += (1 - win_probability) * (loss_return - target_roi) ** 2
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return math.ceil(z * z * variance / (target_roi * target_roi))


def _bootstrap_mean(values: list[float], iterations: int, seed: int) -> list[float] | None:
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    estimates = sorted(st.mean(rng.choices(values, k=len(values))) for _ in range(iterations))
    return [estimates[int(0.025 * iterations)], estimates[min(iterations - 1, int(0.975 * iterations))]]


def _calibration(rows: list[tuple[PaperPick, PaperSettlement]]) -> dict[str, float | int | None]:
    if not rows:
        return {"n": 0, "brier": None, "mean_predicted": None, "actual_rate": None}
    probabilities = [pick.model_probability for pick, _ in rows]
    outcomes = [float(settlement.won) for _, settlement in rows]
    return {
        "n": len(rows),
        "brier": st.mean((probability - outcome) ** 2 for probability, outcome in zip(probabilities, outcomes)),
        "mean_predicted": st.mean(probabilities),
        "actual_rate": st.mean(outcomes),
    }


def evaluate_cohort(
    picks: list[PaperPick], settlements: list[PaperSettlement], policy: CohortPolicy
) -> dict[str, object]:
    if len({pick.pick_id for pick in picks}) != len(picks):
        raise ValueError("duplicate pick_id in cohort")
    by_pick = {settlement.pick_id: settlement for settlement in settlements}
    matured = []
    for pick in picks:
        settlement = by_pick.get(pick.pick_id)
        if settlement is not None:
            settlement.assert_matches(pick)
            matured.append((pick, settlement))
    pnl = [pick.captured_odds - 1 if settlement.won else -1.0 for pick, settlement in matured]
    clv = [math.log(pick.captured_odds / settlement.closing_odds) for pick, settlement in matured]
    roi = st.mean(pnl) if pnl else None
    psr = probabilistic_sharpe_ratio(pnl, 0.0) if len(pnl) >= 2 else None
    denominator = list(policy.historical_trial_sharpes) + [None] * policy.declared_trials
    dsr_result = registry_module.deflated_sharpe_ratio(pnl, denominator) if len(pnl) >= 2 else None
    dsr = float(dsr_result["dsr"]) if dsr_result and math.isfinite(float(dsr_result["dsr"])) else None
    eligible = len(matured) >= policy.min_matured and dsr is not None and dsr >= policy.dsr_gate
    gate: CapitalGate = "CAPITAL_GATE: ELIGIBLE_FOR_REVIEW" if eligible else "CAPITAL_GATE: LOCKED"
    mean_odds = st.mean(pick.captured_odds for pick, _ in matured) if matured else None
    return {
        "schema_version": "prospective-validation/1",
        "scientific_state": "PAPER_TRADING_ONLY",
        "counts": {"emitted": len(picks), "matured": len(matured)},
        "coverage": len(matured) / len(picks) if picks else 0.0,
        "flat_stake_units": 1.0,
        "mean_log_clv": st.mean(clv) if clv else None,
        "roi": roi,
        "roi_bootstrap_ci95": _bootstrap_mean(pnl, policy.bootstrap_iterations, policy.bootstrap_seed),
        "calibration": _calibration(matured),
        "psr": float(psr) if psr is not None and math.isfinite(float(psr)) else None,
        "dsr": dsr,
        "dsr_gate": policy.dsr_gate,
        "mean_odds": mean_odds,
        "power_required_n": required_sample_size(mean_odds) if mean_odds and mean_odds > 1.05 else None,
        "capital_gate": gate,
        "capital_decision_authority": "HUMAN_REVIEW_OUTSIDE_CODE",
    }
