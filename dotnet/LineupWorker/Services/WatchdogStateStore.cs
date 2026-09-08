namespace LineupWorker.Services;

/// <summary>Durable discovery and snapshot-conditional repair of lineup timeout tracking.</summary>
public static class WatchdogStateStore
{
    // KEYS: watchdog index. ARGV: scan cursor. Reply: cursor, server time ms, due match IDs.
    public const string ReadDue = """
        local kind = redis.call('TYPE', KEYS[1]).ok
        if kind ~= 'none' and kind ~= 'zset' then error('invalid watchdog index type') end
        local now = redis.call('TIME')
        local nowMs = now[1] * 1000 + math.floor(now[2] / 1000)
        local scanned = redis.call('ZSCAN', KEYS[1], ARGV[1], 'COUNT', '32')
        local result = {scanned[1], string.format('%.0f', nowMs)}
        for i = 1, #scanned[2], 2 do
            if tonumber(scanned[2][i + 1]) <= nowMs then result[#result + 1] = scanned[2][i] end
        end
        return result
        """;

    // KEYS: lineup, current, watchdog index.
    // ARGV: expectedStateExists, expectedState, expectedCurrentExists, expectedCurrent, matchId.
    // No state rewrite or provider timestamp invention: the stored snapshot is authoritative.
    public const string Synchronize = """
        local stateKind = redis.call('TYPE', KEYS[1]).ok
        local currentKind = redis.call('TYPE', KEYS[2]).ok
        local indexKind = redis.call('TYPE', KEYS[3]).ok
        if (stateKind ~= 'none' and stateKind ~= 'string') or
           (currentKind ~= 'none' and currentKind ~= 'string') or
           (indexKind ~= 'none' and indexKind ~= 'zset') then error('invalid watchdog key type') end
        local state = redis.call('GET', KEYS[1])
        local current = redis.call('GET', KEYS[2])
        if (ARGV[1] == '0' and state) or (ARGV[1] == '1' and state ~= ARGV[2]) then return 0 end
        if (ARGV[3] == '0' and current) or (ARGV[3] == '1' and current ~= ARGV[4]) then return 0 end
        local deadline = nil
        if state then
            local parsed = cjson.decode(state)
            if parsed.MatchId ~= ARGV[5] then error('invalid watchdog identity') end
            local value = parsed.WatchdogDeadlineUnixMs
            if value ~= nil and value ~= cjson.null then
                if type(value) ~= 'number' or value <= 0 or value > 9007199254740991 or math.floor(value) ~= value then
                    error('invalid watchdog deadline')
                end
                if not (parsed.HomeLineupComplete and parsed.AwayLineupComplete) and
                   (current or parsed.FallbackStrategy ~= 'timeout_widen_variance') then deadline = value end
            end
        end
        if deadline then
            if not redis.acl_check_cmd('ZADD', KEYS[3], deadline, ARGV[5]) then error('watchdog write denied') end
            redis.call('ZADD', KEYS[3], deadline, ARGV[5])
        else
            if not redis.acl_check_cmd('ZREM', KEYS[3], ARGV[5]) then error('watchdog cleanup denied') end
            redis.call('ZREM', KEYS[3], ARGV[5])
        end
        return 1
        """;
}
