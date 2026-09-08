"""Synthetic-only tests. No repository/operational database is opened."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import time
import unittest
from unittest.mock import patch
import uuid

import snapshot_sqlite as subject

TEST_ROOT = Path(__file__).resolve().parent / "synthetic_tests" / ("suite_" + uuid.uuid4().hex)
TEST_ROOT.mkdir(parents=True, exist_ok=False)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.directory = TEST_ROOT / self._testMethodName
        self.directory.mkdir(exist_ok=False)
        self.source = self.directory / "synthetic # & source.db"
        self.writer = sqlite3.connect(self.source)
        self.writer.execute("PRAGMA journal_mode=WAL")
        self.writer.execute("PRAGMA wal_autocheckpoint=0")
        self.writer.execute("CREATE TABLE synthetic_rows(value INTEGER)")
        self.writer.commit()
        self.writer.execute("PRAGMA wal_checkpoint(TRUNCATE)")  # Synthetic fixture only.
        self.writer.executemany("INSERT INTO synthetic_rows VALUES (?)", [(1,), (2,), (3,)])
        self.writer.commit()

    def tearDown(self):
        self.writer.close()

    def observe(self):
        return subject._observe(self.source, time.monotonic() + 30)

    def test_committed_wal_is_preserved_without_opening_or_mutating_originals(self):
        main_only = self.directory / "synthetic_main_only.db"
        shutil.copyfile(self.source, main_only)
        with sqlite3.connect(main_only.as_uri() + "?mode=ro", uri=True) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM synthetic_rows").fetchone()[0], 0)
        before = self.observe()
        self.assertGreater(Path(str(self.source) + "-wal").stat().st_size, 32)
        connections, statements = [], []
        original_connect = sqlite3.connect

        def connect(database_url, **kwargs):
            connections.append(database_url)
            self.assertNotEqual(database_url.split("?")[0], self.source.as_uri())
            connection = original_connect(database_url, **kwargs)
            connection.set_trace_callback(lambda sql: statements.append((database_url, sql)))
            return connection

        with patch.object(subject.sqlite3, "connect", side_effect=connect):
            receipt = subject.snapshot_sqlite(self.source)
        self.assertEqual(receipt["status"], "ok", receipt)
        self.assertEqual(receipt["source_kind"], "sqlite_with_wal_sidecar")
        self.assertFalse(receipt["original_sqlite_connection_opened"])
        self.assertEqual(before, self.observe())
        self.assertEqual(len(connections), 2)
        self.assertIn("_staging", connections[0])
        self.assertIn("?mode=ro", connections[0])
        self.assertIn("?mode=rw", connections[1])
        self.assertEqual(statements, [(connections[1], "PRAGMA integrity_check")])
        copied = Path(receipt["snapshot_path"])
        with sqlite3.connect(copied.as_uri() + "?mode=ro", uri=True) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM synthetic_rows").fetchone()[0], 3)
        self.assertEqual(receipt["snapshot_sha256"], hashlib.sha256(copied.read_bytes()).hexdigest())
        self.assertFalse(Path(receipt["staging_path"]).exists())

    def test_concurrent_change_is_refused_without_stopping_writer(self):
        copy = subject._copy_file
        changed = False

        def concurrent(source, destination, deadline):
            nonlocal changed
            copy(source, destination, deadline)
            if source == self.source and not changed:
                self.writer.execute("INSERT INTO synthetic_rows VALUES (4)")
                self.writer.commit()
                changed = True

        with patch.object(subject, "_copy_file", side_effect=concurrent):
            receipt = subject.snapshot_sqlite(self.source)
        self.assertEqual(receipt["status"], "failed")
        self.assertIn(receipt["failure_code"], {
            "staged_bytes_differ_from_initial_observation", "source_changed_during_capture"})
        self.assertIsNone(receipt["snapshot_path"])
        self.assertEqual(self.writer.execute("SELECT COUNT(*) FROM synthetic_rows").fetchone()[0], 4)

    def test_empty_file_is_not_fabricated_into_a_database(self):
        empty = self.directory / "empty.db"
        empty.touch(exist_ok=False)
        with patch.object(subject.sqlite3, "connect") as connect:
            receipt = subject.snapshot_sqlite(empty)
        connect.assert_not_called()
        self.assertEqual(receipt["failure_code"], "empty_file_is_not_declared_a_valid_database")
        self.assertEqual(empty.stat().st_size, 0)

    def test_invalid_file_fails_without_exposing_database_diagnostics(self):
        invalid = self.directory / "invalid.db"
        contents = b"synthetic_invalid_marker" * 100
        invalid.write_bytes(contents)
        receipt = subject.snapshot_sqlite(invalid)
        self.assertEqual(receipt["status"], "failed")
        self.assertIsNone(receipt["snapshot_path"])
        self.assertEqual(invalid.read_bytes(), contents)
        self.assertNotIn("synthetic_invalid_marker", json.dumps(receipt))

    def test_repeated_capture_creates_distinct_files_without_overwrite(self):
        first = subject.snapshot_sqlite(self.source)
        second = subject.snapshot_sqlite(self.source)
        self.assertEqual(first["status"], "ok")
        self.assertEqual(second["status"], "ok")
        self.assertNotEqual(first["snapshot_path"], second["snapshot_path"])
        self.assertNotEqual(first["receipt_path"], second["receipt_path"])
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])


if __name__ == "__main__":
    started = datetime.now(UTC).isoformat()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SnapshotTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {"started_at_utc": started, "completed_at_utc": datetime.now(UTC).isoformat(),
               "synthetic_only": True, "test_root": str(TEST_ROOT), "sqlite_version": sqlite3.sqlite_version,
               "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "success": result.wasSuccessful(),
               "source_sha256": hashlib.sha256(Path(subject.__file__).read_bytes()).hexdigest()}
    (TEST_ROOT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt), flush=True)
    raise SystemExit(0 if result.wasSuccessful() else 1)
