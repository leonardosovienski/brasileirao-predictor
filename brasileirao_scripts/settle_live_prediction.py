"""Liquida uma previsão ao vivo em ledger separado, append-only e sem capital."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brasileirao_predictor.bet_log import _writer_lock  # noqa: E402
from brasileirao_predictor.sofascore import Sofascore  # noqa: E402

PREDICTIONS = ROOT / "data" / "live_predictions.jsonl"
SETTLEMENTS = ROOT / "data" / "live_prediction_settlements.jsonl"
Clock = Callable[[], datetime]


def load_prediction(path: Path, prediction_id: str) -> dict:
    matches = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("prediction_id") == prediction_id:
            matches.append(row)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one prediction {prediction_id}; found {len(matches)}")
    return matches[0]


def build_settlement(prediction: dict, event: dict, settled_at: datetime) -> dict:
    if settled_at.tzinfo is None or settled_at.utcoffset() is None:
        raise ValueError("settled_at must be timezone-aware")
    status = event.get("status") or {}
    if status.get("type") != "finished":
        raise ValueError("event is not finished")
    expected = prediction.get("source_event_id")
    if not expected or isinstance(expected, bool) or str(event.get("id")) != str(expected):
        raise ValueError("event identity does not match prediction")
    home = (event.get("homeScore") or {}).get("current")
    away = (event.get("awayScore") or {}).get("current")
    if type(home) is not int or type(away) is not int or home < 0 or away < 0:
        raise ValueError("official final score unavailable")
    actual = "home" if home > away else "away" if away > home else "draw"
    probs = prediction["prediction"]
    values = [probs.get(f"p_{key}") for key in ("home", "draw", "away")]
    if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in values):
        raise ValueError("invalid probability vector")
    if not math.isclose(sum(values), 1.0, abs_tol=1e-9, rel_tol=0):
        raise ValueError("probabilities must sum to one")
    predicted = max(("home", "draw", "away"), key=lambda key: float(probs[f"p_{key}"]))
    row = {
        "schema_version": "live-prediction-settlement/2",
        "prediction_id": prediction["prediction_id"],
        "source_event_id": str(event.get("id")),
        "settled_at": settled_at.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "sofascore",
        "official_status": status,
        "final_score": [home, away],
        "actual_1x2": actual,
        "predicted_1x2": predicted,
        "diagnostic_hit": predicted == actual,
        "accuracy_policy": "DIAGNOSTIC_ONLY",
        "capital_enabled": False,
        "original_prediction_unchanged": True,
        "prediction_hash": _digest(prediction),
    }
    row["fact_hash"] = _digest({k: v for k, v in row.items() if k != "settled_at"})
    row["content_hash"] = _digest(row)
    return row


def _digest(value: dict) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_settlement(path: Path, row: dict) -> bool:
    return record_settlement(path, row)[0]


def record_settlement(path: Path, row: dict) -> tuple[bool, dict]:
    """Return the persisted receipt under the same writer lock used for append."""
    path = path.resolve()
    with _writer_lock(path):
        return _append_settlement_locked(path, row)


def _append_settlement_locked(path: Path, row: dict) -> tuple[bool, dict]:
    if row.get("content_hash") != _digest({k: v for k, v in row.items() if k != "content_hash"}):
        raise ValueError("settlement content hash mismatch")
    if row.get("fact_hash") != _digest(
        {k: v for k, v in row.items() if k not in {"content_hash", "fact_hash", "settled_at"}}
    ):
        raise ValueError("settlement fact hash mismatch")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            existing = json.loads(line)
            if existing.get("prediction_id") == row.get("prediction_id"):
                valid = existing.get("content_hash") == _digest(
                    {k: v for k, v in existing.items() if k != "content_hash"}
                )
                if not valid or existing.get("fact_hash") != row.get("fact_hash"):
                    raise ValueError(f"conflicting settlement for {row.get('prediction_id')}")
                return False, existing
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return True, row


def wait_for_final(
    event_id: int,
    client: Sofascore,
    *,
    poll_seconds: int = 60,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    while True:
        payload = client._get(f"event/{event_id}", cache=False) or {}
        event = payload.get("event", payload)
        if (event.get("status") or {}).get("type") == "finished":
            return event
        sleep(max(15, poll_seconds))


def main(*, now: Clock = lambda: datetime.now(UTC)) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prediction_id")
    parser.add_argument("--predictions", type=Path, default=PREDICTIONS)
    parser.add_argument("--settlements", type=Path, default=SETTLEMENTS)
    parser.add_argument("--wait-final", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--run-log", type=Path)
    args = parser.parse_args()
    prediction = load_prediction(args.predictions, args.prediction_id)
    event_id = int(prediction["source_event_id"])
    client = Sofascore(rate_limit=0.2, cache_dir=None)
    if args.wait_final:
        event = wait_for_final(event_id, client, poll_seconds=args.poll_seconds)
    else:
        payload = client._get(f"event/{event_id}", cache=False) or {}
        event = payload.get("event", payload)
    row = build_settlement(prediction, event, now())
    appended, row = record_settlement(args.settlements, row)
    output = json.dumps(
        {"prediction_id": args.prediction_id, "settlement_appended": appended, **row}, ensure_ascii=False
    )
    print(output, flush=True)
    if args.run_log:
        args.run_log.parent.mkdir(parents=True, exist_ok=True)
        with args.run_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(output + "\n")
            handle.flush()
            os.fsync(handle.fileno())


if __name__ == "__main__":
    main()
