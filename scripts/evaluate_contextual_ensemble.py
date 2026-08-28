"""Run the experimental contextual ensemble from a versioned JSON dataset."""

import argparse
import json
from pathlib import Path

from src.research.contextual_ensemble import evaluate_contextual_ensemble


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/contextual_ensemble.json"))
    args = parser.parse_args()
    payload = json.loads(args.dataset.read_text(encoding="utf-8"))
    report = evaluate_contextual_ensemble(
        payload["rows"],
        minimum_train=int(payload["protocol_parameters"]["minimum_train"]),
        minimum_test=int(payload["protocol_parameters"]["minimum_test"]),
        minimum_context_coverage=float(payload["protocol_parameters"]["minimum_context_coverage"]),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 2 if report["status"] == "FAIL_NUMERIC" else 0


if __name__ == "__main__":
    raise SystemExit(main())
