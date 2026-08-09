"""Evaluate frozen market-residual records; research only, never enables capital."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.research.residual_walkforward import evaluate_walkforward

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RECORDS = ROOT / "data" / "research" / "residual_records.jsonl"
DEFAULT_REPORT = ROOT / "data" / "research" / "residual_walkforward_report.json"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--minimum-train", type=int, default=200)
    parser.add_argument("--block-size", type=int, default=50)
    args = parser.parse_args()
    records = _load_jsonl(args.records)
    if len(records) <= args.minimum_train:
        report = {
            "status": "PENDING_SAMPLE",
            "n": len(records),
            "minimum_train": args.minimum_train,
            "capital_enabled": False,
        }
    else:
        report = evaluate_walkforward(
            records,
            minimum_train=args.minimum_train,
            block_size=args.block_size,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
