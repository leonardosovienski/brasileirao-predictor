using System.Diagnostics;
using System.Text.Json;
using LineupWorker.Services;
using Microsoft.Extensions.Logging.Abstractions;
using StackExchange.Redis;
using Xunit;

namespace LineupWorker.Tests;

public sealed partial class WorkerRuntimeTests
{
    [RedisRuntimeFact]
    public async Task CliHealthFailsWhenRedisRespondsButWorkerIsAbsent()
    {
        await _redis.GetDatabase().PingAsync();
        Assert.Equal(1, await HealthExitCode());
        var health = new WorkerHealth(_redis);
        Assert.True(await health.RenewAsync("mse"));
        Assert.Equal(1, await HealthExitCode()); // One live loop cannot stand in for the other.
        Assert.True(await health.RenewAsync("inbox"));
        Assert.Equal(0, await HealthExitCode());
        await _redis.GetDatabase().KeyExpireAsync(WorkerHealth.KeyFor("inbox"), TimeSpan.FromMilliseconds(20));
        await Task.Delay(40);
        Assert.Equal(1, await HealthExitCode());
    }

    private async Task<int> HealthExitCode()
    {
        var start = new ProcessStartInfo("dotnet")
        {
            UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true,
        };
        start.ArgumentList.Add(typeof(MarketStateEngine).Assembly.Location);
        start.ArgumentList.Add("--healthcheck");
        start.Environment["VORP_ARTIFACT_PATH"] = Path.Combine(_root, "unused-vorp.json");
        start.Environment["TITULARIDADE_PATH"] = Path.Combine(_root, "unused-titularidade.json");
        using var process = System.Diagnostics.Process.Start(start)!;
        var stdout = process.StandardOutput.ReadToEndAsync();
        var stderr = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        try { await process.WaitForExitAsync(timeout.Token); }
        catch (OperationCanceledException) { process.Kill(entireProcessTree: true); throw; }
        await Task.WhenAll(stdout, stderr);
        Assert.InRange(process.ExitCode, 0, 1);
        return process.ExitCode;
    }

    [RedisRuntimeFact]
    public async Task HeartbeatRequiresSameSessionAndInstanceAndCleanupCannotEraseNewOwner()
    {
        var instance = Guid.NewGuid().ToString("N");
        var first = new WorkerHealth(_redis, instance);
        var second = new WorkerHealth(_redis, instance);
        Assert.False(await WorkerHealth.CheckAsync(_redis, instance));
        Assert.True(await first.RenewAsync("mse"));
        Assert.True(await second.RenewAsync("inbox"));
        Assert.False(await WorkerHealth.CheckAsync(_redis, instance));
        Assert.False(await second.RenewAsync("mse")); // Cannot overwrite another active session.
        await first.ReleaseAsync("mse");
        Assert.True(await second.RenewAsync("mse"));
        Assert.True(await WorkerHealth.CheckAsync(_redis, instance));
        await first.ReleaseAsync("mse");
        Assert.True(await WorkerHealth.CheckAsync(_redis, instance));
        Assert.False(await WorkerHealth.CheckAsync(_redis, "another-instance"));
        var db = _redis.GetDatabase();
        var key = WorkerHealth.KeyFor("mse", instance);
        var own = await db.StringGetAsync(key);
        await db.StringSetAsync(key, own); // A stale permanent key is not a heartbeat.
        Assert.False(await WorkerHealth.CheckAsync(_redis, instance));
        foreach (var malformed in new[] { "null", "{", "{}", JsonSerializer.Serialize(new
        {
            protocol_version = "brasileirao.redis/2", instance_id = "wrong-instance",
            session_id = second.SessionId, role = "mse"
        }) })
        {
            await db.StringSetAsync(key, malformed, TimeSpan.FromSeconds(5));
            Assert.False(await WorkerHealth.CheckAsync(_redis, instance));
        }
        await Assert.ThrowsAsync<ArgumentException>(() => first.RenewAsync("unknown"));
    }

    [RedisRuntimeFact]
    public async Task MseHeartbeatTracksSuccessfulRecoveryLoopAndIsRemovedAtStop()
    {
        var cfg = Config();
        var health = new WorkerHealth(_redis, Guid.NewGuid().ToString("N"));
        var engine = new MarketStateEngine(_redis,
            new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, cfg),
            new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, cfg),
            NullLogger<MarketStateEngine>.Instance, cfg, health);
        await engine.StartAsync(default);
        try
        {
            await WaitUntil(async () => await _redis.GetDatabase().KeyExistsAsync(WorkerHealth.KeyFor("mse", health.InstanceId)));
            Assert.False(await WorkerHealth.CheckAsync(_redis, health.InstanceId));
            await health.RenewAsync("inbox");
            Assert.True(await WorkerHealth.CheckAsync(_redis, health.InstanceId));
        }
        finally { await engine.StopAsync(default); }
        Assert.False(await _redis.GetDatabase().KeyExistsAsync(WorkerHealth.KeyFor("mse", health.InstanceId)));
    }

    [RedisRuntimeFact]
    public async Task BothHeartbeatsExpireNaturallyWhenProcessingStops()
    {
        var health = new WorkerHealth(_redis, Guid.NewGuid().ToString("N"));
        await health.RenewAsync("mse");
        await health.RenewAsync("inbox");
        Assert.True(await WorkerHealth.CheckAsync(_redis, health.InstanceId));
        await Task.Delay(WorkerHealth.LifetimeMs + 100);
        await _redis.GetDatabase().PingAsync();
        Assert.False(await WorkerHealth.CheckAsync(_redis, health.InstanceId));
    }
}
