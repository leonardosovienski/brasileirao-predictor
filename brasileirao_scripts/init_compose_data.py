"""Create isolated empty Compose databases and deterministic kernel parameters."""

import os

from brasileirao_predictor import db
from brasileirao_predictor.cron_update_models import config_hash
from brasileirao_predictor.ingest import load_config


def main() -> int:
    sports_path = os.environ["SPORTS_DB_PATH"]
    market_path = os.environ["MARKET_DB_PATH"]
    cfg = load_config()
    sports = db.connect(sports_path)
    db.save_params(sports, 0.2, 1.0, 0.1, 0.0, 0, config_hash(cfg), "2026-01-01T00:00:00Z")
    sports.commit()
    sports.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    sports.execute("PRAGMA journal_mode=DELETE")
    sports.close()
    market = db.connect(market_path)
    market.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    market.execute("PRAGMA journal_mode=DELETE")
    market.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
