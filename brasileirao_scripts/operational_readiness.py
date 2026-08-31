"""Print local A1 readiness without network calls or secret values."""

import json

from brasileirao_predictor.ingest import ROOT
from brasileirao_predictor.operational_readiness import assess_operational_readiness


def main() -> int:
    report = assess_operational_readiness(ROOT)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "READY_FOR_HUMAN_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
