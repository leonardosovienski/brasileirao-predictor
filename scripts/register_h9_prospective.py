"""Register H9 before its first decision; idempotent and fail-closed."""

from __future__ import annotations

import json
from pathlib import Path

from predictor_core.measurement.trials import TrialRegistry, attestation_path_for

ROOT = Path(__file__).resolve().parent.parent
TRIALS = ROOT / "data" / "trials.json"
CONTRACT = ROOT / "contracts" / "h9-ou25-prospective.json"
NAME = "h9-ou25-prospective-replication"


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    registry = TrialRegistry(TRIALS)
    if any(row.get("name") == NAME for row in registry.load()):
        errors = registry.validate()
        if errors:
            raise SystemExit("invalid trial registry: " + "; ".join(errors))
        print(json.dumps({"trial": NAME, "status": "ALREADY_REGISTERED"}))
        return
    attestation = json.loads(attestation_path_for(TRIALS).read_text(encoding="utf-8"))
    registry.register(
        NAME,
        params={**contract, "capital_enabled": False},
        sharpe=None,
        notes=(
            "PROSPECTIVE registration before the first H9 decision. Strict H8 replication with "
            "named executable H-1.5 bookmaker quote and same-book closing CLV. API-Football lineups "
            "are optional and cannot alter this frozen trial. Any model, source, edge, horizon or "
            "selection change creates a new registered attempt. Shadow only; no capital."
        ),
        test_period=["2026-08-09", "2027-12-31"],
        metric="psr",
        pipeline_fingerprint=attestation["pipeline_fingerprint"],
    )
    errors = registry.validate()
    if errors:
        raise SystemExit("invalid trial registry: " + "; ".join(errors))
    print(json.dumps({"trial": NAME, "status": "REGISTERED"}))


if __name__ == "__main__":
    main()
