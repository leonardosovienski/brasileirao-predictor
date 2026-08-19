import json
import sqlite3
from pathlib import Path

import pytest

from src.backup_restore import BackupError, create_backup, restore_backup, verify_backup


def _root(path: Path) -> Path:
    (path / "data").mkdir(parents=True)
    conn = sqlite3.connect(path / "data" / "matches.db")
    conn.execute("create table matches (id integer primary key, team text)")
    conn.execute("insert into matches values (1, 'Palmeiras')")
    conn.commit()
    conn.close()
    (path / "data" / "sombra_picks.jsonl").write_text('{"event_id": 1}\n', encoding="utf-8")
    (path / "data" / "trials.json").write_text("[]", encoding="utf-8")
    return path


def test_backup_verify_restore_roundtrip(tmp_path):
    source = _root(tmp_path / "source")
    backup = create_backup(tmp_path / "backup", root=source)
    assert verify_backup(backup)["schema_version"] == "brasileirao-backup/1.0"
    assert not list((backup / "data").glob("matches.db-*"))
    restored = restore_backup(backup, tmp_path / "restored")
    conn = sqlite3.connect(restored / "data" / "matches.db")
    assert conn.execute("select * from matches").fetchall() == [(1, "Palmeiras")]
    conn.close()
    assert json.loads((restored / "data" / "trials.json").read_text()) == []


def test_backup_includes_research_and_runtime(tmp_path):
    source = _root(tmp_path / "source")
    (source / "data" / "research").mkdir()
    (source / "data" / "research" / "h9_shadow.jsonl").write_text("{}\n")
    (source / "data" / "runtime").mkdir()
    (source / "data" / "runtime" / "heartbeat.json").write_text("{}\n")
    backup = create_backup(tmp_path / "backup", root=source)
    assert (backup / "data" / "research" / "h9_shadow.jsonl").is_file()
    assert (backup / "data" / "runtime" / "heartbeat.json").is_file()


def test_backup_rejeita_tamper_e_overwrite(tmp_path):
    source = _root(tmp_path / "source")
    backup = create_backup(tmp_path / "backup", root=source)
    (backup / "data" / "sombra_picks.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(BackupError, match="diverge"):
        verify_backup(backup)
    clean = create_backup(tmp_path / "clean", root=source)
    with pytest.raises(BackupError, match="já existe"):
        restore_backup(clean, tmp_path)
