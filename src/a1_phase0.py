"""A1 OU2.5 operational calibration: append-only, fingerprinted, no labels."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist
from typing import Any

from .collector_a1 import canonical_json, parse_utc, utc_text
from .math_utils import shin_probabilities

FORBIDDEN_LABEL_KEYS = frozenset(
    {"result", "closing_odds", "clv", "roi", "pnl", "won", "settlement", "home_goals", "away_goals"}
)


def policy_fingerprint(policy_path: Path, code_paths: list[Path]) -> dict[str, Any]:
    files = [policy_path.resolve(), *(path.resolve() for path in code_paths)]
    hashes = {str(path.as_posix()): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    return {
        "schema_version": "a1-phase0-fingerprint/1",
        "policy_id": json.loads(policy_path.read_text(encoding="utf-8"))["policy_id"],
        "files": hashes,
        "fingerprint": hashlib.sha256(canonical_json(hashes)).hexdigest(),
    }


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {str(key).casefold() for key in value} | set().union(*(_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value), set())
    return set()


class Phase0Ledger:
    def __init__(self, path: Path, fingerprint: str) -> None:
        self.path = path
        self.fingerprint = fingerprint

    def append(self, observation: dict[str, Any]) -> str:
        forbidden = _keys(observation) & FORBIDDEN_LABEL_KEYS
        if forbidden:
            raise ValueError(f"phase0 forbids labeled/economic fields: {sorted(forbidden)}")
        existing = (
            [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
            if self.path.exists()
            else []
        )
        record = {
            "schema_version": "a1-phase0-observation/1",
            "recorded_at": utc_text(datetime.now(UTC)),
            "policy_fingerprint": self.fingerprint,
            "observation": observation,
            "hash_prev": existing[-1]["hash_self"] if existing else None,
        }
        record["hash_self"] = hashlib.sha256(canonical_json(record)).hexdigest()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return record["hash_self"]

    def verify(self) -> bool:
        previous = None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["hash_prev"] != previous or record["policy_fingerprint"] != self.fingerprint:
                return False
            claimed = record.pop("hash_self")
            if hashlib.sha256(canonical_json(record)).hexdigest() != claimed:
                return False
            previous = claimed
        return True


def conservative_reference(rows: list[dict[str, Any]], reference_books: set[str]) -> dict[str, Any] | None:
    """Lower probability by selection across complete same-capture OU2.5 pairs."""
    groups: dict[tuple[str, str, str], dict[str, float]] = {}
    for row in rows:
        if (
            row.get("bookmaker") in reference_books
            and row.get("market") == "ou2.5"
            and row.get("line") == 2.5
            and row.get("status") == "active"
        ):
            event = str(row.get("event_id") or row.get("source_event_id") or "missing-event")
            groups.setdefault((event, str(row["bookmaker"]), str(row["captured_at"])), {})[str(row["selection"])] = (
                float(row["odds"])
            )
    estimates: dict[str, list[float]] = {"over": [], "under": []}
    complete = 0
    for pair in groups.values():
        if set(pair) != {"over", "under"}:
            continue
        complete += 1
        odds = [pair["over"], pair["under"]]
        implied = [1 / odd for odd in odds]
        proportional = [value / sum(implied) for value in implied]
        shin = list(shin_probabilities(odds)[0])
        for index, selection in enumerate(("over", "under")):
            estimates[selection].extend((float(proportional[index]), float(shin[index])))
    if not complete:
        return None
    return {
        "complete_reference_pairs": complete,
        "p_conservative": {selection: min(values) for selection, values in estimates.items()},
        "p_range": {selection: [min(values), max(values)] for selection, values in estimates.items()},
        "method": "minimum across proportional and Shin; sensitivity range, not a confidence interval",
    }


def clv_required_sample_size(
    pilot_sd_log_clv: float,
    minimum_mean_log_clv: float,
    *,
    power: float = 0.8,
    alpha: float = 0.05,
    design_effect: float = 1.0,
) -> int:
    if (
        pilot_sd_log_clv <= 0
        or minimum_mean_log_clv <= 0
        or not 0 < power < 1
        or not 0 < alpha < 1
        or design_effect < 1
    ):
        raise ValueError("invalid CLV power parameters")
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return math.ceil(design_effect * (z * pilot_sd_log_clv / minimum_mean_log_clv) ** 2)


def phase0_report(rows: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    reference = conservative_reference(rows, set(policy["reference_books"]))
    soft = [row for row in rows if row.get("bookmaker") in policy["soft_books"] and row.get("market") == "ou2.5"]
    capture_times = [parse_utc(str(row["captured_at"])) for row in rows]
    uncertainty_pp = None
    if reference:
        uncertainty_pp = max(100 * (bounds[1] - bounds[0]) for bounds in reference["p_range"].values())
    return {
        "schema_version": "a1-phase0-report/1",
        "scientific_state": "OPERATIONAL_CALIBRATION_NO_LABELS",
        "rows": len(rows),
        "soft_rows": len(soft),
        "reference": reference,
        "operational_friction_observations": {
            "reference_method_range_max_pp": uncertainty_pp,
            "active_soft_books": sorted({str(row["bookmaker"]) for row in soft if row.get("status") == "active"}),
            "commission_pp": None,
            "slippage_pp": None,
            "latency_pp": None,
            "availability_pp": None,
            "note": "null components require prospective operational measurement; no invented defaults",
        },
        "first_capture": utc_text(min(capture_times)) if capture_times else None,
        "last_capture": utc_text(max(capture_times)) if capture_times else None,
        "threshold_frozen": bool(policy["threshold_frozen"]),
        "capital_enabled": False,
        "contains_outcomes": False,
    }
