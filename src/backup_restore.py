"""Backup e restauração verificáveis dos artefatos operacionais científicos.

Usa a API online do SQLite para produzir snapshot consistente mesmo com WAL.
Restauração só aceita uma raiz inexistente e nunca sobrescreve produção.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = "brasileirao-backup/1.0"
LEDGERS = (
    "sombra_picks.jsonl",
    "sombra_results.jsonl",
    "sombra_h5_picks.jsonl",
    "sombra_h5_results.jsonl",
    "trials.json",
    "trials.harness_attestation.json",
    "teams_brasileirao.json",
)
OPERATIONAL_DIRECTORIES = ("odds_snapshots", "odds_quarantine", "collector_state", "collector_metrics")


class BackupError(RuntimeError):
    pass


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and path.name != "BACKUP_MANIFEST.json")


def create_backup(destination: Path, *, root: Path = ROOT) -> Path:
    destination = destination.resolve()
    if destination.exists():
        raise BackupError(f"destino já existe: {destination}")
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    temporary.mkdir(parents=True)
    try:
        data = temporary / "data"
        data.mkdir()
        source_db = root / "data" / "matches.db"
        if not source_db.is_file():
            raise BackupError("data/matches.db ausente")
        source = sqlite3.connect(f"file:{source_db.resolve().as_posix()}?mode=ro", uri=True, timeout=30)
        target = sqlite3.connect(data / "matches.db")
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        odds_db = root / "data" / "odds_operational.db"
        if odds_db.is_file():
            source = sqlite3.connect(f"file:{odds_db.resolve().as_posix()}?mode=ro", uri=True, timeout=30)
            target = sqlite3.connect(data / "odds_operational.db")
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
        for name in LEDGERS:
            path = root / "data" / name
            if path.is_file():
                shutil.copy2(path, data / name)
        for name in ("research", "runtime"):
            source_directory = root / "data" / name
            if source_directory.is_dir():
                shutil.copytree(source_directory, data / name)
        for name in OPERATIONAL_DIRECTORIES:
            source_directory = root / "data" / name
            if source_directory.is_dir():
                shutil.copytree(source_directory, data / name)
        files = {path.relative_to(temporary).as_posix(): _hash(path) for path in _files(temporary)}
        manifest: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "created_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "files": files,
        }
        (temporary / "BACKUP_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.rename(destination)
        return destination
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def verify_backup(backup: Path) -> dict[str, Any]:
    backup = backup.resolve()
    try:
        manifest = json.loads((backup / "BACKUP_MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError(f"manifesto ilegível: {exc}") from exc
    if manifest.get("schema_version") != SCHEMA_VERSION or not isinstance(manifest.get("files"), dict):
        raise BackupError("manifesto inválido")
    actual = {path.relative_to(backup).as_posix(): _hash(path) for path in _files(backup)}
    if actual != manifest["files"]:
        raise BackupError("conteúdo do backup diverge do manifesto")
    for database in (backup / "data").glob("*.db"):
        conn = sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BackupError(f"integrity_check do SQLite falhou: {database.name}")
        finally:
            conn.close()
    return manifest


def restore_backup(backup: Path, destination_root: Path) -> Path:
    verify_backup(backup)
    destination_root = destination_root.resolve()
    if destination_root.exists():
        raise BackupError(f"raiz de restauração já existe: {destination_root}")
    shutil.copytree(backup.resolve(), destination_root)
    (destination_root / "BACKUP_MANIFEST.json").unlink()
    return destination_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backup/restore verificável do brasileirao-predictor")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--backup", type=Path, required=True)
    restore = sub.add_parser("restore")
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = {"backup": str(create_backup(args.output))}
        elif args.command == "verify":
            result = {"verified": str(args.backup), "manifest": verify_backup(args.backup)}
        else:
            result = {"restored": str(restore_backup(args.backup, args.destination))}
    except (BackupError, OSError, sqlite3.Error) as exc:
        print(str(exc))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
