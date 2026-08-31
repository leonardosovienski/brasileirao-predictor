"""Initialize, verify and report the label-free A1 OU2.5 calibration phase."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from brasileirao_predictor.a1_phase0 import Phase0Ledger, clv_required_sample_size, phase0_report, policy_fingerprint

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "contracts" / "a1-ou25-phase0-policy.json"
RUNTIME = ROOT / "data" / "a1_phase0"
CODE_PATHS = [
    ROOT / "brasileirao_predictor" / "a1_phase0.py",
    ROOT / "brasileirao_predictor" / "collector_a1.py",
    ROOT / "brasileirao_scripts" / "collect_odds_a1.py",
    ROOT / "schemas" / "odds_snapshot_v1.json",
    ROOT / "data" / "team_aliases.json",
]


def _fingerprint() -> dict[str, object]:
    return policy_fingerprint(POLICY, CODE_PATHS)


def main() -> int:
    parser = argparse.ArgumentParser(description="A1 OU2.5 phase 0; no outcomes, no capital")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init", action="store_true")
    group.add_argument("--verify", action="store_true")
    group.add_argument("--report", action="store_true")
    group.add_argument("--clv-power", nargs=2, type=float, metavar=("PILOT_SD", "MIN_EFFECT"))
    args = parser.parse_args()
    fingerprint = _fingerprint()
    ledger = Phase0Ledger(
        RUNTIME / f"operational_observations-{str(fingerprint['fingerprint'])[:12]}.jsonl",
        str(fingerprint["fingerprint"]),
    )
    if args.init:
        RUNTIME.mkdir(parents=True, exist_ok=True)
        initialized = {**fingerprint, "initialized_at": datetime.now(UTC).isoformat().replace("+00:00", "Z")}
        (RUNTIME / "fingerprint.json").write_text(json.dumps(initialized, indent=2) + "\n", encoding="utf-8")
        output = {"status": "INITIALIZED_NOT_STARTED", **initialized, "capital_enabled": False}
    elif args.verify:
        output = {"status": "VERIFIED" if ledger.path.exists() and ledger.verify() else "NOT_STARTED", **fingerprint}
    elif args.clv_power:
        output = {"required_n": clv_required_sample_size(*args.clv_power), "metric": "mean_log_clv"}
    else:
        fingerprint_path = RUNTIME / "fingerprint.json"
        if not fingerprint_path.exists():
            parser.error("phase0 not initialized; run --init after review")
        initialized = json.loads(fingerprint_path.read_text(encoding="utf-8"))
        if initialized.get("fingerprint") != fingerprint["fingerprint"]:
            parser.error("phase0 fingerprint changed; re-review and reinitialize")
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        rows = []
        initialized_at = str(initialized["initialized_at"])
        for path in sorted((ROOT / "data" / "odds_snapshots").glob("*.jsonl")):
            rows.extend(
                row
                for line in path.read_text(encoding="utf-8").splitlines()
                if (row := json.loads(line))["captured_at"] >= initialized_at
            )
        output = phase0_report(rows, policy)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
