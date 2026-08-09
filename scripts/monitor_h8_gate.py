"""Monitor H8 evidence milestones without changing its frozen configuration."""

from __future__ import annotations

import json
import statistics as st
from pathlib import Path

from predictor_core.measurement.bootstrap import bootstrap_ci
from predictor_core.measurement.stats import probabilistic_sharpe_ratio
from predictor_core.measurement.trials import TrialRegistry

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "research" / "retest_2023_2025_train_2026_bets.jsonl"
TRIALS = ROOT / "data" / "trials.json"
MILESTONES = (100, 200, 300, 500)


def report() -> dict:
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    returns = [float(row["pnl"]) for row in rows]
    lo, hi, _ = bootstrap_ci(
        rows,
        lambda sample: st.mean(float(row["pnl"]) for row in sample),
        scheme="cluster",
        cluster_key=lambda row: row["event_id"],
        n_boot=5000,
        seed=13,
    )
    dsr = TrialRegistry(TRIALS).deflated_sharpe(returns)
    next_milestone = next((milestone for milestone in MILESTONES if len(rows) < milestone), None)
    largest = sorted(returns, reverse=True)[:5]
    output = {
        "trial": "h8-ou25-train-2023-2025-test-2026-observed",
        "status": "HISTORICAL_EXPLORATORY",
        "n": len(rows),
        "next_milestone": next_milestone,
        "remaining_to_milestone": max(0, next_milestone - len(rows)) if next_milestone else 0,
        "roi": st.mean(returns),
        "roi_ci95": [lo, hi],
        "psr": probabilistic_sharpe_ratio(returns),
        "dsr": dsr["dsr"],
        "dsr_trials": dsr["n_trials"],
        "top5_profit_share": sum(largest) / sum(returns) if sum(returns) > 0 else None,
        "executable_price_evidence": False,
        "prospective_clv_available": False,
        "verdict": "PENDING_PROSPECTIVE_REPLICATION",
        "capital_enabled": False,
    }
    return output


def main() -> None:
    print(json.dumps(report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
