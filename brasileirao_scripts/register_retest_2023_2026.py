"""Record the already-observed 2023-2025 train / 2026 OOS attempt.

This is registration in the immortal multiple-testing denominator, not a
retrospective pre-registration. The result was observed on 2026-08-09.
"""

from __future__ import annotations

import json
from pathlib import Path

from predictor_core.measurement.trials import TrialRegistry, attestation_path_for
from predictor_core.testing.harness import attest_pipeline_power

from brasileirao_predictor.ingest import load_config
from brasileirao_scripts.governanca import _make_series, evaluate_funnel

ROOT = Path(__file__).resolve().parent.parent
TRIALS = ROOT / "data" / "trials.json"
RESULT = ROOT.parent.parent / "outputs" / "RETEST_2023_2025_TRAIN_2026_TEST.json"
NAME = "h8-ou25-train-2023-2025-test-2026-observed"


def main() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    registry = TrialRegistry(TRIALS)
    cfg = load_config()
    params = tuple(result["params"])

    def edge_generator():
        return _make_series(params, cfg, inflated=True, seed=13)

    def noise_generator():
        return _make_series(params, cfg, inflated=False, seed=14)

    attestation = attest_pipeline_power(
        evaluate_funnel,
        edge_generator,
        noise_generator,
        attestation_path=attestation_path_for(TRIALS),
        metric="psr",
        note="H8 O/U 2.5 fixed 2-15% funnel; synthetic sensitivity/specificity before registry write",
    )
    registry.register(
        NAME,
        params={
            "market": "ou25",
            "min_edge": 0.02,
            "max_edge": 0.15,
            "stake": "fixed-1u-shadow",
            "train_seasons": ["2023", "2024", "2025"],
            "test_season": "2026",
            "price_definition": "sofascore-postgame-close-approximation",
            "model": "elo+negative-binomial+dixon-coles",
            "capital_enabled": False,
        },
        sharpe=float(result["sharpe_per_bet"]),
        notes=(
            "OBSERVED BEFORE REGISTRATION on 2026-08-09; exploratory evidence only. "
            f"n={result['bets']}, ROI={result['roi']:.6f}, PSR={result['psr']:.6f}, "
            f"ROI_CI95={result['roi_ci95']}. The 2026 outcomes were not used to fit model "
            "parameters, but this record cannot become confirmatory retroactively. Prices are "
            "Sofascore postgame closing approximations, not proven executable quotes."
        ),
        test_period=["2026-01-01", "2026-08-09"],
        metric="psr",
        pipeline_fingerprint=attestation["pipeline_fingerprint"],
    )
    errors = registry.validate()
    if errors:
        raise SystemExit("invalid trial registry: " + "; ".join(errors))
    dsr = registry.deflated_sharpe(
        [
            json.loads(line)["pnl"]
            for line in (ROOT / "data" / "research" / "retest_2023_2025_train_2026_bets.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
    )
    print(json.dumps({"trial": NAME, **dsr}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
