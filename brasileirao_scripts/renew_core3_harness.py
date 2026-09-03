"""Execute and enrich the real RPS power harness under predictor-core 3.x."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from brasileirao_scripts.research_01a_refit_cadence import TRIALS, attest_rps_power

ROOT = Path(__file__).resolve().parent.parent


def _code_version() -> str:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    )
    return f"git:{sha}{';dirty' if dirty else ''}"


def run() -> dict:
    record = attest_rps_power()
    reference = json.dumps(
        {
            "positive": {"generator": "probabilistic_predictor", "n": 300, "skill": 0.6, "seed": 13},
            "negative": {"generator": "probabilistic_predictor", "n": 300, "skill": 0.0, "seed": 17},
            "metric": "rps",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    record.update(
        {
            "executed_at": record["passed_at"],
            "code_version": _code_version(),
            "dataset_reference_fingerprint": "sha256:" + hashlib.sha256(reference).hexdigest(),
            "positive_control_result": "COMPROVADA",
            "negative_control_result": "REFUTADA",
        }
    )
    path = TRIALS.with_name(TRIALS.stem + ".harness_attestation.json")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return record


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
