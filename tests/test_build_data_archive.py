"""Synthetic-only migration tests; no application, database or network imports."""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.migration import build_data_archive as builder
from scripts.migration.verify_archive import verify

COMMIT = "abc12345" * 5
REMOTE = "https://github.com/example/project.git"


def zipped(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


class DataArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="data-archive-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.zip"
        self.plan_path = self.root / "plan.json"
        self.output = self.root / "new" / "data.zip"

    def fixture(self, payloads=None, selected=None, *, maps=None, corrupt=None):
        self.payloads = (
            payloads if payloads is not None else {"data.csv": b"n,v\n1,2\n", "code.py": b"print('never run')"}
        )
        entries = [builder._metadata_entry(name, content) for name, content in self.payloads.items()]
        if corrupt:
            next(entry for entry in entries if entry["path"] == corrupt)["sha256"] = "0" * 64
        self.manifest = {
            "files": entries,
            "snapshot_restore_map": maps or [],
            "omissions": [{"path": "original-unreadable", "reason": "synthetic"}],
        }
        manifest_bytes = builder._json_bytes(self.manifest)
        self.source.write_bytes(zipped({**self.payloads, builder.MANIFEST: manifest_bytes}))
        selected = selected if selected is not None else [name for name in self.payloads if not name.endswith(".py")]
        self.plan = {
            "schema_version": 1,
            "source_sha256": builder._hash_file(self.source),
            "source_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "include_names": selected,
            "excluded": [{**entry, "reason": "source code"} for entry in entries if entry["path"] not in selected],
            "extras": [],
        }
        self.save_plan()

    def save_plan(self):
        self.plan_path.write_bytes(builder._json_bytes(self.plan))

    def build(self):
        return builder.build_archive(self.source, self.plan_path, self.output, code_commit=COMMIT, code_remote=REMOTE)

    def rejects(self, pattern):
        source_hash = builder._hash_file(self.source)
        with self.assertRaisesRegex(ValueError, pattern):
            self.build()
        self.assertFalse(self.output.exists())
        self.assertEqual(source_hash, builder._hash_file(self.source))

    def test_end_to_end_preserves_bytes_maps_exclusions_and_standalone_verification(self):
        snapshot = b"synthetic opaque sqlite bytes, never queried"
        snapshot_hash = hashlib.sha256(snapshot).hexdigest()
        receipt = {
            "receipt_path": "C:/old/snapshot.receipt.json",
            "snapshot_sha256": snapshot_hash,
            "status": "ok",
            "integrity_ok": True,
        }
        maps = [
            {
                "source_archive_path": "db/source.db",
                "snapshot_archive_path": "snapshots/snapshot.sqlite3",
                "snapshot_sha256": snapshot_hash,
                "receipt": receipt,
            }
        ]
        self.fixture(
            {
                "db/source.db": b"opaque original",
                "db/source.db-wal": b"opaque WAL",
                "snapshots/snapshot.sqlite3": snapshot,
                "snapshots/snapshot.receipt.json": builder._json_bytes(receipt),
                "cache/a.zip": zipped({"data/a.csv": b"a,b\n1,2\n"}),
                "config/.env": b"SYNTHETIC_ONLY=value\n",
                "code.py": b"raise RuntimeError('must never run')",
            },
            maps=maps,
        )
        guide = self.root / "guide.md"
        guide.write_bytes(b"# Synthetic restoration instructions\n")
        self.plan["extras"] = [
            {
                "source_path": str(guide),
                "archive_path": "RESTORE.md",
                "bytes": guide.stat().st_size,
                "sha256": builder._hash_file(guide),
                "provenance": {"kind": "synthetic guide", "original_name": "guide.md"},
            }
        ]
        self.save_plan()
        original_hash = builder._hash_file(self.source)
        result = self.build()
        self.assertEqual("PASS", result["status"])
        self.assertEqual(1, result["snapshot_restore_maps_preserved"])
        self.assertEqual(original_hash, builder._hash_file(self.source))
        with zipfile.ZipFile(self.output) as archive:
            self.assertNotIn("code.py", archive.namelist())
            for name in self.plan["include_names"]:
                self.assertEqual(self.payloads[name], archive.read(name))
            manifest = json.loads(archive.read(builder.MANIFEST))
            self.assertEqual(maps, manifest["snapshot_restore_map"])
            self.assertEqual(COMMIT, manifest["code"]["commit"])
            self.assertEqual(self.manifest["omissions"], manifest["omissions"])
            self.assertEqual(self.plan, json.loads(archive.read(builder.PLAN_ENTRY)))
        target = self.root / "restored"
        self.assertEqual("PASS", verify(self.output, target)["status"])
        self.assertEqual(snapshot, (target / "snapshots/snapshot.sqlite3").read_bytes())
        for path in result["artifacts"].values():
            self.assertTrue(Path(path).is_file())

    def test_source_hash_mismatch_is_rejected_before_creating_output(self):
        self.fixture()
        self.plan["source_sha256"] = "0" * 64
        self.save_plan()
        self.rejects("Source ZIP does not match")

    def test_manifest_hash_mismatch_is_rejected(self):
        self.fixture()
        self.plan["source_manifest_sha256"] = "0" * 64
        self.save_plan()
        self.rejects("Source manifest")

    def test_corrupt_included_hash_removes_own_partial_output(self):
        self.fixture(corrupt="data.csv")
        self.rejects("Entry SHA-256")
        self.assertEqual([], list(self.output.parent.iterdir()))

    def test_exclusions_cannot_hide_unaccounted_files(self):
        self.fixture()
        self.plan["excluded"] = []
        self.save_plan()
        self.rejects("Exclusions must account")

    def test_existing_output_is_preserved(self):
        self.fixture()
        self.output.parent.mkdir()
        self.output.write_bytes(b"preexisting archive")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.build()
        self.assertEqual(b"preexisting archive", self.output.read_bytes())

    def test_extra_cannot_sneak_in_source_or_mismatched_bytes(self):
        self.fixture()
        extra = self.root / "extra.json"
        extra.write_bytes(b"{}")
        self.plan["extras"] = [
            {
                "source_path": str(extra),
                "archive_path": "extra.json",
                "bytes": 2,
                "sha256": "0" * 64,
                "provenance": "synthetic",
            }
        ]
        self.save_plan()
        self.rejects("Entry SHA-256")
        renamed = self.root / "program.py"
        renamed.write_bytes(b"{}")
        self.plan["extras"][0]["source_path"] = str(renamed)
        self.save_plan()
        self.rejects("suffix is forbidden")

    def test_snapshot_components_cannot_be_omitted(self):
        receipt = {
            "receipt_path": "C:/snapshot.receipt.json",
            "snapshot_sha256": "0" * 64,
            "status": "ok",
            "integrity_ok": True,
        }
        maps = [
            {
                "source_archive_path": "original.db",
                "snapshot_archive_path": "snapshot.sqlite3",
                "snapshot_sha256": "0" * 64,
                "receipt": receipt,
            }
        ]
        self.fixture(
            {"original.db": b"x", "snapshot.sqlite3": b"x", "snapshot.receipt.json": b"{}"},
            selected=["original.db", "snapshot.sqlite3"],
            maps=maps,
        )
        self.rejects("source/snapshot/receipt")

    def test_nested_zip_is_recursive_and_never_accepts_code(self):
        self.fixture({"cache.zip": zipped({"child.zip": zipped({"data.csv": b"x,y\n"})})})
        self.assertEqual("PASS", self.build()["status"])
        with self.assertRaisesRegex(ValueError, "suffix is forbidden"):
            builder._nested_zip(io.BytesIO(zipped({"child.zip": zipped({"hidden.py.bak": b"x"})})))
        with self.assertRaisesRegex(ValueError, "unapproved data type"):
            builder._nested_zip(io.BytesIO(zipped({"script.txt": b"ambiguous"})))
        with self.assertRaisesRegex(ValueError, "path is forbidden"):
            builder._nested_zip(io.BytesIO(zipped({"cache/.git/": b""})))

    def test_nested_zip_rejects_traversal_collisions_depth_and_size_budget(self):
        for files in ({"../x.csv": b"x"}, {"A.csv": b"x", "a.csv": b"y"}):
            with self.subTest(files=list(files)), self.assertRaises(ValueError):
                builder._nested_zip(io.BytesIO(zipped(files)))
        nested = zipped({"data.csv": b"data"})
        for _ in range(builder.MAX_NESTED_DEPTH):
            nested = zipped({"child.zip": nested})
        with self.assertRaisesRegex(ValueError, "depth"):
            builder._nested_zip(io.BytesIO(nested))
        with self.assertRaisesRegex(ValueError, "budget"):
            builder._nested_zip(
                io.BytesIO(zipped({"data.csv": b"x"})),
                budget={"entries": builder.MAX_NESTED_ENTRIES, "expanded_bytes": 0, "archives": 0},
            )

    def test_windows_name_policy_and_source_suffix_chains(self):
        forbidden = [
            "app.py.bak",
            "Worker.cs.snapshot",
            "test.ipynb",
            "change.patch",
            "change.diff",
            "x.csproj",
            "Directory.Build.props",
            "x.targets",
            "x.exe",
            "x.dll",
            "data.tar.gz",
            "old/.GIT/config",
            "copy/.venv/data.json",
            "__pycache__/x.json",
            "x/bin/data.json",
            "x/obj/data.json",
            "package-lock.json",
            "pyproject.toml",
            "requirements-dev.txt",
            "../x.csv",
            "x//y.csv",
            "/absolute.csv",
            "a\\b.csv",
            "CON.txt",
            "data.json:stream",
            "x?.csv",
        ]
        for name in forbidden:
            with self.subTest(name=name), self.assertRaises(ValueError):
                builder._check_payload_name(name)
        for name in ("config.yaml", ".env", "data.db-wal", "old/run.lock", "model.pkl"):
            builder._check_payload_name(name)

    def test_source_or_extra_windows_collisions_fail(self):
        self.fixture({"A.csv": b"x", "a.csv": b"y"})
        self.rejects("colliding ZIP")
        self.fixture({"data": b"x", "data/file.csv": b"y"})
        self.rejects("parent directory")
        self.fixture({"caf\u00e9.csv": b"x", "cafe\u0301.csv": b"y"})
        self.rejects("colliding ZIP")

    def test_references_are_full_and_do_not_embed_credentials(self):
        for commit, remote in (("abcdef", REMOTE), (COMMIT, "https://user:token@example.com/repo.git")):
            with self.subTest(commit=commit), self.assertRaises(ValueError):
                builder._validate_code_reference(commit, remote)
        builder._validate_code_reference(COMMIT, "ssh://git@github.com/example/repo.git")


if __name__ == "__main__":
    unittest.main()
