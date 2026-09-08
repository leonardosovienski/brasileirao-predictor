"""Reconcile the five migration snapshots with a fresh byte-only observation."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import time

from snapshot_sqlite import _observe, snapshot_sqlite


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> int:
    root = Path(__file__).resolve().parent
    original = root / "sqlite_snapshot_receipts.json"
    final = root / "sqlite_snapshot_receipts_final.json"
    consistency = root / "sqlite_snapshot_final_consistency.json"
    if final.exists() or consistency.exists():
        raise SystemExit("Final artifacts already exist; refusing to overwrite.")
    receipts = json.loads(original.read_text(encoding="utf-8"))
    if len(receipts) != 5 or any(row["status"] != "ok" for row in receipts):
        raise SystemExit("Expected the five previously successful authorized captures.")
    audit = {
        "format": "sqlite-migration-final-reconciliation/1",
        "started_at_utc": _utc(),
        "original_aggregate_path": str(original),
        "original_aggregate_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "source_access": "byte_reads_and_stat_only",
        "scope": "per_database_observation_not_global_or_vss",
        "checks": [],
    }
    selected = []
    for receipt in receipts:
        observed_at = _utc()
        observed = _observe(Path(receipt["source_path"]), time.monotonic() + 300)
        baseline = {item["role"]: item for item in receipt["source_files_after_snapshot"]}
        changes = []
        for item in observed:
            before = baseline[item["role"]]
            fields = sorted(key for key in set(before) | set(item)
                            if before.get(key) != item.get(key))
            if fields:
                changes.append({"role": item["role"], "changed_fields": fields})
        # Rollback journals can also carry recovery-relevant changes. Treat every
        # DB/WAL/journal change conservatively; SHM alone is a disposable cache.
        recapture = any(item["role"] in {"main", "wal", "journal"} for item in changes)
        chosen = snapshot_sqlite(receipt["source_path"]) if recapture else receipt
        selected.append(chosen)
        check = {
            "source_path": receipt["source_path"],
            "observation_started_at_utc": observed_at,
            "observation_completed_at_utc": _utc(),
            "compared_to_receipt": receipt["receipt_path"],
            "source_files_observed": observed,
            "changes": changes,
            "decision": "recaptured" if recapture else "reuse_snapshot",
            "selected_receipt_path": chosen["receipt_path"],
            "selected_snapshot_path": chosen.get("snapshot_path"),
            "selected_status": chosen["status"],
        }
        audit["checks"].append(check)
        print(json.dumps({key: check[key] for key in (
            "source_path", "changes", "decision", "selected_status"
        )}), flush=True)
    audit["completed_at_utc"] = _utc()
    audit["all_five_ok"] = len(selected) == 5 and all(row["status"] == "ok" for row in selected)
    if audit["all_five_ok"]:
        _write_new(final, selected)
        audit["final_aggregate_path"] = str(final)
        audit["final_aggregate_sha256"] = hashlib.sha256(final.read_bytes()).hexdigest()
    _write_new(consistency, audit)
    print(json.dumps({
        "all_five_ok": audit["all_five_ok"],
        "final_aggregate_path": audit.get("final_aggregate_path"),
        "final_aggregate_sha256": audit.get("final_aggregate_sha256"),
        "consistency_receipt_path": str(consistency),
    }), flush=True)
    return 0 if audit["all_five_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
