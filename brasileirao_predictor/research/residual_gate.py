"""Descriptive unit-stake shadow gate; provenance and execution remain unverified."""

from __future__ import annotations

import math
import statistics as st
from numbers import Integral, Real
from typing import Any

from predictor_core.measurement.bootstrap import bootstrap_ci
from predictor_core.measurement.stats import probabilistic_sharpe_ratio


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _probability(value: Any, name: str) -> float:
    result = _finite_number(value, name)
    if not 0 <= result <= 1:
        raise ValueError(f"{name} must be in [0, 1]")
    return result


def evaluate_economic_gate(
    settlements: list[dict[str, Any]],
    *,
    dsr: float,
    minimum_sample: int = 200,
    minimum_psr: float = 0.80,
    minimum_dsr: float = 0.95,
    n_boot: int = 2000,
) -> dict[str, Any]:
    dsr = _probability(dsr, "dsr")
    minimum_psr = _probability(minimum_psr, "minimum_psr")
    minimum_dsr = _probability(minimum_dsr, "minimum_dsr")
    for name, value in (("minimum_sample", minimum_sample), ("n_boot", n_boot)):
        if isinstance(value, bool) or not isinstance(value, Integral) or value < 2:
            raise ValueError(f"{name} must be an integer >= 2")
    if not isinstance(settlements, list):
        raise ValueError("settlements must be a list")
    complete = []
    for index, row in enumerate(settlements):
        if not isinstance(row, dict):
            raise ValueError(f"settlements[{index}] must be an object")
        event_id = row.get("event_id")
        if event_id is not None and (
            isinstance(event_id, bool)
            or not isinstance(event_id, (str, int))
            or (isinstance(event_id, str) and not event_id.strip())
        ):
            raise ValueError(f"settlements[{index}].event_id must be a nonblank string or integer")
        values = {}
        for field in ("pnl", "clv"):
            if row.get(field) is not None:
                values[field] = _finite_number(row[field], f"settlements[{index}].{field}")
        # This helper has no portfolio engine. Never ignore an explicit stake
        # that contradicts the historical unit-stake interpretation of `roi`.
        if "stake" in row and _finite_number(row["stake"], "unit stake") != 1.0:
            raise ValueError("residual gate requires unit stake; variable stakes need a portfolio evaluator")
        if len(values) == 2 and event_id is not None:
            complete.append({"event_id": event_id, **values})
    metadata = {
        "schema_version": "residual-shadow-gate/v2",
        "n": len(complete),
        "n_input": len(settlements),
        "n_incomplete": len(settlements) - len(complete),
        "minimum_sample": int(minimum_sample),
        "roi_scope": "mean_pnl_assuming_one_unit_staked_per_row",
        "dsr_source": "caller_declared_unverified",
        "psr_scope": "row_returns_without_cluster_dependence_adjustment",
        "provenance_verified": False,
        "economic_evidence": False,
        "capital_enabled": False,
    }
    if len(complete) != len(settlements) or len(complete) < minimum_sample:
        return {
            **metadata,
            "verdict": "PENDING_DATA" if len(complete) != len(settlements) else "PENDING_SAMPLE",
        }
    pnl = [float(row["pnl"]) for row in complete]
    clv = [float(row["clv"]) for row in complete]
    roi_lo, roi_hi, _ = bootstrap_ci(
        complete,
        lambda sample: st.mean(float(row["pnl"]) for row in sample),
        scheme="cluster",
        cluster_key=lambda row: row["event_id"],
        n_boot=n_boot,
        seed=13,
    )
    clv_lo, clv_hi, _ = bootstrap_ci(
        complete,
        lambda sample: st.mean(float(row["clv"]) for row in sample),
        scheme="cluster",
        cluster_key=lambda row: row["event_id"],
        n_boot=n_boot,
        seed=17,
    )
    raw_psr = probabilistic_sharpe_ratio(pnl, 0.0)
    psr = float(raw_psr) if raw_psr is not None and math.isfinite(raw_psr) else None
    passed = bool(
        roi_lo is not None
        and clv_lo is not None
        and roi_lo > 0
        and clv_lo > 0
        and psr is not None
        and psr >= minimum_psr
        and dsr >= minimum_dsr
    )
    return {
        **metadata,
        "verdict": "GO_CANDIDATE" if passed else "NO_GO",
        "roi": st.mean(pnl),
        "roi_ci95": [roi_lo, roi_hi],
        "clv": st.mean(clv),
        "clv_ci95": [clv_lo, clv_hi],
        "psr": psr,
        "dsr": dsr,
    }
