namespace LineupWorker.Services;

/// <summary>Redis standalone atomic boundaries; no model or betting formulas.</summary>
public static class KernelRedisProtocolV2
{
    public const string InvokeChannel = "system:invoke_kernel:v2";
    public const string CurrentPrefix = "kernel:v2:current:";
    public const string SequencePrefix = "kernel:v2:sequence:";
    public const string RequestPrefix = "kernel:v2:request:";
    public const string IdentityPrefix = "kernel:v2:identity:";
    public const string LeasePrefix = "kernel:v2:lease:";
    public const string SignalsPrefix = "kernel:v2:signals:";
    public const string PendingKey = "kernel:v2:pending";
    public const string ReadyKey = "kernel:v2:ready";
    public const string SignalOutboxKey = "kernel:v2:signal_outbox";
    public const string WatchdogKey = "lineup:v2:watchdogs";
    public const string VersionPlaceholder = "__REDIS_STATE_VERSION__";
    public const int RequestLifetimeMs = 60_000;

    private const string Checks = """
        local function kind(key, expected)
            local actual = redis.call('TYPE', key).ok
            if actual ~= 'none' and actual ~= expected then error('invalid protocol key type') end
        end
        local function allow(...)
            if not redis.acl_check_cmd or not redis.acl_check_cmd(...) then
                error('protocol command permission unavailable')
            end
        end
        local function ttl(value)
            if not string.match(value, '^%d+$') or tonumber(value) <= 0 or tonumber(value) > 9007199254740991 then
                error('invalid protocol TTL')
            end
        end
        local function run(payload)
            local parsed = cjson.decode(payload)
            if type(parsed) ~= 'table' or type(parsed.run_id) ~= 'string' or parsed.run_id == '' then
                error('invalid current invocation')
            end
            return parsed.run_id
        end
        local function watchdogDeadline(state)
            local value = state.WatchdogDeadlineUnixMs
            if value == nil or value == cjson.null then return nil end
            if type(value) ~= 'number' or value <= 0 or value > 9007199254740991 or math.floor(value) ~= value then
                error('invalid watchdog deadline')
            end
            return value
        end
        """;

