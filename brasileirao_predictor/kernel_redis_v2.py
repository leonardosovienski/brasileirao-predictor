"""Atomic Redis lifecycle for the v2 kernel; no IO occurs on import.

The .NET producer owns registration and final signal publication. These scripts
consume its immutable request/current bytes. TTLs use Redis time, never the
publisher timestamp. Redis Pub/Sub has no subscriber delivery acknowledgement.
"""

PROTOCOL_VERSION = "brasileirao.redis/2"
INVOKE_CHANNEL = "system:invoke_kernel:v2"
CURRENT_PREFIX = "kernel:v2:current:"
REQUEST_PREFIX = "kernel:v2:request:"
LEASE_PREFIX = "kernel:v2:lease:"
PENDING_KEY = "kernel:v2:pending"
READY_KEY = "kernel:v2:ready"
LEASE_MS = 5000
FAIR_MS = 5000
RETRY_MS = 250
POLL_SECONDS = 0.25
POLL_LIMIT = 32
HEALTH_KEY = "health:kernel"
HEALTH_MS = 5000

_HELPERS = """
local function kind(key)
    return redis.call('TYPE', key).ok
end
local function allowed(key, expected)
    local actual = kind(key)
    return actual == 'none' or actual == expected
end
local function now_ms()
    local clock = redis.call('TIME')
    return tonumber(clock[1]) * 1000 + math.floor(tonumber(clock[2]) / 1000)
end
"""

# KEYS health; ARGV session payload JSON, ttl_ms, start|renew|release.
HEARTBEAT_SCRIPT = (
    "-- kernel-v2:heartbeat\n"
    + _HELPERS
    + """
if not allowed(KEYS[1], 'string') then return redis.error_reply('invalid health key type') end
local valid, message = pcall(cjson.decode, ARGV[1])
local ttl = tonumber(ARGV[2])
local mode = ARGV[3]
if not valid or type(message) ~= 'table' or message.protocol_version ~= 'brasileirao.redis/2'
    or type(message.session_id) ~= 'string' or message.session_id == ''
    or not ttl or ttl < 1 or ttl > 5000
    or (mode ~= 'start' and mode ~= 'renew' and mode ~= 'release') then
    return redis.error_reply('invalid heartbeat arguments')
end
local current = redis.call('GET', KEYS[1])
if mode == 'release' then
    if current ~= ARGV[1] then return 0 end
    if not redis.acl_check_cmd('DEL', KEYS[1]) then return redis.error_reply('heartbeat release denied') end
    return redis.call('DEL', KEYS[1])
end
if mode == 'renew' and current and current ~= ARGV[1] then return 0 end
if not redis.acl_check_cmd('SET', KEYS[1], ARGV[1], 'PX', ttl) then
    return redis.error_reply('heartbeat write denied')
end
redis.call('SET', KEYS[1], ARGV[1], 'PX', ttl)
return 1
"""
)

HEALTHCHECK_SCRIPT = (
    "-- kernel-v2:healthcheck\n"
    + _HELPERS
    + """
if kind(KEYS[1]) ~= 'string' or redis.call('PTTL', KEYS[1]) <= 0 then return 0 end
local valid, message = pcall(cjson.decode, redis.call('GET', KEYS[1]))
if valid and type(message) == 'table' and message.protocol_version == 'brasileirao.redis/2'
    and type(message.session_id) == 'string' and message.session_id ~= '' then return 1 end
return 0
"""
)

# KEYS current, request, lease, pending, lineup; ARGV payload, run, token, lease_ms.
CLAIM_SCRIPT = (
    "-- kernel-v2:claim\n"
    + _HELPERS
    + """
if not allowed(KEYS[1], 'string') or not allowed(KEYS[2], 'hash')
    or not allowed(KEYS[3], 'string') or not allowed(KEYS[4], 'zset')
    or not allowed(KEYS[5], 'string') then
    return 'INVALID_STATE'
end
local lease_ms = tonumber(ARGV[4])
if not lease_ms or lease_ms < 1 or lease_ms > 5000
    or ARGV[1] == '' or ARGV[2] == '' or ARGV[3] == '' then
    return 'INVALID_ARGUMENT'
end
if not redis.acl_check_cmd('SET', KEYS[3], ARGV[3], 'PX', lease_ms, 'NX')
    or not redis.acl_check_cmd('ZADD', KEYS[4], 0, ARGV[2])
    or not redis.acl_check_cmd('ZREM', KEYS[4], ARGV[2]) then return 'ACL_DENIED' end
local stored = redis.call('HGET', KEYS[2], 'payload')
if not stored then
    redis.call('ZREM', KEYS[4], ARGV[2])
    return 'EXPIRED'
end
if stored ~= ARGV[1] then return 'UNREGISTERED' end
if redis.call('GET', KEYS[1]) ~= ARGV[1]
    or not redis.call('HGET', KEYS[2], 'lineup_state')
    or redis.call('GET', KEYS[5]) ~= redis.call('HGET', KEYS[2], 'lineup_state') then
    redis.call('ZREM', KEYS[4], ARGV[2])
    return 'STALE'
end
local remaining = redis.call('PTTL', KEYS[2])
if remaining <= 0 then
    redis.call('ZREM', KEYS[4], ARGV[2])
    return 'EXPIRED'
end
local status = redis.call('HGET', KEYS[2], 'status')
if status == 'completed' then return 'COMPLETED' end
if status ~= 'pending' then return 'INVALID_STATE' end
local duration = math.min(lease_ms, remaining)
local accepted = redis.call('SET', KEYS[3], ARGV[3], 'PX', duration, 'NX')
if not accepted then
    local busy_for = redis.call('PTTL', KEYS[3])
    if busy_for > 0 then
        redis.call('ZADD', KEYS[4], now_ms() + busy_for, ARGV[2])
    end
    return 'BUSY'
end
redis.call('ZADD', KEYS[4], now_ms() + duration, ARGV[2])
return 'CLAIMED'
"""
)

