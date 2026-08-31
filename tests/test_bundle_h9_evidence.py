import hashlib
from datetime import UTC, datetime

from brasileirao_scripts.bundle_h9_evidence import build_manifest


def test_bundle_manifest_records_hash_rows_commit_and_capital_lock(tmp_path):
    ledger = tmp_path / "h9.jsonl"
    content = '{"id":1}\n{"id":2}\n'
    ledger.write_text(content, encoding="utf-8")

    manifest = build_manifest((ledger,), generated_at=datetime(2026, 8, 24, tzinfo=UTC), commit="abc123")

    assert manifest["schema_version"] == "h9-evidence-bundle/1"
    assert manifest["source_commit"] == "abc123"
    assert manifest["capital_enabled"] is False
    assert manifest["missing_historical_windows_recoverable"] is False
    assert manifest["files"][0]["rows"] == 2
    assert manifest["files"][0]["sha256"] == hashlib.sha256(ledger.read_bytes()).hexdigest()
