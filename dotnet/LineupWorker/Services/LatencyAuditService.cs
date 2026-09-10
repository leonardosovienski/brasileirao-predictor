using System.Text.Json;
using LineupWorker.Models;
using StackExchange.Redis;

namespace LineupWorker.Services;

/// <summary>
/// Diagnostic latency records with a bounded server-received window.
/// Values use declared capture clocks, not authenticated publication times.
/// Counters are successful calls in this process; percentiles use retained unique records.
/// </summary>
public sealed class LatencyAuditService
{
    // New namespace preserves historical v1 statistics without reinterpreting them.
    private const string SortedKey = "latency_stats:v2:e2e";
    private const string ReceivedKey = "latency_stats:v2:received";
    private const string AuditPrefix = "latency_audit:";
    private readonly IConnectionMultiplexer _redis;
    private readonly ILogger<LatencyAuditService> _log;
    private readonly double _budgetMs;
    private readonly long _retentionMs;
    private readonly int _maximumRecords;
    private long _totalRecords;
    private long _slaBreaches;

    // Prune and read atomically so a concurrent writer cannot mix percentile universes.
    // Redis TIME orders retention by receipt, independently of producer clocks or latency.
    private const string WindowScript = """
        for i = 1, 2 do
            local kind = redis.call('TYPE', KEYS[i]).ok
            if kind ~= 'none' and kind ~= 'zset' then error('invalid latency index type') end
        end
        if ARGV[1] == 'record' then
            local kind = redis.call('TYPE', KEYS[3]).ok
            if kind ~= 'none' and kind ~= 'string' then error('invalid latency record type') end
        end
        local now = redis.call('TIME')
        local nowUs = tonumber(now[1]) * 1000000 + tonumber(now[2])
        if ARGV[1] == 'record' then
            redis.call('SET', KEYS[3], ARGV[4], 'PX', ARGV[2])
            if ARGV[7] == '1' then
                redis.call('ZADD', KEYS[1], ARGV[6], ARGV[5])
                redis.call('ZADD', KEYS[2], nowUs, ARGV[5])
            else
                redis.call('ZREM', KEYS[1], ARGV[5])
                redis.call('ZREM', KEYS[2], ARGV[5])
            end
        end
        local function remove(members)
            for _, member in ipairs(members) do
                redis.call('ZREM', KEYS[1], member)
                redis.call('ZREM', KEYS[2], member)
            end
        end
        remove(redis.call('ZRANGEBYSCORE', KEYS[2], '-inf', nowUs - tonumber(ARGV[2]) * 1000))
        local excess = redis.call('ZCARD', KEYS[2]) - tonumber(ARGV[3])
        if excess > 0 then remove(redis.call('ZRANGE', KEYS[2], 0, excess - 1)) end
        redis.call('PEXPIRE', KEYS[1], ARGV[2])
        redis.call('PEXPIRE', KEYS[2], ARGV[2])
        local n = redis.call('ZCARD', KEYS[1])
        if n == 0 then return {'0', '0', '0'} end
        local result = {}
        for _, percentile in ipairs({0.50, 0.95, 0.99}) do
            local rank = math.min(math.floor(n * percentile), n - 1)
            local entry = redis.call('ZRANGE', KEYS[1], rank, rank, 'WITHSCORES')
            result[#result + 1] = entry[2]
        end
        return result
        """;

    internal const string MarkReadScript = """
        if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
        redis.call('SET', KEYS[1], ARGV[2], 'KEEPTTL')
        return 1
        """;

    public LatencyAuditService(IConnectionMultiplexer redis, ILogger<LatencyAuditService> log, IConfiguration cfg)
    {
        _redis = redis;
        _log = log;
        _budgetMs = cfg.GetValue<double>("MarketStateEngine:LatencyBudgetMs", 300);
        _maximumRecords = cfg.GetValue<int>("LatencyAudit:MaximumRecords", 10_000);
        var seconds = cfg.GetValue<int>("LatencyAudit:RetentionSeconds", 172_800);
        if (!double.IsFinite(_budgetMs) || _budgetMs <= 0)
            throw new ArgumentOutOfRangeException(nameof(cfg), "Latency budget must be positive and finite.");
        if (_maximumRecords is < 1 or > 100_000 || seconds is < 1 or > 172_800)
            throw new ArgumentOutOfRangeException(nameof(cfg), "Invalid latency retention window.");
        _retentionMs = (long)seconds * 1000;
    }

    public async ValueTask RecordAsync(LatencyRecord rec)
    {
        var validClocks = rec.NetworkLagMs >= 0 && rec.ProcessingMs >= 0 && rec.WriteMs >= 0;
        var json = JsonSerializer.Serialize(rec);
        var member = $"{rec.MatchId}:{rec.Side}:{rec.T3_RedisWritten:O}";
        await _redis.GetDatabase().ScriptEvaluateAsync(WindowScript,
            [SortedKey, ReceivedKey, string.Concat(AuditPrefix, rec.MatchId, ":", rec.Side)],
            ["record", _retentionMs, _maximumRecords, json, member, rec.E2EMs, validClocks ? "1" : "0"]);
        Interlocked.Increment(ref _totalRecords);
        if (!validClocks || !rec.IsWithinBudget(_budgetMs))
        {
            Interlocked.Increment(ref _slaBreaches);
            _log.LogWarning("[Latency] Invalid clocks or budget exceeded for {Match} {Side}: E2E={E2E:F1}ms",
                rec.MatchId, rec.Side, rec.E2EMs);
        }
    }

    /// <summary>Record the first observed market read only if the exact snapshot is still current.</summary>
    public async ValueTask MarkMarketReadAsync(string matchId, string side, DateTimeOffset t4)
    {
        var db = _redis.GetDatabase();
        var key = string.Concat(AuditPrefix, matchId, ":", side);
        var raw = await db.StringGetAsync(key);
        if (!raw.HasValue) return;
        var rec = JsonSerializer.Deserialize<LatencyRecord>(raw.ToString());
        if (rec is null || rec.MatchId != matchId || rec.Side != side ||
            rec.T4_MarketEngineRead.HasValue || t4 < rec.T3_RedisWritten) return;
        var updated = rec with { T4_MarketEngineRead = t4 };
        await db.ScriptEvaluateAsync(MarkReadScript, [key], [raw, JsonSerializer.Serialize(updated)]);
    }

    /// <summary>Percentiles of retained valid records; zero denotes an empty window, not measured zero latency.</summary>
    public async Task<(double p50, double p95, double p99, long breaches, long total)> GetStatsAsync()
    {
        var values = (RedisResult[])(await _redis.GetDatabase().ScriptEvaluateAsync(WindowScript,
            [SortedKey, ReceivedKey], ["read", _retentionMs, _maximumRecords]))!;
        return ((double)values[0], (double)values[1], (double)values[2],
            Interlocked.Read(ref _slaBreaches), Interlocked.Read(ref _totalRecords));
    }
}