    // KEYS: lineup, current, sequence, new request, identity, fair, pending, ready, watchdog.
    // ARGV: expectedExists, expectedLineup, updatedLineup, invokeTemplate,
    //       stateTtlMs, requestTtlMs, invokeChannel, requestPrefix, leasePrefix,
    //       optionalCompleteNotification, completeChannel.
    // Never cjson.encode the invocation: Redis Lua's JSON number formatting can
    // round the model inputs. Substitute only the known string version field.
    public const string Register = Checks + "\n" + """
        kind(KEYS[1], 'string'); kind(KEYS[2], 'string'); kind(KEYS[3], 'string')
        kind(KEYS[4], 'hash'); kind(KEYS[5], 'string'); kind(KEYS[6], 'string'); kind(KEYS[7], 'zset'); kind(KEYS[8], 'zset'); kind(KEYS[9], 'zset')
        ttl(ARGV[5]); ttl(ARGV[6])
        if ARGV[6] ~= '60000' then error('invalid request lifetime') end
        local updated = cjson.decode(ARGV[3])
        local request = cjson.decode(ARGV[4])
        if type(updated) ~= 'table' or type(request) ~= 'table' or
           request.protocol_version ~= 'brasileirao.redis/2' or
           request.state_version ~= '__REDIS_STATE_VERSION__' or
           updated.MatchId ~= request.match_id or updated.DeltaVorpHome ~= request.dvorp_a or
           updated.DeltaVorpAway ~= request.dvorp_b then error('invalid registration snapshot') end
        local newRun = run(ARGV[4])
        local deadline = watchdogDeadline(updated)
        local needsWatchdog = deadline and not (updated.HomeLineupComplete and updated.AwayLineupComplete)
        local identity = redis.call('GET', KEYS[5])
        if identity then
            kind(ARGV[8] .. identity, 'hash')
            local original = redis.call('HGET', ARGV[8] .. identity, 'payload')
            local snapshot = redis.call('HGET', ARGV[8] .. identity, 'lineup_state')
            if original and snapshot and redis.call('GET', KEYS[2]) == original and redis.call('GET', KEYS[1]) == snapshot then
                local canonical = cjson.decode(snapshot)
                local originalDeadline = watchdogDeadline(canonical)
                if originalDeadline and not (canonical.HomeLineupComplete and canonical.AwayLineupComplete) then
                    allow('ZADD', KEYS[9], originalDeadline, canonical.MatchId)
                    redis.call('ZADD', KEYS[9], originalDeadline, canonical.MatchId)
                else
                    allow('ZREM', KEYS[9], canonical.MatchId)
                    redis.call('ZREM', KEYS[9], canonical.MatchId)
                end
                return {'duplicate', original}
            end
            return {'superseded', original or ''}
        end
        local state = redis.call('GET', KEYS[1])
        if (ARGV[1] == '0' and state) or (ARGV[1] == '1' and state ~= ARGV[2]) then
            return {'conflict', ''}
        end
        if state then
            local originalDeadline = watchdogDeadline(cjson.decode(state))
            if originalDeadline and deadline ~= originalDeadline then error('watchdog deadline cannot move') end
        end
        local marker = '"state_version":"__REDIS_STATE_VERSION__"'
        if not string.find(ARGV[4], marker, 1, true) then
            return redis.error_reply('invalid invocation version placeholder')
        end
        if KEYS[4] ~= ARGV[8] .. newRun then
            return redis.error_reply('request key does not match invocation')
        end
        if redis.call('EXISTS', KEYS[4]) ~= 0 then
            return redis.error_reply('run identity already exists')
        end
        local old = redis.call('GET', KEYS[2])
        local oldRun = old and run(old) or nil
        local sequence = redis.call('GET', KEYS[3])
        if sequence and (not string.match(sequence, '^%d+$') or #sequence > 19 or
            (#sequence == 19 and sequence >= '9223372036854775807')) then error('invalid sequence') end
        allow('INCR', KEYS[3])
        allow('SET', KEYS[1], ARGV[3], 'PX', ARGV[5])
        allow('SET', KEYS[2], ARGV[4], 'PX', ARGV[5])
        allow('HSET', KEYS[4], 'payload', ARGV[4], 'lineup_state', ARGV[3], 'status', 'pending')
        allow('PEXPIRE', KEYS[4], ARGV[6])
        allow('SET', KEYS[5], newRun, 'PX', ARGV[6])
        allow('DEL', KEYS[6])
        allow('ZADD', KEYS[7], '0', newRun)
        if needsWatchdog then allow('ZADD', KEYS[9], deadline, updated.MatchId)
        else allow('ZREM', KEYS[9], updated.MatchId) end
        if oldRun then
            allow('ZREM', KEYS[7], oldRun)
            allow('ZREM', KEYS[8], oldRun)
            allow('DEL', ARGV[9] .. oldRun)
        end
        redis.call('INCR', KEYS[3])
        local version = redis.call('GET', KEYS[3])
        local payload = string.gsub(ARGV[4], marker, '"state_version":"' .. version .. '"', 1)
        local now = redis.call('TIME')
        local nowMs = now[1] * 1000 + math.floor(now[2] / 1000)
        redis.call('SET', KEYS[1], ARGV[3], 'PX', ARGV[5])
        redis.call('SET', KEYS[2], payload, 'PX', ARGV[5])
        redis.call('HSET', KEYS[4], 'payload', payload, 'lineup_state', ARGV[3], 'status', 'pending')
        redis.call('PEXPIRE', KEYS[4], ARGV[6])
        redis.call('SET', KEYS[5], newRun, 'PX', ARGV[6])
        redis.call('DEL', KEYS[6])
        if oldRun then
            redis.call('ZREM', KEYS[7], oldRun)
            redis.call('ZREM', KEYS[8], oldRun)
            redis.call('DEL', ARGV[9] .. oldRun)
        end
        redis.call('ZADD', KEYS[7], nowMs, newRun)
        if needsWatchdog then redis.call('ZADD', KEYS[9], deadline, updated.MatchId)
        else redis.call('ZREM', KEYS[9], updated.MatchId) end
        if ARGV[10] ~= '' then redis.pcall('PUBLISH', ARGV[11], ARGV[10]) end
        redis.pcall('PUBLISH', ARGV[7], payload)
        return {'registered', payload}
        """;

