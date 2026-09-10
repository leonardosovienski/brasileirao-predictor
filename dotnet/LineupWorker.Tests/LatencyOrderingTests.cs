using System.Text.Json;
using LineupWorker.Models;
using LineupWorker.Services;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace LineupWorker.Tests;

public sealed partial class WorkerRuntimeTests
{
    [RedisRuntimeFact]
    public async Task OlderAuditArrivalCannotReplaceLatestT3OrRefreshItsTtl()
    {
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, Config());
        var newer = AuditRecord("reordered", 20);
        var older = newer with
        {
            T0_SourcePublished = newer.T0_SourcePublished.AddSeconds(-1),
            T1_Received = newer.T1_Received.AddSeconds(-1),
            T2_VorpComputed = newer.T2_VorpComputed.AddSeconds(-1),
            T3_RedisWritten = newer.T3_RedisWritten.AddSeconds(-1),
        };
        var db = _redis.GetDatabase();
        var key = "latency_audit:reordered:combined";
        await audit.RecordAsync(newer);
        await db.KeyExpireAsync(key, TimeSpan.FromSeconds(10));
        await audit.RecordAsync(older);
        var raw = await db.StringGetAsync(key);
        Assert.Equal(newer, JsonSerializer.Deserialize<LatencyRecord>(raw.ToString()));
        Assert.True(await db.KeyTimeToLiveAsync(key) <= TimeSpan.FromSeconds(10));
        // Historical valid observations remain represented separately.
        Assert.Equal(2, await db.SortedSetLengthAsync("latency_stats:v2:received"));
    }

    [RedisRuntimeFact]
    public async Task DuplicateAuditArrivalCannotEraseTheRecordedMarketRead()
    {
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, Config());
        var record = AuditRecord("duplicate-read", 10);
        await audit.RecordAsync(record);
        var t4 = record.T3_RedisWritten.AddMilliseconds(2);
        await audit.MarkMarketReadAsync(record.MatchId, record.Side, t4);
        await audit.RecordAsync(record);
        var raw = await _redis.GetDatabase().StringGetAsync("latency_audit:duplicate-read:combined");
        Assert.Equal(t4, JsonSerializer.Deserialize<LatencyRecord>(raw.ToString())!.T4_MarketEngineRead);
    }
}
