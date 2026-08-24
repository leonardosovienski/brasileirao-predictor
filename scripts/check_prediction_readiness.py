"""Validate a point-in-time prediction-readiness JSON document."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.prediction_protocol import assess_prediction_readiness


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    report = assess_prediction_readiness(json.loads(args.input.read_text(encoding="utf-8")))
    print(report.model_dump_json(indent=2))
    raise SystemExit(0 if report.ready else 2)


if __name__ == "__main__":
    main()