# KEYS current, request, lease, fair, pending, lineup, ready;
# ARGV payload, run, token, fair_json, fair_ms, channel.
COMPLETE_SCRIPT = (
    "-- kernel-v2:complete\n"
    + _HELPERS
    + """
if not allowed(KEYS[1], 'string') or not allowed(KEYS[2], 'hash')
    or not allowed(KEYS[3], 'string') or not allowed(KEYS[4], 'string')
    or not allowed(KEYS[5], 'zset') or not allowed(KEYS[6], 'string')
    or not allowed(KEYS[7], 'zset') then return 'INVALID_STATE' end
local fair_ms = tonumber(ARGV[5])
if not fair_ms or fair_ms < 1 or fair_ms > 5000
    or ARGV[1] == '' or ARGV[2] == '' or ARGV[3] == '' or ARGV[6] == '' then
    return 'INVALID_ARGUMENT'
end
local valid, result = pcall(cjson.decode, ARGV[4])
local valid_input, request = pcall(cjson.decode, ARGV[1])
if not valid or not valid_input or type(result) ~= 'table' or type(request) ~= 'table'
    or result.protocol_version ~= 'brasileirao.redis/2'
    or result.run_id ~= ARGV[2] or request.run_id ~= ARGV[2]
    or result.match_id ~= request.match_id or result.job_id ~= request.job_id
    or result.idempotency_key ~= request.idempotency_key
    or result.state_version ~= request.state_version then return 'INVALID_ARGUMENT' end
if not redis.acl_check_cmd('SET', KEYS[4], ARGV[4], 'PX', fair_ms)
    or not redis.acl_check_cmd('PUBLISH', ARGV[6], ARGV[4])
    or not redis.acl_check_cmd('HSET', KEYS[2], 'status', 'completed', 'result', ARGV[4])
    or not redis.acl_check_cmd('ZREM', KEYS[5], ARGV[2])
    or not redis.acl_check_cmd('ZADD', KEYS[7], 0, ARGV[2])
    or not redis.acl_check_cmd('ZREM', KEYS[7], ARGV[2])
    or not redis.acl_check_cmd('PEXPIRETIME', KEYS[4])
    or not redis.acl_check_cmd('DEL', KEYS[3]) then return 'ACL_DENIED' end
local stored = redis.call('HGET', KEYS[2], 'payload')
if stored and stored ~= ARGV[1] then return 'UNREGISTERED' end
if not stored or redis.call('GET', KEYS[1]) ~= ARGV[1]
    or not redis.call('HGET', KEYS[2], 'lineup_state')
    or redis.call('GET', KEYS[6]) ~= redis.call('HGET', KEYS[2], 'lineup_state') then
    redis.call('ZREM', KEYS[5], ARGV[2])
    redis.call('ZREM', KEYS[7], ARGV[2])
    if redis.call('GET', KEYS[3]) == ARGV[3] then redis.call('DEL', KEYS[3]) end
    return 'STALE'
end
local remaining = redis.call('PTTL', KEYS[2])
if remaining <= 0 then
    redis.call('ZREM', KEYS[5], ARGV[2])
    redis.call('ZREM', KEYS[7], ARGV[2])
    if redis.call('GET', KEYS[3]) == ARGV[3] then redis.call('DEL', KEYS[3]) end
    return 'EXPIRED'
end
local status = redis.call('HGET', KEYS[2], 'status')
if status == 'completed' then
    if redis.call('PTTL', KEYS[4]) <= 0
        or redis.call('GET', KEYS[4]) ~= redis.call('HGET', KEYS[2], 'result') then
        redis.call('ZREM', KEYS[7], ARGV[2])
    end
    return 'COMPLETED'
end
if status ~= 'pending' then return 'INVALID_STATE' end
if redis.call('GET', KEYS[3]) ~= ARGV[3] then return 'LEASE_LOST' end

-- Completion and discoverability share the same atomic operation. The index
-- uses the actual key deadline, never a refreshed window on replay/recovery.
redis.call('SET', KEYS[4], ARGV[4], 'PX', math.min(fair_ms, remaining))
redis.call('ZADD', KEYS[7], redis.call('PEXPIRETIME', KEYS[4]), ARGV[2])
redis.call('HSET', KEYS[2], 'status', 'completed', 'result', ARGV[4])
redis.call('ZREM', KEYS[5], ARGV[2])
redis.call('DEL', KEYS[3])
-- Pub/Sub is a wakeup only. Even an unexpected PUBLISH error must not delete
-- a completed result or recompute it with a new economic validity window.
redis.pcall('PUBLISH', ARGV[6], ARGV[4])
return 'COMPLETED'
"""
)

