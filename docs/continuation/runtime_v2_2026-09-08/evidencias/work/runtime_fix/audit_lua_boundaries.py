"""Adversarial Lua checks using only UUID synthetic keys in owned Redis DB12."""
from __future__ import annotations

import ast
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

import redis

import provision_redis_wsl as provision

REPO = Path("C:/Users/Superleo13/projetos/brasileirao-predictor")
BASELINE_SIGNALS = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return -1 end
if redis.call('GET', KEYS[2]) ~= ARGV[2] or redis.call('PTTL', KEYS[2]) <= 0 then return -2 end
local ttl = redis.call('PTTL', KEYS[3])
if ttl <= 0 or redis.call('HGET', KEYS[3], 'payload') ~= ARGV[1] then return -3 end
if redis.call('HGET', KEYS[3], 'status') ~= 'completed' then return -3 end
if redis.call('HGET', KEYS[3], 'result') ~= ARGV[2] then return -3 end
if redis.call('HGET', KEYS[3], 'lineup_state') ~= ARGV[3] then return -4 end
if redis.call('GET', KEYS[4]) ~= ARGV[3] then return -4 end
if redis.call('EXISTS', KEYS[5]) ~= 0 then return 0 end
redis.call('SET', KEYS[5], ARGV[1], 'PX', ttl)
for i = 5, #ARGV do redis.call('PUBLISH', ARGV[4], ARGV[i]) end
return #ARGV - 4
"""


def python_constants(source):
    values = {}
    def value(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return value(node.left) + value(node.right)
        raise ValueError("unexpected constant expression")
    for statement in ast.parse(source).body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            values[statement.targets[0].id] = value(statement.value)
    return values


def cs_constant(source, name):
    found = re.search(rf'const string {name} = (Checks \+ (?:"\\n" \+ )?)?"""\s*(.*?)\s*""";', source, re.S)
    if not found:
        raise ValueError(f"constant {name} missing")
    prefix = cs_constant(source, "Checks") if found.group(1) else ""
    if found.group(1) and '"\\n"' in found.group(1):
        prefix += "\n"
    return prefix + found.group(2)


def connection(username=None):
    return redis.Redis(host="127.0.0.1", port=provision.PORT, db=12, username=username,
                       password="" if username else None, decode_responses=True, socket_timeout=3)


def signals_case(default, script):
    prefix = "review-lua-" + uuid4().hex + ":"
    user = "review_lua_" + uuid4().hex
    keys = [prefix + suffix for suffix in ("current", "fair", "request", "lineup", "marker")]
    args = ["payload", "fair", "lineup", prefix + "signals", '{"synthetic":true}']
    default.set(keys[0], args[0], px=30000)
    default.set(keys[1], args[1], px=30000)
    default.hset(keys[2], mapping={"payload": args[0], "status": "completed", "result": args[1], "lineup_state": args[2]})
    default.pexpire(keys[2], 30000)
    default.set(keys[3], args[2], px=30000)
    restricted = None
    try:
        default.execute_command("ACL", "SETUSER", user, "on", "nopass", "~" + prefix + "*", "&" + prefix + "*", "+@all", "-publish")
        restricted = connection(user)
        try:
            restricted.eval(script, len(keys), *keys, *args)
            failure = None
        except redis.ResponseError as exc:
            failure = str(exc)
        marker_after_denial = default.get(keys[4])
        replay = default.eval(script, len(keys), *keys, *args)
        return {"script_sha256": hashlib.sha256(script.encode()).hexdigest(), "acl_denial": failure,
                "marker_written_despite_failed_publish": marker_after_denial is not None,
                "allowed_replay_result": replay}
    finally:
        if restricted is not None:
            restricted.close()
        default.execute_command("ACL", "DELUSER", user)
        default.delete(*keys)


def completion_case(default, script):
    prefix = "review-lua-" + uuid4().hex + ":"
    user = "review_lua_" + uuid4().hex
    run = prefix + "run"
    keys = [prefix + suffix for suffix in ("current", "request", "lease", "fair", "pending", "lineup")]
    request = {"protocol_version": "brasileirao.redis/2", "run_id": run, "job_id": prefix + "job",
               "match_id": prefix + "match", "idempotency_key": prefix + "idem", "state_version": "1"}
    payload, fair = json.dumps(request), json.dumps(request | {"1": 2.0})
    channel = prefix + "ready"
    default.set(keys[0], payload, px=30000)
    default.hset(keys[1], mapping={"payload": payload, "status": "pending", "lineup_state": "lineup"})
    default.pexpire(keys[1], 30000)
    default.set(keys[2], "token", px=5000)
    default.zadd(keys[4], {run: 0})
    default.set(keys[5], "lineup", px=30000)
    pubsub = default.pubsub()
    restricted = None
    try:
        pubsub.subscribe(channel)
        pubsub.get_message(ignore_subscribe_messages=False, timeout=2)
        default.execute_command("ACL", "SETUSER", user, "on", "nopass", "~" + prefix + "*", "&" + prefix + "*", "+@all", "-hset")
        restricted = connection(user)
        try:
            reply = restricted.eval(script, len(keys), *keys, payload, run, "token", fair, 5000, channel, 250)
            failure = None
        except redis.ResponseError as exc:
            reply, failure = None, str(exc)
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.2)
        return {"script_sha256": hashlib.sha256(script.encode()).hexdigest(), "reply": reply, "acl_denial": failure,
                "request_status": default.hget(keys[1], "status"), "fair_written": default.exists(keys[3]) == 1,
                "notification_observed": message is not None, "lease_still_owned": default.get(keys[2]) == "token"}
    finally:
        pubsub.close()
        if restricted is not None:
            restricted.close()
        default.execute_command("ACL", "DELUSER", user)
        default.delete(*keys)


def main():
    cs_path = REPO / "dotnet/LineupWorker/Services/KernelRedisProtocolV2.cs"
    py_path = REPO / "brasileirao_predictor/kernel_redis_v2.py"
    cs_bytes, py_bytes = cs_path.read_bytes(), py_path.read_bytes()
    cs_source, py_source = cs_bytes.decode("utf-8"), py_bytes.decode("utf-8")
    ready = json.loads((provision.BASE / "ready.json").read_text(encoding="utf-8"))
    result = {"at_utc": datetime.now(UTC).isoformat(), "redis_url": "redis://127.0.0.1:26380/12",
              "run_id": ready["run_id"], "synthetic_only": True, "no_global_cleanup": True,
              "source_hashes": {str(cs_path): hashlib.sha256(cs_bytes).hexdigest(), str(py_path): hashlib.sha256(py_bytes).hexdigest()}}
    target = Path(__file__).resolve().parent / ("lua_boundary_audit_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S"))
    target.mkdir(exist_ok=False)
    (target / "KernelRedisProtocolV2.cs.snapshot").write_bytes(cs_bytes)
    (target / "kernel_redis_v2.py.snapshot").write_bytes(py_bytes)
    default = connection()
    try:
        assert default.info("server")["run_id"] == ready["run_id"]
        result["dbsize_before"] = default.dbsize()
        result["signals_baseline"] = signals_case(default, BASELINE_SIGNALS)
        try:
            result["signals_current"] = signals_case(default, cs_constant(cs_source, "PublishSignals"))
        except redis.ResponseError as exc:
            result["signals_current"] = {"unexpected_script_error": str(exc)}
        result["python_completion_current"] = completion_case(default, python_constants(py_source)["COMPLETE_SCRIPT"])
        result["dbsize_after"] = default.dbsize()
    finally:
        default.close()
        (target / "audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
