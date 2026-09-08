"""Hash-only verification of protected files and the frozen session backup."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys

LIVE = Path("C:/Users/Superleo13/projetos/brasileirao-predictor")
BACKUP = Path("C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07")
ROOT = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


state = json.loads((LIVE / "docs/continuation/review_2026-09-07/estado_final.json").read_text())
protected = {path: sha(LIVE / path) == expected for path, expected in state["protected_sha256"].items()}
receipt = {"checked_at_utc": datetime.now(UTC).isoformat(), "protected_matches": protected}
if "--backup" in sys.argv:
    manifest_path = BACKUP / "BACKUP_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    expected_manifest = json.loads((LIVE / "docs/continuation/backup_receipt.json").read_text())["manifest_sha256"]
    failures = []
    for item in manifest["files"]:
        path = (BACKUP / item["path"]).resolve()
        if not path.is_relative_to(BACKUP) or not path.is_file():
            failures.append(item["path"])
        elif path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            failures.append(item["path"])
    receipt.update({"backup_manifest_matches": sha(manifest_path) == expected_manifest,
                    "backup_files_checked": len(manifest["files"]), "backup_failures": failures})
receipt["passed"] = all(protected.values()) and receipt.get("backup_manifest_matches", True) and not receipt.get("backup_failures")
target = ROOT / "validation" / ("integrity_before.json" if "--backup" in sys.argv else "integrity_after.json")
target.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, indent=2))
raise SystemExit(0 if receipt["passed"] else 1)
