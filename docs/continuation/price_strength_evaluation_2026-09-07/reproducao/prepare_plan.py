"""Freeze one conditional historical comparison before computing any new score."""

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKUP = Path("C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07")
REPO = Path("C:/Users/Superleo13/projetos/brasileirao-predictor")
OUTPUT = HERE.parents[1] / "outputs/TESTE_XG_REAL"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=False)
    inputs = HERE / "inputs"
    inputs.mkdir(exist_ok=False)
    sources = {
        "history.json": BACKUP / "work/selection_reanalysis/historical_input.json",
        "baseline_2025.json": BACKUP
        / "work/new_split_backtest/run/forecasts_2025.json",
        "baseline_plan.json": BACKUP / "work/new_split_backtest/plan.json",
        "baseline_candidate.json": BACKUP
        / "work/new_split_backtest/run/candidate.json",
    }
    hashes = {}
    for name, source in sources.items():
        shutil.copy2(source, inputs / name)
        assert sha(source) == sha(inputs / name)
        hashes[name] = {"source_path": str(source), "sha256": sha(source)}
    accounting = BACKUP / "work/new_split_backtest/economics.py"
    shutil.copy2(accounting, HERE / "frozen_economics.py")
    # Inspect identity/time only to freeze the fixture universe; no metrics or payouts.
    history = json.loads((inputs / "history.json").read_text(encoding="utf-8"))
    fixtures = [
        {
            "event_id": str(row["event_id"]),
            "home": row["home"],
            "away": row["away"],
            "kickoff": row["kickoff"],
        }
        for row in history
        if datetime.fromisoformat(row["kickoff"]).year == 2025
    ]
    fixtures.sort(key=lambda row: (row["kickoff"], row["event_id"]))
    assert len(fixtures) == 380 and len({row["event_id"] for row in fixtures}) == 380
    config = {
        "window_matches": 5,
        "min_team_matches": 3,
        "half_life_days": 90.0,
        "prior_weight": 2.0,
        "prior_home_xg": 1.5,
        "prior_away_xg": 1.2,
        "min_calibration_matches": 20,
        "calibration_prior_exposure": 5.0,
        "calibration_lead_minutes": 60,
    }
    plan = {
        "study_id": "rolling-xg-2025-conditional48h-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "EXPLORATORY_CONDITIONAL_48H",
        "question": "Does the frozen rolling-xG candidate improve paired forecast losses and hypothetical net payout in explored 2025?",
        "reason_for_year": "2025 has historical xG and an existing raw comparator fitted only through 2024; selected before new scores.",
        "hypothesis": "Recent chance creation/concession and chronological rate calibration may add information to the old static model and market.",
        "candidate_config": config,
        "candidate_module_sha256": sha(
            REPO / "brasileirao_predictor/research/price_strength/dynamic_xg.py"
        ),
        "source_files": hashes,
        "frozen_accounting_sha256": sha(accounting),
        "warmup_years": [2021, 2022, 2023],
        "calibration_target_year": 2024,
        "calibration_cutoff": "2025-01-01T00:00:00+00:00",
        "evaluation_year": 2025,
        "evaluation_fixtures": fixtures,
        "availability_policy": "ASSUMED_48H_NOT_OBSERVED",
        "availability_rule": "Only prior kickoff + 48 hours < decision; decision = target kickoff - 60 minutes. No observed availability timestamps are created.",
        "assumed_stats_lag_hours": 48,
        "updates": "Rolling strengths update from eligible prior matches during calibration/evaluation; two rate scales fit once on eligible 2024 labels only.",
        "arms": [
            "xg_calibrated_primary",
            "xg_raw_diagnostic",
            "old_raw_frozen_2024",
            "market_proportional_devig",
        ],
        "baseline": "Existing raw forecasts_2025 from model fitted once on 2021-2024. Retrospectively generated; do not use its 2025-trained blend.",
        "panel": "One common intersection of eligible new raw/calibrated forecasts, old raw and all three complete valid quote markets; retain all 380 with exclusion reasons.",
        "primary_metrics": ["Brier per market", "log_loss per market"],
        "improvement_definition": "Report each paired mean delta. Uniform predictive improvement requires lower mean Brier in all three markets; otherwise report mixed/no improvement. No promotion.",
        "economic_policy": json.loads((inputs / "baseline_plan.json").read_text())[
            "selection"
        ],
        "accounting": {
            "stake_units": 1,
            "cost_units_every_bet": 0.02,
            "max_bets_per_event": 1,
            "compound": False,
            "meaning": "Hypothetical payments at retrospective aggregate odds, not executable or realized profit.",
        },
        "bootstrap": {
            "unit": "ISO calendar week of kickoff",
            "paired_complete_fixtures": True,
            "replicates": 2000,
            "seed": 20260907,
            "confidence": 0.95,
            "interpretation": "Descriptive; no correction for prior searches or estimation uncertainty.",
        },
        "cross_book_comparison": "NOT_EVALUATED: no admissible full-market simultaneous captured snapshots; closed price studies remain closed.",
        "previous_exploration": "Historical years already explored, including 2025 calibration of the earlier replay; not untouched holdout. Twelve-policy and 51-ID studies are not rerun.",
        "stop": "Run these frozen arms once, audit arithmetic and publish all outcomes including negative. No changes to year, lag, priors, windows, filters or calibration after scoring.",
        "execution_proven": False,
        "real_capital_enabled": False,
    }
    content = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (OUTPUT / "PLANO.json").write_bytes(content)
    (HERE / "plan.json").write_bytes(content)
    print(
        json.dumps(
            {
                "fixtures": len(fixtures),
                "plan_sha256": hashlib.sha256(content).hexdigest(),
                "plan_path": str(OUTPUT / "PLANO.json"),
                "scores_computed": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
