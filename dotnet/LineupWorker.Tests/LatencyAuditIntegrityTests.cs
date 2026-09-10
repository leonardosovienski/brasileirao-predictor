using System.Text.Json;
using System.Reflection;
using LineupWorker.Models;
using LineupWorker.Services;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Configuration;
using Xunit;

namespace LineupWorker.Tests;

public sealed partial class WorkerRuntimeTests
{
    private static LatencyRecord AuditRecord(string match, double milliseconds)
    {
        var now = DateTimeOffset.UtcNow;
        return new(match, "combined", now.AddMilliseconds(-milliseconds), now, now, now, null, 0, false, null);
    }

    [RedisRuntimeFact]
    public async Task AuditRetainsNewestRecordsInsteadOfAllHistory()
    {
        var cfg = Config();
        cfg["LatencyAudit:MaximumRecords"] = "2";
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, cfg);
        await audit.RecordAsync(AuditRecord("oldest", 1));
        await Task.Delay(5);
        await audit.RecordAsync(AuditRecord("slow-new", 20));
        await Task.Delay(5);
        await audit.RecordAsync(AuditRecord("fast-new", 2));
        var stats = await audit.GetStatsAsync();
        Assert.Equal(20, stats.p50, 3); // retained [2,20], not [1,2,20]
    }

    [RedisRuntimeFact]
    public async Task AuditExpiresItsWindowEvenWithoutNewRecords()
    {
        var cfg = Config();
        cfg["LatencyAudit:RetentionSeconds"] = "1";
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, cfg);
        await audit.RecordAsync(AuditRecord("expires", 10));
        await Task.Delay(1200);
        var stats = await audit.GetStatsAsync();
        Assert.Equal(0, stats.p50);
        Assert.Equal(0, stats.p99);
    }

    [RedisRuntimeFact]
    public async Task MarketReadBeforeTheWriteCannotEnterAudit()
    {
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, Config());
        var record = AuditRecord("clock-test", 10);
        await audit.RecordAsync(record);
        await audit.MarkMarketReadAsync(record.MatchId, record.Side, record.T3_RedisWritten.AddSeconds(-1));
        var raw = await _redis.GetDatabase().StringGetAsync("latency_audit:clock-test:combined");
        Assert.Null(JsonSerializer.Deserialize<LatencyRecord>(raw.ToString())!.T4_MarketEngineRead);
    }

    [RedisRuntimeFact]
    public async Task StaleMarketReadCannotReplaceNewerAuditRecord()
    {
        var db = _redis.GetDatabase();
        var key = "latency_audit:cas:combined";
        var before = JsonSerializer.Serialize(AuditRecord("cas", 5));
        var newer = JsonSerializer.Serialize(AuditRecord("cas", 10));
        await db.StringSetAsync(key, newer, TimeSpan.FromMinutes(1));
        var script = (string)typeof(LatencyAuditService).GetField("MarkReadScript",
            BindingFlags.NonPublic | BindingFlags.Static)!.GetRawConstantValue()!;
        Assert.Equal(0L, (long)await db.ScriptEvaluateAsync(script, [key], [before, "stale-write"]));
        Assert.Equal(newer, (await db.StringGetAsync(key)).ToString());
        Assert.True(await db.KeyTimeToLiveAsync(key) > TimeSpan.Zero);
    }

    [RedisRuntimeFact]
    public async Task InvalidClockRevisionCannotRemainInPercentiles()
    {
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, Config());
        var record = AuditRecord("invalid", 10);
        await audit.RecordAsync(record);
        await audit.RecordAsync(record with { T0_SourcePublished = record.T3_RedisWritten.AddSeconds(1) });
        Assert.Equal(0, (await audit.GetStatsAsync()).p50);
    }
}

// Configuration tests never initialize a Redis fixture or connect anywhere.
public sealed class LatencyAuditConfigurationTests
{
    [Theory]
    [InlineData("0")]
    [InlineData("-1")]
    [InlineData("NaN")]
    public void AuditRejectsInvalidBudget(string value)
    {
        var cfg = new ConfigurationBuilder().AddInMemoryCollection(
            new Dictionary<string, string?> { ["MarketStateEngine:LatencyBudgetMs"] = value }).Build();
        Assert.Throws<ArgumentOutOfRangeException>(() => new LatencyAuditService(
            null!, NullLogger<LatencyAuditService>.Instance, cfg));
    }
}
