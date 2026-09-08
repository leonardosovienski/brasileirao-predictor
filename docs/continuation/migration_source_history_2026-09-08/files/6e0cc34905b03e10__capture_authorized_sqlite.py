"""Capture only the five sources explicitly authorized for this migration."""
from pathlib import Path
import json

from snapshot_sqlite import snapshot_sqlite


SOURCES = (
    "C:/Users/Superleo13/projetos/brasileirao-predictor/data/matches.db",
    "C:/Users/Superleo13/projetos/brasileirao-predictor/data/odds_operational.db",
    "C:/Users/Superleo13/projetos/brasileirao-predictor/data/research/prospective.db",
    "C:/predictor/data/output/binance_spot_microstructure.sqlite3",
    "C:/predictor/data/output/feature_store.db",
)


def main() -> int:
    output = Path(__file__).resolve().parent / "sqlite_snapshot_receipts.json"
    if output.exists():
        raise SystemExit("Aggregate receipt already exists; refusing to overwrite.")
    receipts = []
    for source in SOURCES:
        receipt = snapshot_sqlite(source)
        receipts.append(receipt)
        print(json.dumps({
            key: receipt.get(key)
            for key in (
                "source_path", "status", "snapshot_path", "snapshot_sha256",
                "snapshot_size", "integrity_ok", "failure_code", "receipt_path",
            )
        }), flush=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipts, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"aggregate_receipt": str(output), "count": len(receipts)}), flush=True)
    return 0 if all(row["status"] == "ok" for row in receipts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
