"""Separate arithmetic implementation; does not import the research calculator."""

import hashlib
import json
import sys
from decimal import Decimal, getcontext
from pathlib import Path
from statistics import median


def main():
    input_path, output_dir, receipt = (Path(arg).resolve() for arg in sys.argv[1:4])
    raw = input_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != "14153f7cbb348e9eef22a8e1c438757b1ef482951e2576d4a8381d7928e8e142":
        raise ValueError("input_hash_mismatch")
    getcontext().prec = 45
    source = json.loads(raw, parse_float=Decimal)
    events = json.loads((output_dir / "events.json").read_bytes(), parse_float=Decimal)
    summary = json.loads((output_dir / "summary.json").read_bytes(), parse_float=Decimal)
    indexed = {str(row["event_id"]): row for row in source if row["date"].startswith("2025-")}
    if len(indexed) != len(events):
        raise AssertionError("universe_mismatch")
    hurdles = []
    equations = 0
    tolerance = Decimal("1e-12")
    for event in events:
        original = indexed[event["event_id"]]
        vector = original["odds"]["1x2"]
        if event["price_diagnostic"] is None:
            if all(
                isinstance(value, int | Decimal)
                and not isinstance(value, bool)
                and Decimal(value).is_finite()
                and value > 1
                for value in vector
            ):
                raise AssertionError("valid_price_omitted")
            continue
        prices = [Decimal(value) for value in vector]
        s = sum(1 / price for price in prices)
        hurdle = s * Decimal("1.02") - 1
        diagnostic = event["price_diagnostic"]
        if abs(hurdle - diagnostic["relative_price_uplift_to_break_even"]) > tolerance:
            raise AssertionError("hurdle_mismatch")
        if abs(1 / s - 1 - diagnostic["own_price_gross_ev"]) > tolerance:
            raise AssertionError("own_price_ev_mismatch")
        equations += 2
        for side, price in zip(("home", "draw", "away"), prices, strict=True):
            p = (1 / price) / s
            required = diagnostic["break_even_odds_scenario"][side]
            if abs(p * (required - 1) - (1 - p) - Decimal(".02")) > tolerance:
                raise AssertionError("win_loss_accounting_mismatch")
            equations += 1
        hurdles.append(hurdle)
    if len(hurdles) != summary["summary"]["numeric_complete_vectors"]:
        raise AssertionError("coverage_mismatch")
    if abs(median(hurdles) - summary["summary"]["relative_price_uplift_scenarios"]["0.02"]["median"]) > tolerance:
        raise AssertionError("median_mismatch")
    result = {
        "status": "PASS",
        "independence": "SEPARATE_IMPLEMENTATION_SAME_RESEARCHER",
        "arithmetic": "decimal_45_digits",
        "event_count": len(events),
        "valid_vectors": len(hurdles),
        "equations_checked": equations,
        "labels_used": False,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
