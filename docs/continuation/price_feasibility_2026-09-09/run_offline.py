"""Explicit hash-locked inputs; no database, provider, labels, or protected data.

Usage: python -I run_offline.py --repository PATH --input FILE --output NEW_DIR
The input is the one closed historical export identified before this study.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

INPUT_SHA256 = "14153f7cbb348e9eef22a8e1c438757b1ef482951e2576d4a8381d7928e8e142"
PROTOCOL_SHA256 = "f69d6aa1fbca0b64adabe0dd61cfddef409e3f47061c4baaedf9e203f46702e5"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    repository, input_path, output = (path.resolve() for path in (args.repository, args.input, args.output))
    if input_path.is_relative_to(repository) or output.is_relative_to(repository):
        raise ValueError("research_inputs_and_outputs_must_be_outside_repository")
    if output.exists() or input_path.is_relative_to(output):
        raise ValueError("output_must_be_new_and_separate_from_inputs")
    protocol_dir = repository / "docs/continuation/price_feasibility_2026-09-09"
    if _digest(protocol_dir / "PROTOCOL.md") != PROTOCOL_SHA256:
        raise ValueError("protocol_hash_mismatch")
    blob = input_path.read_bytes()
    if hashlib.sha256(blob).hexdigest() != INPUT_SHA256:
        raise ValueError("input_hash_mismatch")
    output.mkdir(parents=True)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repository))
    # Credential-free process state; do not enumerate or print inherited values.
    keep = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
    for name in list(os.environ):
        if name.upper() not in keep:
            del os.environ[name]

    def guard(event, parameters):
        if event.startswith(("socket.", "subprocess.", "os.system", "sqlite3.")):
            raise PermissionError("network_process_database_forbidden")
        if event == "open" and isinstance(parameters[0], str | bytes | os.PathLike):
            path = Path(os.fsdecode(parameters[0])).resolve()
            mode = parameters[1] or ""
            flags = parameters[2] or 0
            writing = any(char in mode for char in "wax+") or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)
            if writing and not path.is_relative_to(output):
                raise PermissionError("write_outside_output_forbidden")
            if path.is_relative_to(repository / "data") or path.name == ".env":
                raise PermissionError("operational_data_forbidden")

    sys.addaudithook(guard)
    from brasileirao_predictor.research.price_strength.price_hurdle import audit_legacy_2025
    from brasileirao_predictor.research.price_strength.quotes import PricePolicy, scan_quotes

    source = json.loads(blob)
    # Deliberately discard labels and other years before any economic operation.
    rows = [
        {key: value for key, value in row.items() if key != "result"}
        for row in source
        if str(row.get("date", "")).startswith("2025-")
    ]
    del source, blob
    report = audit_legacy_2025(rows)
    policy = PricePolicy(
        reference_books=("pinnacle",),
        max_age_seconds=120,
        max_skew_seconds=30,
        cost_per_unit=0.02,
        commission_on_profit=0.0,
        min_ev=0.0,
        max_ev=0.15,
    )
    scanner_rejections = []
    for row in rows:
        decision = datetime.fromisoformat(row["kickoff"]) - timedelta(minutes=60)
        # No fabricated bookmaker, status, timestamps, or normalized quote.
        scan = scan_quotes([row], as_of=decision, policy=policy)
        if not scan["batch_blocked"] or scan["selected_candidates"]:
            raise AssertionError("legacy_input_unexpectedly_admitted")
        scanner_rejections.append(
            {
                "event_id": str(row["event_id"]),
                "batch_blocked": scan["batch_blocked"],
                "validation_errors": scan["validation_errors"],
            }
        )
    report["existing_scanner_check"] = {"events_tested": len(scanner_rejections), "all_blocked": True}
    events = report.pop("events")
    artifacts = {"summary.json": report, "events.json": events, "scanner_rejections.json": scanner_rejections}
    for name, value in artifacts.items():
        with (output / name).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
    if _digest(input_path) != INPUT_SHA256:
        raise ValueError("input_changed_during_run")
    manifest = {
        "status": "COMPLETE",
        "generated_at": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "base_git_sha": "f00304574044ab9d18aa3603abc538fbb3102c64",
        "input_sha256": INPUT_SHA256,
        "protocol_sha256": PROTOCOL_SHA256,
        "addendum_sha256": _digest(protocol_dir / "MEASUREMENT_ADDENDUM.md"),
        "source_hashes": {
            str(path.relative_to(repository)): _digest(path)
            for path in (
                repository / "brasileirao_predictor/research/price_strength/price_hurdle.py",
                repository / "brasileirao_predictor/research/price_strength/quotes.py",
                Path(__file__).resolve(),
            )
        },
        "artifacts": {name: _digest(output / name) for name in artifacts},
        "isolation": {
            "network": "DENIED",
            "subprocess": "DENIED",
            "sqlite": "DENIED",
            "repository_data": "DENIED",
            "writes": "NEW_OUTPUT_ONLY",
            "environment": "SYSTEM_ALLOWLIST",
        },
        "claims": {"profitability_established": False, "execution_proven": False, "protected_cohorts_used": False},
    }
    with (output / "manifest.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps(report, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