    // KEYS: current, fair, request, lineup, emitted marker, ready, signal outbox.
    // ARGV: exact current payload, exact fair payload, exact lineup snapshot,
    //       signal channel, individual immutable signal JSON strings...
    // The bounded outbox and deduplication share the final fence. Pub/Sub is
    // only an optional low-latency notification after the batch is retained.
    public const string PublishSignals = Checks + "\n" + """
        kind(KEYS[1], 'string'); kind(KEYS[2], 'string'); kind(KEYS[3], 'hash')
        kind(KEYS[4], 'string'); kind(KEYS[5], 'string'); kind(KEYS[6], 'zset'); kind(KEYS[7], 'stream')
        if redis.call('GET', KEYS[1]) ~= ARGV[1] then return -1 end
        if redis.call('GET', KEYS[2]) ~= ARGV[2] or redis.call('PTTL', KEYS[2]) <= 0 then return -2 end
        local ttl = redis.call('PTTL', KEYS[3])
        if ttl <= 0 or redis.call('HGET', KEYS[3], 'payload') ~= ARGV[1] then return -3 end
        if redis.call('HGET', KEYS[3], 'status') ~= 'completed' then return -3 end
        if redis.call('HGET', KEYS[3], 'result') ~= ARGV[2] then return -3 end
        if redis.call('HGET', KEYS[3], 'lineup_state') ~= ARGV[3] then return -4 end
        if redis.call('GET', KEYS[4]) ~= ARGV[3] then return -4 end
        local invocation = cjson.decode(ARGV[1])
        local runId = run(ARGV[1])
        if type(invocation.match_id) ~= 'string' or type(invocation.state_version) ~= 'string' or
           type(invocation.job_id) ~= 'string' or invocation.protocol_version ~= 'brasileirao.redis/2' then
            error('invalid outbox identity')
        end
        allow('ZREM', KEYS[6], runId)
        if redis.call('EXISTS', KEYS[5]) ~= 0 then
            redis.call('ZREM', KEYS[6], runId)
            return 0
        end
        if #ARGV <= 4 then return 0 end
        local items = {}
        for i = 5, #ARGV do
            local signal = cjson.decode(ARGV[i])
            if type(signal) ~= 'table' or signal.RunId ~= runId or signal.MatchId ~= invocation.match_id or
               signal.StateVersion ~= invocation.state_version or signal.JobId ~= invocation.job_id then
                error('invalid signal batch identity')
            end
            items[#items + 1] = ARGV[i]
        end
        local batch = '[' .. table.concat(items, ',') .. ']'
        local now = redis.call('TIME')
        local deadline = string.format('%.0f', now[1] * 1000 + math.floor(now[2] / 1000) + redis.call('PTTL', KEYS[2]))
        local fields = {'protocol_version', invocation.protocol_version, 'job_id', invocation.job_id,
            'run_id', runId, 'match_id', invocation.match_id, 'state_version', invocation.state_version,
            'expires_at_ms', deadline, 'batch_json', batch}
        allow('XADD', KEYS[7], 'MAXLEN', '=', '10000', '*', unpack(fields))
        allow('SET', KEYS[5], ARGV[1], 'PX', ttl)
        redis.call('XADD', KEYS[7], 'MAXLEN', '=', '10000', '*', unpack(fields))
        redis.call('SET', KEYS[5], ARGV[1], 'PX', ttl)
        redis.call('ZREM', KEYS[6], runId)
        for i = 5, #ARGV do redis.pcall('PUBLISH', ARGV[4], ARGV[i]) end
        return #ARGV - 4
        """;

