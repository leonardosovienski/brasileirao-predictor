"""Synthetic-only measurement of SQLite's read-only WAL side effects."""
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

root = Path(__file__).resolve().parent / "synthetic_tests" / ("probe_" + uuid.uuid4().hex)
root.mkdir(parents=True, exist_ok=False)
source = root / "synthetic.db"
writer = sqlite3.connect(source)
writer.execute("PRAGMA journal_mode=WAL")
writer.execute("PRAGMA wal_autocheckpoint=0")
writer.execute("CREATE TABLE synthetic_rows(value INTEGER)")
writer.commit()
writer.execute("PRAGMA wal_checkpoint(TRUNCATE)")  # Synthetic fixture only.
writer.execute("INSERT INTO synthetic_rows VALUES (42)")
writer.commit()

def hashes():
    return {suffix: hashlib.sha256(Path(str(source) + suffix).read_bytes()).hexdigest()
            for suffix in ("", "-wal", "-shm")}

before = hashes()
reader = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)
target = sqlite3.connect(root / "copy.db")
reader.backup(target)
during = hashes()
reader.close()
after = hashes()
print(json.dumps({"sqlite_version": sqlite3.sqlite_version, "source": str(source),
                  "before": before, "during": during, "after": after,
                  "copied_rows": target.execute("SELECT COUNT(*) FROM synthetic_rows").fetchone()[0]}))
target.close()
writer.close()
