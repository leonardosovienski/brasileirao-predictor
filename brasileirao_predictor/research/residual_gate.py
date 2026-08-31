"""Pre-registered-style economic gate for the residual shadow candidate."""

from __future__ import annotations

import statistics as st
from typing import Any

from predictor_core.measurement.bootstrap import bootstrap_ci
from predictor_core.measurement.stats import probabilistic_sharpe_ratio


def evaluate_economic_gate(
    settlements: list[dict[str, Any]],
    *,
    dsr: float,
    minimum_sample: int = 200,
    minimum_psr: float = 0.80,
    minimum_dsr: float = 0.95,
    n_boot: int = 2000,
) -> dict[str, Any]:
    complete = [
        row
        for row in settlements
        if isinstance(row.get("pnl"), (int, float))
        and isinstance(row.get("clv"), (int, float))
        and row.get("event_id") is not None
    ]
    if len(complete) < minimum_sample:
        return {
            "verdict": "PENDING_SAMPLE",
            "n": len(complete),
            "minimum_sample": minimum_sample,
            "capital_enabled": False,
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
    psr = probabilistic_sharpe_ratio(pnl, 0.0)
    passed = bool(
        roi_lo is not None
        and clv_lo is not None
        and roi_lo > 0
        and clv_lo > 0
        and psr >= minimum_psr
        and dsr >= minimum_dsr
    )
    return {
        "verdict": "GO_CANDIDATE" if passed else "NO_GO",
        "n": len(complete),
        "roi": st.mean(pnl),
        "roi_ci95": [roi_lo, roi_hi],
        "clv": st.mean(clv),
        "clv_ci95": [clv_lo, clv_hi],
        "psr": psr,
        "dsr": dsr,
        # A gate result is evidence for a human-controlled promotion. It never
        # turns real-money execution on by itself.
        "capital_enabled": False,
    }
