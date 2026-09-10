import json
import sqlite3

import pytest

from brasileirao_predictor import backup_restore as backup


def fixture(tmp_path):
    source = tmp_path / "source"
    (source / "data").mkdir(parents=True)
    with sqlite3.connect(source / "data" / "matches.db") as conn:
        conn.execute("CREATE TABLE synthetic (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO synthetic VALUES (1, 'only-synthetic-data')")
    (source / "data" / "teams_brasileirao.json").write_text('["synthetic"]', encoding="utf-8")
    return backup.create_backup(tmp_path / "backup", root=source)


def test_restored_copy_keeps_manifest_and_is_independently_verifiable(tmp_path):
    source = fixture(tmp_path)
    restored = backup.restore_backup(source, tmp_path / "restored")
    assert backup.verify_backup(restored)["files"] == backup.verify_backup(source)["files"]
    with sqlite3.connect(restored / "data" / "matches.db") as conn:
        assert conn.execute("SELECT * FROM synthetic").fetchall() == [(1, "only-synthetic-data")]


def test_restore_detects_copy_corruption_before_reporting_success(tmp_path, monkeypatch):
    source = fixture(tmp_path)
    copytree = backup.shutil.copytree

    def broken_copy(src, dst, *args, **kwargs):
        result = copytree(src, dst, *args, **kwargs)
        if src == source.resolve():
            (dst / "data" / "teams_brasileirao.json").write_text('["corrupt"]', encoding="utf-8")
        return result

    monkeypatch.setattr(backup.shutil, "copytree", broken_copy)
    with pytest.raises(backup.BackupError):
        backup.restore_backup(source, tmp_path / "restored")
    assert json.loads((source / "data" / "teams_brasileirao.json").read_text()) == ["synthetic"]


def test_backup_restore_accepts_literal_uri_characters_in_paths(tmp_path):
    directory = tmp_path / "literal # percent %"
    source = fixture(directory)
    restored = backup.restore_backup(source, directory / "restored # copy")
    assert backup.verify_backup(restored)["files"] == backup.verify_backup(source)["files"]


def test_backup_restore_does_not_decode_literal_percent_sequences(tmp_path):
    directory = tmp_path / "literal %23 %3f"
    source = fixture(directory)
    restored = backup.restore_backup(source, directory / "restored %23")
    assert backup.verify_backup(restored)["files"] == backup.verify_backup(source)["files"]


def test_create_refuses_destination_inside_a_copied_tree_before_copying(tmp_path, monkeypatch):
    fixture(tmp_path)
    root = tmp_path / "source"
    (root / "reports").mkdir()

    def forbidden_copy(*args, **kwargs):
        raise AssertionError("recursive backup destination was not rejected")

    monkeypatch.setattr(backup.shutil, "copytree", forbidden_copy)
    with pytest.raises(backup.BackupError):
        backup.create_backup(root / "reports" / "recursive-backup", root=root)


def test_create_checks_source_links_before_copying_external_content(tmp_path, monkeypatch):
    fixture(tmp_path)
    root = tmp_path / "source"
    reports = root / "reports"
    reports.mkdir()
    # Metadata double models a Windows junction/symlink without requiring admin.
    original = type(reports).is_symlink
    monkeypatch.setattr(type(reports), "is_symlink", lambda path: path == reports or original(path))

    def forbidden_copy(*args, **kwargs):
        raise AssertionError("source link was followed before validation")

    monkeypatch.setattr(backup.shutil, "copytree", forbidden_copy)
    with pytest.raises(backup.BackupError):
        backup.create_backup(tmp_path / "second-backup", root=root)
