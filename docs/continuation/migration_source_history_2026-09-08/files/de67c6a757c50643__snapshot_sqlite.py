"""Capture a stable SQLite file set without letting SQLite open original files.

Original DB/WAL/SHM/journal files receive byte reads and stat calls only. SQLite
opens a private staged clone with mode=ro, backs it up to a new owned destination,
and runs integrity_check only on that destination. No application rows are read.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import time
import uuid

SNAPSHOTS_ROOT = Path(__file__).resolve().parent / "sqlite_snapshots"
SUFFIXES = (("main", ""), ("wal", "-wal"), ("shm", "-shm"), ("journal", "-journal"))
BUFFER_BYTES = 1024 * 1024


class CaptureError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _check_deadline(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise CaptureError("capture_timeout")


def _sha256(path: Path, deadline: float) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(BUFFER_BYTES):
            _check_deadline(deadline)
            digest.update(chunk)
    return digest.hexdigest()


def _stat_fields(value: os.stat_result) -> dict:
    return {"size": value.st_size, "mtime_ns": value.st_mtime_ns,
            "device": value.st_dev, "file_id": value.st_ino,
            "birthtime_ns": getattr(value, "st_birthtime_ns", None)}


def _observe(source: Path, deadline: float) -> list[dict]:
    observations = []
    for role, suffix in SUFFIXES:
        path = Path(str(source) + suffix)
        try:
            before = path.stat()
        except FileNotFoundError:
            observations.append({"role": role, "path": str(path), "exists": False})
            continue
        if not stat.S_ISREG(before.st_mode):
            raise CaptureError("source_member_is_not_regular_file")
        digest = _sha256(path, deadline)
        after = path.stat()
        if _stat_fields(before) != _stat_fields(after):
            raise CaptureError("source_changed_during_observation")
        observations.append({"role": role, "path": str(path), "exists": True,
                             **_stat_fields(after), "sha256": digest})
    return observations


def _copy_file(source: Path, destination: Path, deadline: float) -> None:
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        while chunk := incoming.read(BUFFER_BYTES):
            _check_deadline(deadline)
            outgoing.write(chunk)


def _remove_owned(path: Path, root: Path) -> None:
    resolved = path.resolve()
    boundary = root.resolve()
    if resolved == boundary or not resolved.is_relative_to(boundary):
        raise RuntimeError("Refusing cleanup outside the snapshot directory")
    if path.is_symlink():
        raise RuntimeError("Refusing cleanup of replaced staging path")
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def snapshot_sqlite(source: str | Path, *, timeout_seconds: float = 300,
                    keep_staging: bool = False) -> dict:
    """Return and persist an exclusive JSON receipt; status is ok or failed.

    Stable observations are required before/after capture and after backup. A
    concurrent change is refused without retrying or stopping the other process.
    This is a per-database capture window, not a VSS/global application snapshot.
    """
    if isinstance(timeout_seconds, bool) or not 0 < timeout_seconds <= 3600:
        raise ValueError("timeout_seconds must be in (0, 3600]")
    started = _utc()
    deadline = time.monotonic() + timeout_seconds
    requested = Path(source).absolute()
    source_path = requested.resolve()
    root = SNAPSHOTS_ROOT.resolve()
    root.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_path.stem)[:60] or "sqlite"
    token = f"{slug}__{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}__{uuid.uuid4().hex[:12]}"
    stage = root / "_staging" / token
    destination = root / (token + ".sqlite3")
    receipt_path = root / (token + ".receipt.json")
    receipt = {
        "format": "sqlite-migration-snapshot/1", "status": "failed",
        "source_requested_path": str(requested), "source_path": str(source_path),
        "started_at_utc": started, "sqlite_version": sqlite3.sqlite_version,
        "original_sqlite_connection_opened": False, "original_access": "byte_reads_and_stat_only",
        "source_capture_scope": "per_database_stability_window_not_global_or_vss",
        "staging_sqlite_mode": "ro", "integrity_check_target": "new_snapshot_only",
        "receipt_path": str(receipt_path), "snapshot_path": None,
        "staging_path": str(stage), "staging_retained": keep_staging,
    }
    created_destination = False
    try:
        before = _observe(source_path, deadline)
        receipt["source_files_before"] = before
        if not before[0]["exists"]:
            raise CaptureError("source_missing")
        if before[0]["size"] == 0:
            raise CaptureError("empty_file_is_not_declared_a_valid_database")
        if any(item["role"] == "wal" and item["exists"] and item["size"] > 0 for item in before):
            receipt["source_kind"] = "sqlite_with_wal_sidecar"
        elif any(item["role"] == "journal" and item["exists"] for item in before):
            receipt["source_kind"] = "sqlite_with_rollback_journal_sidecar"
        else:
            receipt["source_kind"] = "sqlite_main_file_without_nonempty_wal"
        stage.mkdir(parents=True, exist_ok=False)
        staged_main = stage / source_path.name
        for item in before:
            if not item["exists"]:
                continue
            staged_file = stage / Path(item["path"]).name
            _copy_file(Path(item["path"]), staged_file, deadline)
            if _sha256(staged_file, deadline) != item["sha256"]:
                raise CaptureError("staged_bytes_differ_from_initial_observation")
        after_capture = _observe(source_path, deadline)
        receipt["source_files_after_capture"] = after_capture
        receipt["capture_finished_at_utc"] = _utc()
        if before != after_capture:
            raise CaptureError("source_changed_during_capture")
        # SHM is a disposable index/read-mark cache. Regenerate only this private
        # copy so stale shared-memory state is never treated as source authority.
        private_shm = Path(str(staged_main) + "-shm")
        if private_shm.exists():
            _remove_owned(private_shm, root)
        receipt["private_shm_rebuilt_if_required"] = True
        with destination.open("xb"):
            pass
        created_destination = True
        with closing(sqlite3.connect(staged_main.as_uri() + "?mode=ro", uri=True,
                                     timeout=5, isolation_level=None)) as incoming:
            with closing(sqlite3.connect(destination.as_uri() + "?mode=rw", uri=True,
                                         timeout=5, isolation_level=None)) as outgoing:
                incoming.backup(outgoing, pages=256,
                                progress=lambda *_: _check_deadline(deadline), sleep=0.05)
                check = outgoing.execute("PRAGMA integrity_check").fetchall()
                receipt["integrity_ok"] = check == [("ok",)]
                receipt["integrity_result_count"] = len(check)
                if not receipt["integrity_ok"]:
                    raise CaptureError("snapshot_integrity_check_failed")
        # Opening a WAL clone can transfer its journal-mode flag. Closing the last
        # destination connection must leave a standalone file, not needed WAL data.
        destination_wal = Path(str(destination) + "-wal")
        if destination_wal.exists() and destination_wal.stat().st_size:
            raise CaptureError("snapshot_requires_nonempty_wal_sidecar")
        final = _observe(source_path, deadline)
        receipt["source_files_after_snapshot"] = final
        if before != final:
            raise CaptureError("source_changed_during_snapshot_window")
        receipt.update({"status": "ok", "snapshot_path": str(destination),
                        "snapshot_sha256": _sha256(destination, deadline),
                        "snapshot_size": destination.stat().st_size,
                        "original_bytes_and_observed_metadata_unchanged": True})
    except CaptureError as exc:
        receipt["failure_code"] = exc.code
    except (OSError, sqlite3.Error) as exc:
        # Do not echo SQLite diagnostics that could contain table/row names.
        receipt["failure_code"] = "file_or_sqlite_operation_failed"
        receipt["error_type"] = type(exc).__name__
    finally:
        if receipt["status"] != "ok" and created_destination:
            for suffix in ("", "-wal", "-shm", "-journal"):
                _remove_owned(Path(str(destination) + suffix), root)
        if not keep_staging and stage.exists():
            _remove_owned(stage, root)
        receipt["completed_at_utc"] = _utc()
        with receipt_path.open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    parser.add_argument("--keep-staging", action="store_true")
    args = parser.parse_args()
    failed = False
    for source in args.source:
        result = snapshot_sqlite(source, timeout_seconds=args.timeout_seconds,
                                 keep_staging=args.keep_staging)
        failed |= result["status"] != "ok"
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
