"""Read-only daily operational view of the strict H3/H5 cohort."""
from __future__ import annotations

import json
from pathlib import Path

from evaluate_shadow_cohort import ROOT, evaluate


def main() -> int:
    report = evaluate(ROOT / "data" / "sombra_picks.jsonl", ROOT / "data" / "sombra_results.jsonl")
    counts, classes = report["counts"], report["classification"]
    monitor = {"schema_version": "shadow-cohort-monitor/v1", "trial_id": "h3-ou25-sombra-2026", "model_version": "frozen; see data/trials.json", "cohort_start": "2026-07-22", "emitted": counts["emitted"], "prospective_eligible": classes["PROSPECTIVE_ELIGIBLE"], "prospective_rejected": classes["PROSPECTIVE_REJECTED"], "matured_eligible": classes["MATURED_ELIGIBLE"], "legacy_incomplete": classes["LEGACY_INCOMPLETE"], "pending_closing": max(0, classes["PROSPECTIVE_ELIGIBLE"] - classes["MATURED_ELIGIBLE"]), "pending_result": max(0, classes["PROSPECTIVE_ELIGIBLE"] - classes["MATURED_ELIGIBLE"]), "remaining_to_100": max(0, 100 - classes["MATURED_ELIGIBLE"]), "rejections": report["rejections"], "dataset_hash": report["dataset_hash"], "verdict": report["verdict"]}
    print(json.dumps(monitor, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
