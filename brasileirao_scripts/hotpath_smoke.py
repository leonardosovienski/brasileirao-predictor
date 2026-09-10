"""Verify a request already registered by the v2 .NET producer.

This check never manufactures a current run, bypasses registration, or refreshes
the request/fair-odds TTL. It may send the existing immutable request as a wakeup.
It verifies Redis/kernel plumbing, not profitability or external execution.

Usage: python -m brasileirao_scripts.hotpath_smoke --match-id MATCH --redis URL
"""

import argparse
import json
import math
import os
import time
from datetime import UTC, datetime
from uuid import uuid4

import redis

from brasileirao_scripts.lineup_inbox import enqueue_lineup

_READ_RESULT = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return {'superseded'} end
if redis.call('HGET', KEYS[2], 'payload') ~= ARGV[1] then return {'unregistered'} end
if redis.call('PTTL', KEYS[2]) <= 0 then return {'expired'} end
local snapshot = redis.call('HGET', KEYS[2], 'lineup_state')
if not snapshot or redis.call('GET', KEYS[4]) ~= snapshot then return {'inconsistent'} end
if redis.call('HGET', KEYS[2], 'status') ~= 'completed' then return {'pending'} end
local fair = redis.call('GET', KEYS[3])
if not fair or redis.call('PTTL', KEYS[3]) <= 0 then return {'expired'} end
if redis.call('HGET', KEYS[2], 'result') ~= fair then return {'inconsistent'} end
return {'ready', fair}
"""


def register_synthetic_lineup(client, *, timeout: float = 10.0) -> str:
    """Exercise the actual Worker producer through fabricated lineup events.

    Intended for a disposable Compose/test environment. This never writes
    current/request keys; the .NET Worker owns all protocol registration.
    """
    match = "synthetic-smoke-" + uuid4().hex
    deadline = time.perf_counter() + timeout
    for side in ("home", "away"):
        event = {
            "MatchId": match,
            "HomeTeam": "SYNTHETIC_HOME",
            "AwayTeam": "SYNTHETIC_AWAY",
            "Side": side,
            "Starters": [f"SYNTHETIC_{side}_{index}" for index in range(11)],
            "Subs": [],
            "CapturedAt": datetime.now(UTC).isoformat(),
        }
        enqueue_lineup(client, event)
    while time.perf_counter() < deadline:
        current = client.get(f"kernel:v2:current:{match}")
        if current:
            request = json.loads(current)
            state = client.hget(f"kernel:v2:request:{request['run_id']}", "lineup_state")
            if state:
                snapshot = json.loads(state)
                if snapshot.get("HomeLineupComplete") is True and snapshot.get("AwayLineupComplete") is True:
                    return match
        time.sleep(0.05)
    raise TimeoutError("Worker did not register both synthetic lineup sides")


def verify_registered_request(client, match_id: str, *, timeout: float = 5.0) -> dict:
    """Read the current registered result or wake a still-pending request."""
    from brasileirao_predictor.kernel_message import parse_invoke as _parse_invoke

    current_key = f"kernel:v2:current:{match_id}"
    current = client.get(current_key)
    if not current:
        raise ValueError("no current registered v2 request")
    request = _parse_invoke(current.encode() if isinstance(current, str) else current)
    if request["match_id"] != match_id:
        raise ValueError("invalid registered v2 request")
    request_key = f"kernel:v2:request:{request['run_id']}"
    if client.hget(request_key, "payload") != current:
        raise ValueError("request registration is missing or inconsistent")

    started = time.perf_counter()
    # Pub/Sub is only a wakeup. Completed requests cannot be recomputed or have
    # their lifetime extended. Pending recovery also runs in the daemon.
    client.publish("system:invoke_kernel:v2", current)
    deadline = started + timeout
    while True:
        response = client.eval(
            _READ_RESULT, 4, current_key, request_key, f"fair_odds:{match_id}", f"lineup_state:{match_id}", current
        )
        status = response[0]
        if status == "ready":
            fair = json.loads(response[1])
            if not isinstance(fair, dict) or any(
                fair.get(field) != request[field]
                for field in ("protocol_version", "job_id", "run_id", "match_id", "state_version", "idempotency_key")
            ):
                raise ValueError("result does not match the registered request")
            for field in ("1", "X", "2", "o25", "u25"):
                if field not in fair:
                    raise ValueError("incomplete fair-odds result")
                value = fair[field]
                if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 1):
                    raise ValueError("invalid fair-odds result")
            return {"status": "VERIFIED_CURRENT_RESULT", "verification_ms": (time.perf_counter() - started) * 1000}
        if status != "pending":
            raise ValueError("current result is superseded, expired or inconsistent")
        if time.perf_counter() >= deadline:
            raise TimeoutError("registered request has not completed within the verification window")
        time.sleep(min(0.05, max(0, deadline - time.perf_counter())))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify an already registered v2 kernel request")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--match-id")
    selection.add_argument(
        "--synthetic-lineup",
        action="store_true",
        help="exercise the Worker using fabricated lineups in a disposable environment",
    )
    parser.add_argument("--n", type=int, default=1, help="verification count; does not create new invocations")
    parser.add_argument("--redis", default=os.environ.get("REDIS_URL"))
    args = parser.parse_args(argv)
    if not args.redis:
        parser.error("--redis or REDIS_URL is required")
    if args.n < 1 or (args.match_id is not None and not args.match_id.strip()):
        parser.error("a nonempty match ID and positive verification count are required")
    client = redis.from_url(args.redis, decode_responses=True)
    try:
        client.ping()
        results = []
        for _ in range(args.n):
            match = register_synthetic_lineup(client) if args.synthetic_lineup else args.match_id
            if not isinstance(match, str):
                raise ValueError("an explicit match ID is required")
            results.append(verify_registered_request(client, match))
    except (redis.RedisError, ValueError, TypeError, KeyError, TimeoutError, OverflowError):
        # Never print URLs, credentials or arbitrary provider/input fragments.
        print("[smoke] FAIL: v2 registration, Redis or current result could not be verified.")
        return 1
    finally:
        client.close()
    print(json.dumps({"status": "PASS", "verified": len(results), "results": results}))
    print("[smoke] Verification timings are not new kernel-compute or economic measurements.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