    // KEYS: ready. ARGV: ZSCAN cursor. Redis time is the only expiry clock.
    // COUNT is a scan hint, not a hard bound; rotating the cursor avoids a few
    // unavailable markets monopolizing the first page until their TTL expires.
    public const string ReadReady = Checks + "\n" + """
        kind(KEYS[1], 'zset')
        allow('ZSCAN', KEYS[1], ARGV[1], 'COUNT', '32')
        local now = redis.call('TIME')
        local nowMs = now[1] * 1000 + math.floor(now[2] / 1000)
        local expired = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', nowMs, 'LIMIT', '0', '32')
        for _, runId in ipairs(expired) do allow('ZREM', KEYS[1], runId) end
        for _, runId in ipairs(expired) do redis.call('ZREM', KEYS[1], runId) end
        local scanned = redis.call('ZSCAN', KEYS[1], ARGV[1], 'COUNT', '32')
        local result = {scanned[1]}
        for i = 1, #scanned[2], 2 do
            if tonumber(scanned[2][i + 1]) > nowMs then result[#result + 1] = scanned[2][i] end
        end
        return result
        """;

    // KEYS: lineup, current, fair, pending, ready, watchdog.
    // ARGV: expectedLineup, expectedCurrentExists, expectedCurrent, fallback,
    //       stateTtlMs, leasePrefix, wideningChannel, widening JSON strings...
    public const string ApplyWatchdog = Checks + "\n" + """
        kind(KEYS[1], 'string'); kind(KEYS[2], 'string'); kind(KEYS[3], 'string'); kind(KEYS[4], 'zset'); kind(KEYS[5], 'zset'); kind(KEYS[6], 'zset')
        ttl(ARGV[5])
        local fallback = cjson.decode(ARGV[4])
        if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
        local current = redis.call('GET', KEYS[2])
        if (ARGV[2] == '0' and current) or (ARGV[2] == '1' and current ~= ARGV[3]) then return 0 end
        local oldRun = current and run(current) or nil
        local original = cjson.decode(ARGV[1])
        local deadline = watchdogDeadline(original)
        local now = redis.call('TIME')
        local nowMs = now[1] * 1000 + math.floor(now[2] / 1000)
        if not deadline or deadline > nowMs or (original.HomeLineupComplete and original.AwayLineupComplete) then return 0 end
        if fallback.MatchId ~= original.MatchId or watchdogDeadline(fallback) ~= deadline then error('invalid watchdog fallback') end
        allow('SET', KEYS[1], ARGV[4], 'PX', ARGV[5])
        allow('DEL', KEYS[2], KEYS[3])
        allow('ZREM', KEYS[6], original.MatchId)
        if oldRun then
            allow('ZREM', KEYS[4], oldRun)
            allow('ZREM', KEYS[5], oldRun)
            allow('DEL', ARGV[6] .. oldRun)
        end
        for i = 8, #ARGV do allow('PUBLISH', ARGV[7], ARGV[i]) end
        redis.call('SET', KEYS[1], ARGV[4], 'PX', ARGV[5])
        redis.call('DEL', KEYS[2], KEYS[3])
        redis.call('ZREM', KEYS[6], original.MatchId)
        if oldRun then
            redis.call('ZREM', KEYS[4], oldRun)
            redis.call('ZREM', KEYS[5], oldRun)
            redis.call('DEL', ARGV[6] .. oldRun)
        end
        for i = 8, #ARGV do redis.call('PUBLISH', ARGV[7], ARGV[i]) end
        return 1
        """;
}

public sealed record KernelRegistrationResult(string Status, string? PayloadJson);
