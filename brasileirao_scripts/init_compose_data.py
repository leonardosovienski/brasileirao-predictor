"""Create isolated empty Compose databases and deterministic kernel parameters."""

import os
from datetime import UTC, datetime
from pathlib import Path

from brasileirao_predictor import db
from brasileirao_predictor.cron_update_models import config_hash
from brasileirao_predictor.ingest import load_config


def main() -> int:
    sports_path = os.environ["SPORTS_DB_PATH"]
    market_path = os.environ["MARKET_DB_PATH"]
    targets = [Path(value).resolve() for value in (sports_path, market_path)]
    if targets[0] == targets[1]:
        raise ValueError("Compose initialization requires distinct databases")
    if any(path.exists() for path in targets):
        raise FileExistsError("Compose initialization requires new empty paths; existing volume left unchanged")
    cfg = load_config()
    # Reserve both paths exclusively. A racing initializer cannot overwrite them.
    # An interrupted initialization stays visible and requires explicit inspection.
    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb"):
            pass
    sports = db.connect(sports_path)
    db.save_params(sports, 0.2, 1.0, 0.1, 0.0, 0, config_hash(cfg), datetime.now(UTC).isoformat())
    sports.commit()
    sports.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    sports.execute("PRAGMA journal_mode=DELETE")
    sports.close()
    market = db.connect(market_path)
    market.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    market.execute("PRAGMA journal_mode=DELETE")
    market.close()
    print("DEMO_PARAMETERS_ONLY: no trained model, validated market feed or capital permission")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
