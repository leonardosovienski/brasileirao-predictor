"""Create and immediately verify a dated backup of the H9 runtime artifacts."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from src.backup_restore import create_backup, verify_backup

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    base = Path(os.environ.get("LOCALAPPDATA", ROOT / "data" / "backups"))
    destination = base / "brasileirao-predictor" / "backups" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = create_backup(destination, root=ROOT)
    manifest = verify_backup(backup)
    print(f"H9_BACKUP_VERIFIED path={backup} files={len(manifest['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
