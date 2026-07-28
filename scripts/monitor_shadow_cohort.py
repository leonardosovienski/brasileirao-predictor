"""Read-only daily operational view of the strict H3/H5 cohort.

Desde 2026-07-25 a coorte vigente é a de bookmaker NOMEADO
(`sombra_picks_pinnacle.jsonl`, trial `h3-ou25-sombra-pinnacle-2026`). Os
ledgers `sombra_picks.jsonl`/`sombra_results.jsonl` da coorte anterior ficam
disponíveis por `--legacy`: eles são `LEGACY_INCOMPLETE` por inteiro (odd do
agregado do Sofascore, sem bookmaker) e não contam para nenhum gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluate_shadow_cohort import ROOT, evaluate

COORTE = {
    "picks": ROOT / "data" / "sombra_picks_pinnacle.jsonl",
    "results": ROOT / "data" / "sombra_results_pinnacle.jsonl",
    "trial_id": "h3-ou25-sombra-pinnacle-2026",
    "cohort_start": "2026-07-25",
}
LEGADO = {
    "picks": ROOT / "data" / "sombra_picks.jsonl",
    "results": ROOT / "data" / "sombra_results.jsonl",
    "trial_id": "h3-ou25-sombra-2026",
    "cohort_start": "2026-07-22",
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--legacy", action="store_true",
                    help="lê a coorte anterior (agregado Sofascore), não a vigente")
    args = ap.parse_args(argv)
    alvo = LEGADO if args.legacy else COORTE

    report = evaluate(alvo["picks"], alvo["results"])
    counts, classes = report["counts"], report["classification"]
    monitor = {"schema_version": "shadow-cohort-monitor/v1",
               "trial_id": alvo["trial_id"],
               "model_version": "frozen; see data/trials.json",
               "cohort_start": alvo["cohort_start"],
               "odds_source": "sofascore-aggregate" if args.legacy else "the_odds_api:pinnacle",
               "emitted": counts["emitted"],
               "prospective_eligible": classes["PROSPECTIVE_ELIGIBLE"],
               "prospective_rejected": classes["PROSPECTIVE_REJECTED"],
               "matured_eligible": classes["MATURED_ELIGIBLE"],
               "legacy_incomplete": classes["LEGACY_INCOMPLETE"],
               "pending_closing": max(0, classes["PROSPECTIVE_ELIGIBLE"] - classes["MATURED_ELIGIBLE"]),
               "pending_result": max(0, classes["PROSPECTIVE_ELIGIBLE"] - classes["MATURED_ELIGIBLE"]),
               "remaining_to_100": max(0, 100 - classes["MATURED_ELIGIBLE"]),
               "rejections": report["rejections"], "dataset_hash": report["dataset_hash"],
               "verdict": report["verdict"]}
    print(json.dumps(monitor, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
