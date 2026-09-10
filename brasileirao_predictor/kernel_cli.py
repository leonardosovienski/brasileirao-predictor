"""Lightweight kernel entry point: health probes never load the numerical model."""

import argparse
import asyncio
import logging
import os
from pathlib import Path

from brasileirao_predictor import kernel_redis_v2 as protocol


def main() -> int | None:
    parser = argparse.ArgumentParser(description="Kernel Python Daemon — Zona 3")
    parser.add_argument("--db", default=os.environ.get("SPORTS_DB_PATH"))
    parser.add_argument("--redis", default=os.environ.get("REDIS_URL"))
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    if not args.db or not Path(args.db).is_absolute():
        parser.error("--db or SPORTS_DB_PATH must be an absolute path")
    if not args.redis:
        parser.error("--redis or REDIS_URL is required")

    if args.healthcheck:
        import redis

        client = None
        try:
            client = redis.from_url(args.redis, socket_connect_timeout=1, socket_timeout=1, retry_on_timeout=False)
            return 0 if client.eval(protocol.HEALTHCHECK_SCRIPT, 1, protocol.HEALTH_KEY) == 1 else 1
        except (redis.RedisError, OSError, ValueError) as exc:
            logging.getLogger(__name__).warning("kernel healthcheck failed: %s", type(exc).__name__)
            return 1
        finally:
            if client is not None:
                client.close()

    from brasileirao_predictor.kernel_daemon import _run_daemon

    asyncio.run(_run_daemon(args.db, args.redis))
    return None


if __name__ == "__main__":
    raise SystemExit(main())