# KEYS current, request, lease, pending, lineup; ARGV payload, run, token, retry_ms.
RELEASE_SCRIPT = (
    "-- kernel-v2:release\n"
    + _HELPERS
    + """
if not allowed(KEYS[1], 'string') or not allowed(KEYS[2], 'hash')
    or not allowed(KEYS[3], 'string') or not allowed(KEYS[4], 'zset')
    or not allowed(KEYS[5], 'string') then
    return 'INVALID_STATE'
end
local retry_ms = tonumber(ARGV[4])
if not retry_ms or retry_ms < 1 or retry_ms > 5000 then return 'INVALID_ARGUMENT' end
if not redis.acl_check_cmd('DEL', KEYS[3])
    or not redis.acl_check_cmd('ZADD', KEYS[4], 0, ARGV[2])
    or not redis.acl_check_cmd('ZREM', KEYS[4], ARGV[2]) then return 'ACL_DENIED' end
if redis.call('GET', KEYS[3]) ~= ARGV[3] then return 'LEASE_LOST' end
redis.call('DEL', KEYS[3])
if redis.call('GET', KEYS[1]) == ARGV[1]
    and redis.call('HGET', KEYS[2], 'payload') == ARGV[1]
    and redis.call('HGET', KEYS[2], 'status') == 'pending'
    and redis.call('HGET', KEYS[2], 'lineup_state')
    and redis.call('GET', KEYS[5]) == redis.call('HGET', KEYS[2], 'lineup_state')
    and redis.call('PTTL', KEYS[2]) > 0 then
    redis.call('ZADD', KEYS[4], now_ms() + retry_ms, ARGV[2])
    return 'RETRY'
end
redis.call('ZREM', KEYS[4], ARGV[2])
return 'STALE'
"""
)

# KEYS pending; ARGV limit, request_prefix, current_prefix, lease_prefix.
# This protocol targets the standalone Redis in Compose, not Redis Cluster.
POLL_SCRIPT = (
    "-- kernel-v2:poll\n"
    + _HELPERS
    + """
if not allowed(KEYS[1], 'zset') then return redis.error_reply('invalid pending key type') end
local limit = tonumber(ARGV[1])
if not limit or limit < 1 or limit > 256 or limit ~= math.floor(limit) then
    return redis.error_reply('invalid poll limit')
end
local now = now_ms()
local runs = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', now, 'LIMIT', 0, limit)
for _, run in ipairs(runs) do
    if not redis.acl_check_cmd('ZREM', KEYS[1], run)
        or not redis.acl_check_cmd('ZADD', KEYS[1], 0, run) then
        return redis.error_reply('pending mutation permission denied')
    end
end
local payloads = {}
for _, run in ipairs(runs) do
    local request_key = ARGV[2] .. run
    local lease_key = ARGV[4] .. run
    local payload = false
    if kind(request_key) == 'hash' and redis.call('PTTL', request_key) > 0
        and redis.call('HGET', request_key, 'status') == 'pending' then
        payload = redis.call('HGET', request_key, 'payload')
    end
    local valid, request = false, false
    if payload then valid, request = pcall(cjson.decode, payload) end
    local current = false
    if valid and type(request) == 'table' and request.run_id == run
        and type(request.match_id) == 'string' then
        local current_key = ARGV[3] .. request.match_id
        if kind(current_key) == 'string' then current = redis.call('GET', current_key) end
    end
    if not payload or current ~= payload then
        redis.call('ZREM', KEYS[1], run)
    elseif allowed(lease_key, 'string') then
        local busy_for = redis.call('PTTL', lease_key)
        if busy_for > 0 then
            redis.call('ZADD', KEYS[1], now + busy_for, run)
        elseif busy_for == -2 then
            table.insert(payloads, payload)
        end
    end
end
return payloads
"""
)
