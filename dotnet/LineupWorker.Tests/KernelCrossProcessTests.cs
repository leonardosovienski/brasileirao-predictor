using System.Collections.Concurrent;
using System.Diagnostics;
using System.Reflection;
using System.Text;
using System.Text.Json;
using LineupWorker.Models;
using LineupWorker.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using StackExchange.Redis;
using Xunit;

namespace LineupWorker.Tests;

public sealed class RedisCrossProcessFactAttribute : FactAttribute
{
    public RedisCrossProcessFactAttribute()
    {
        if (string.IsNullOrEmpty(Environment.GetEnvironmentVariable("LINEUP_E2E_PYTHON")))
            Skip = "Requires an explicitly configured disposable Redis and synthetic Python process.";
    }
}

[Collection("IsolatedRedisRuntime")]
public sealed class KernelCrossProcessTests
{
    [RedisCrossProcessFact]
    public async Task RegisteredDotnetRequestSurvivesLostWakeupAndProducesOneCurrentSignalBatch()
    {
        var url = Environment.GetEnvironmentVariable("LINEUP_E2E_REDIS_URL");
        Assert.Equal("redis://127.0.0.1:26380/13", url);
        var expectedRun = Environment.GetEnvironmentVariable("LINEUP_E2E_REDIS_RUN_ID");
        Assert.False(string.IsNullOrWhiteSpace(expectedRun));
        var options = ConfigurationOptions.Parse("127.0.0.1:26380,abortConnect=true,allowAdmin=true,defaultDatabase=13");
        using var redis = await ConnectionMultiplexer.ConnectAsync(options);
        var db = redis.GetDatabase();
        var info = (string?)await db.ExecuteAsync("INFO", "server");
        Assert.Contains("run_id:" + expectedRun, info);

        var match = "cross-process-" + Guid.NewGuid().ToString("N");
        var signals = new ConcurrentQueue<string>();
        var subscriber = redis.GetSubscriber();
        var signalQueue = await subscriber.SubscribeAsync(RedisChannel.Literal("bet_signals"));
        signalQueue.OnMessage(message =>
        {
            using var document = JsonDocument.Parse(message.Message.ToString());
            if (document.RootElement.GetProperty("MatchId").GetString() == match)
                signals.Enqueue(message.Message.ToString());
        });
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        { ["Exchange:AllowSyntheticPayloads"] = "true", ["Worker:AllowSyntheticInputs"] = "true" }).Build();
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, configuration);
        var parse = typeof(MarketOddsCache).GetMethod("ParseAndUpdate", BindingFlags.Instance | BindingFlags.NonPublic)!;
        var audit = new LatencyAuditService(redis, NullLogger<LatencyAuditService>.Instance, configuration);
        var engine = new MarketStateEngine(redis, cache, audit, NullLogger<MarketStateEngine>.Instance, configuration);
        var now = DateTimeOffset.UtcNow;
        var lineup = new LineupState(match, 0.25, -0.1, true, true, now, now, "none");
        Process? python = null;
        Task<string>? stdout = null;
        Task<string>? stderr = null;
        string? run = null;
        string? identity = null;
        LineupWorker.LineupWorkerService? worker = null;
        VorpStateService? vorp = null;
        var fixtureDirectory = Path.Combine(Path.GetTempPath(), "kernel-cross-process-" + Guid.NewGuid().ToString("N"));
        await engine.StartAsync(CancellationToken.None);
        try
        {
            // Finish cold imports/JIT before measuring protocol recovery. The
            // bootstrap waits for our file barrier before any subscription, so
            // registration below still loses its Pub/Sub wakeup deliberately.
            Directory.CreateDirectory(fixtureDirectory);
            var readyFile = Path.Combine(fixtureDirectory, "python-ready");
            var startFile = Path.Combine(fixtureDirectory, "python-start");
            var start = new ProcessStartInfo(Environment.GetEnvironmentVariable("LINEUP_E2E_PYTHON")!)
            {
                UseShellExecute = false, CreateNoWindow = true,
                RedirectStandardOutput = true, RedirectStandardError = true,
                WorkingDirectory = Environment.CurrentDirectory,
            };
            start.Environment["LINEUP_E2E_READY_FILE"] = readyFile;
            start.Environment["LINEUP_E2E_START_FILE"] = startFile;
            start.ArgumentList.Add(Environment.GetEnvironmentVariable("LINEUP_E2E_KERNEL_SCRIPT")!);
            python = Process.Start(start)!;
            stdout = python.StandardOutput.ReadToEndAsync();
            stderr = python.StandardError.ReadToEndAsync();
            var bootClock = Stopwatch.StartNew();
            while (!File.Exists(readyFile) && bootClock.Elapsed < TimeSpan.FromSeconds(120))
            {
                if (python.HasExited)
                    Assert.Fail("Synthetic kernel exited during initialization: " + await stderr);
                await Task.Delay(50);
            }
            if (!File.Exists(readyFile))
            {
                var lab = Environment.GetEnvironmentVariable("BRASILEIRAO_LAB_OUTPUT")!;
                var phaseFile = Path.Combine(lab, $"kernel-startup-{python.Id}.log");
                var phases = File.Exists(phaseFile) ? await File.ReadAllTextAsync(phaseFile) : "no startup phase was recorded";
                Assert.Fail($"Synthetic initialization exceeded 120s ({bootClock.Elapsed.TotalSeconds:F1}s monotonic). {phases}");
            }

            // A synthetic quote is observed at decision time, after cold JIT.
            // Creating it before startup made this protocol test fail once the
            // 30s market freshness window elapsed during imports/compilation.
            parse.Invoke(cache, [new ReadOnlyMemory<byte>(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(
                new { match_id = match, home = 2.4, draw = 3.0, away = 4.0, source = "synthetic-cross-process" })))]);
            // No kernel subscriber yet: recovery must use the durable request.
            var registration = await engine.InvokeKernelAsync(match, 1600, 1500, lineup, null,
                "synthetic-event", TimeSpan.FromMinutes(2));
            Assert.Equal("registered", registration.Status);
            var payload = JsonSerializer.Deserialize<KernelInvokePayload>(registration.PayloadJson!)!;
            run = payload.run_id;
            identity = payload.idempotency_key;
            Assert.Equal("1", payload.state_version);
            Assert.Equal("pending", (string?)await db.HashGetAsync(KernelRedisProtocolV2.RequestPrefix + run, "status"));

            await File.WriteAllTextAsync(startFile, "start-synthetic-session");
            var until = DateTimeOffset.UtcNow.AddSeconds(40);
            while (signals.IsEmpty && DateTimeOffset.UtcNow < until)
            {
                if (python.HasExited)
                    Assert.Fail("Synthetic kernel exited before completion: " + await stderr);
                await Task.Delay(50);
            }
            Assert.Single(signals);
            Assert.Equal("completed", (string?)await db.HashGetAsync(KernelRedisProtocolV2.RequestPrefix + run, "status"));
            var fairJson = (string?)await db.StringGetAsync("fair_odds:" + match);
            Assert.NotNull(fairJson);
            using var fair = JsonDocument.Parse(fairJson!);
            Assert.Equal(payload.state_version, fair.RootElement.GetProperty("state_version").GetString());
            Assert.Equal(run, fair.RootElement.GetProperty("run_id").GetString());
            using var signal = JsonDocument.Parse(signals.Single());
            Assert.Equal(0.25, signal.RootElement.GetProperty("DeltaVorpHome").GetDouble());
            Assert.Equal(-0.1, signal.RootElement.GetProperty("DeltaVorpAway").GetDouble());

            // A duplicate producer call returns the same registration. Replayed
            // wakeups and fair notifications cannot publish a second batch.
            var duplicate = await engine.InvokeKernelAsync(match, 1600, 1500, lineup, null,
                "synthetic-event", TimeSpan.FromMinutes(2));
            Assert.Equal("duplicate", duplicate.Status);
            Assert.Equal(registration.PayloadJson, duplicate.PayloadJson);
            await subscriber.PublishAsync(RedisChannel.Literal(KernelRedisProtocolV2.InvokeChannel), registration.PayloadJson);
            for (var i = 0; i < 4; i++)
                await subscriber.PublishAsync(RedisChannel.Literal("fair_odds_ready:" + match), fairJson);
            await Task.Delay(300);
            Assert.Single(signals);

            // Exercise the migrated Compose smoke against the actual Worker
            // queue and producer, with fabricated VORP resources only.
            Directory.CreateDirectory(fixtureDirectory);
            var vorpPath = Path.Combine(fixtureDirectory, "vorp.json");
            var lineupPath = Path.Combine(fixtureDirectory, "titularidade.json");
            await File.WriteAllTextAsync(vorpPath, """{"beta_players":{},"replacement_levels":{"UNKNOWN":0}}""");
            await File.WriteAllTextAsync(lineupPath, "{}");
            var settings = new OperationalSettings(url!, vorpPath, lineupPath,
                Path.Combine(fixtureDirectory, "unused-sports.db"), Path.Combine(fixtureDirectory, "unused-market.db"));
            vorp = new VorpStateService(NullLogger<VorpStateService>.Instance, settings);
            await vorp.StartAsync(CancellationToken.None);
            worker = new LineupWorker.LineupWorkerService(NullLogger<LineupWorker.LineupWorkerService>.Instance,
                vorp, audit, engine, redis, configuration);
            await worker.StartAsync(CancellationToken.None);
            var smokeStart = new ProcessStartInfo(Environment.GetEnvironmentVariable("LINEUP_E2E_PYTHON")!)
            {
                UseShellExecute = false, CreateNoWindow = true,
                RedirectStandardOutput = true, RedirectStandardError = true,
                WorkingDirectory = Environment.CurrentDirectory,
            };
            foreach (var argument in new[] { "-m", "brasileirao_scripts.hotpath_smoke", "--synthetic-lineup", "--redis", url! })
                smokeStart.ArgumentList.Add(argument);
            using var smoke = Process.Start(smokeStart)!;
            var smokeOutput = smoke.StandardOutput.ReadToEndAsync();
            var smokeError = smoke.StandardError.ReadToEndAsync();
            using var smokeTimeout = new CancellationTokenSource(TimeSpan.FromSeconds(20));
            try { await smoke.WaitForExitAsync(smokeTimeout.Token); }
            catch (OperationCanceledException)
            {
                if (!smoke.HasExited) smoke.Kill(entireProcessTree: true);
                throw;
            }
            Assert.True(smoke.ExitCode == 0, await smokeOutput + await smokeError);
            Assert.Contains("\"verified\": 1", await smokeOutput);
        }
        finally
        {
            if (worker is not null) { await worker.StopAsync(CancellationToken.None); worker.Dispose(); }
            if (vorp is not null) await vorp.StopAsync(CancellationToken.None);
            if (python is { HasExited: false }) python.Kill(entireProcessTree: true);
            if (python is not null)
            {
                await python.WaitForExitAsync();
                if (stdout is not null) await stdout;
                if (stderr is not null) await stderr;
                python.Dispose();
            }
            await engine.StopAsync(CancellationToken.None);
            engine.Dispose();
            await subscriber.UnsubscribeAllAsync();
            var owned = new List<RedisKey>
            {
                "lineup_state:" + match, "fair_odds:" + match,
                KernelRedisProtocolV2.CurrentPrefix + match, KernelRedisProtocolV2.SequencePrefix + match,
            };
            if (run is not null)
            {
                owned.Add(KernelRedisProtocolV2.RequestPrefix + run);
                owned.Add(KernelRedisProtocolV2.LeasePrefix + run);
                owned.Add(KernelRedisProtocolV2.SignalsPrefix + run);
                await db.SortedSetRemoveAsync(KernelRedisProtocolV2.PendingKey, run);
            }
            if (identity is not null) owned.Add(KernelRedisProtocolV2.IdentityPrefix + identity);
            await db.KeyDeleteAsync(owned.ToArray());
            if (Directory.Exists(fixtureDirectory)) Directory.Delete(fixtureDirectory, recursive: true);
        }
    }
}
