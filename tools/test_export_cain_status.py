"""Focused stdlib checks; no producer runtime or scientific fixtures."""

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("exporter", Path(__file__).with_name("export_cain_status.py"))
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class ExportChecks(unittest.TestCase):
    def test_admission_layout_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "source"
            source = root / "docs/EVIDENCE_REGISTRY.md"
            source.parent.mkdir(parents=True)
            raw = b"".join(
                f"| CLAIM-BR-MARKET-00{n} | Claim | BLOCKED | L | Q | Evidence | Limits | Path | Decision |\n".encode()
                for n in (1, 2, 3)
            )
            source.write_bytes(raw)
            expected = hashlib.sha256(raw).hexdigest()

            def git(args, **kwargs):
                return "a" * 40 if "rev-parse" in args else b""

            with patch.object(exporter.subprocess, "check_output", side_effect=git):
                result = exporter.export(root, expected, base / "publication.json")
                self.assertEqual(result["records"], 3)
                stable = base / "stable.json"
                stamp = "2026-09-11T00:00:00Z"
                first = exporter.export(root, expected, stable, stamp)
                self.assertEqual(first, exporter.export(root, expected, stable, stamp))
                with patch.object(exporter.os, "link", side_effect=OSError("synthetic interruption")):
                    with self.assertRaises(OSError):
                        exporter.export(root, expected, base / "interrupted.json", stamp)
                self.assertFalse((base / "interrupted.json").exists())
                self.assertFalse(list(base.glob(".publication-*")))
                with self.assertRaises(FileExistsError):
                    exporter.export(root, expected, base / "publication.json")
                with self.assertRaises(ValueError):
                    exporter.export(root, "0" * 64, base / "wrong.json")
                with self.assertRaises(ValueError):
                    exporter.export(root, expected, root / "not-permitted.json")
                source.write_bytes(raw + raw)
                with self.assertRaises(ValueError):
                    exporter.export(root, hashlib.sha256(raw + raw).hexdigest(), base / "duplicate.json")
                self.assertFalse((base / "duplicate.json").exists())


if __name__ == "__main__":
    unittest.main()
