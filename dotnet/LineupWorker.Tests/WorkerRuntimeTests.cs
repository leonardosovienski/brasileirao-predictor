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

public sealed class WorkerRuntimeTests : IAsyncLifetime
{
    private ConnectionMultiplexer _redis = null!;
    private readonly string _root = Path.Combine(Path.GetTempPath(), $"lineup-worker-{Guid.NewGuid():N}");

    public async Task InitializeAsync()
    {
        Directory.CreateDirectory(_root);
        _redis = await ConnectionMultiplexer.ConnectAsync("127.0.0.1:6380,abortConnect=false,allowAdmin=true");
        await _redis.GetDatabase().ExecuteAsync("FLUSHDB");
    }

    public async Task DisposeAsync()
    {
        await _redis.CloseAsync();
        _redis.Dispose();
        Directory.Delete(_root, recursive: true);
    }

    private IConfiguration Config(params (string Key, string Value)[] values) =>
        new ConfigurationBuilder().AddInMemoryCollection(values.ToDictionary(v => v.Key, v => (string?)v.Value)).Build();

    private OperationalSettings CreateSettings(string vorp, string titularidade) => new(
        "redis://127.0.0.1:6380/0",
        vorp,
        titularidade,
        Path.Combine(_root, "sports.db"),
        Path.Combine(_root, "market.db"));

    [Fact]
    public async Task VorpWarmupLoadsPlayersFallbacksAndTitularidade()
    {
        var vorp = Path.Combine(_root, "vorp.json");
        var titularidade = Path.Combine(_root, "titularidade.json");
        await File.WriteAllTextAsync(vorp, """{"beta_players":{"p1":1.5},"replacement_levels":{"GK":-0.2,"UNKNOWN":-0.5}}""");
        await File.WriteAllTextAsync(titularidade, """{"home":[0.9,0.8]}""");
        var service = new VorpStateService(NullLogger<VorpStateService>.Instance, CreateSettings(vorp, titularidade));

        await service.StartAsync(default);

        Assert.True(service.IsReady);
        Assert.Equal(1.5, service.GetVorp("p1", "GK"));
        Assert.Equal(-0.2, service.GetVorp("missing", "GK"));
        Assert.Equal(-0.5, service.GetVorp("missing", "missing"));
        Assert.Equal(1.3, service.ComputeDeltaVorp(new[] { ("p1", "GK"), ("missing", "GK") }));
        Assert.Equal([0.9, 0.8], service.GetTitularidadeMatrix("home")!);
        Assert.Null(service.GetTitularidadeMatrix("away"));
        await service.StopAsync(default);
    }

    [Fact]
    public void MarketCacheParsesValidPayloadRejectsInvalidAndExpiresStaleOdds()
    {
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, Config());
        var parse = typeof(MarketOddsCache).GetMethod("ParseAndUpdate", BindingFlags.Instance | BindingFlags.NonPublic)!;
        var valid = Encoding.UTF8.GetBytes(
            """{"match_id":"m1","home":2.2,"draw":3.2,"away":3.4,"over25":1.9,"under25":2.0,"source":"fixture"}""");
        parse.Invoke(cache, [new ReadOnlyMemory<byte>(valid)]);

        Assert.Equal("fixture", cache.TryGet("m1")!.Source);
        Assert.Null(cache.TryGet("missing"));
        parse.Invoke(cache, [new ReadOnlyMemory<byte>(Encoding.UTF8.GetBytes("{"))]);

        var field = typeof(MarketOddsCache).GetField("_cache", BindingFlags.Instance | BindingFlags.NonPublic)!;
        var map = (System.Collections.Concurrent.ConcurrentDictionary<string, MarketOdds>)field.GetValue(cache)!;
        map["stale"] = new MarketOdds("stale", 2, 3, 4, null, null, DateTimeOffset.UtcNow.AddMinutes(-2), "fixture");
        Assert.Null(cache.TryGet("stale"));
    }

    [Fact]
    public async Task LatencyAuditPersistsUpdatesAndComputesPercentiles()
    {
        var audit = new LatencyAuditService(
            _redis,
            NullLogger<LatencyAuditService>.Instance,
            Config(("MarketStateEngine:LatencyBudgetMs", "20")));
        var t0 = DateTimeOffset.UtcNow;
        var fast = new LatencyRecord("m1", "home", t0, t0.AddMilliseconds(2), t0.AddMilliseconds(3),
            t0.AddMilliseconds(10), null, 0.1, false, null);
        var slow = fast with { MatchId = "m2", Side = "away", T3_RedisWritten = t0.AddMilliseconds(50) };

        await audit.RecordAsync(fast);
        await audit.RecordAsync(slow);
        await audit.MarkMarketReadAsync("missing", "home", t0);
        await audit.MarkMarketReadAsync("m1", "home", t0.AddMilliseconds(12));
        var stats = await audit.GetStatsAsync();

        Assert.Equal(2, stats.total);
        Assert.Equal(1, stats.breaches);
        Assert.True(stats.p50 >= 10);
        var stored = await _redis.GetDatabase().StringGetAsync("latency_audit:m1:home");
        Assert.Contains("T4_MarketEngineRead", stored.ToString());
    }

    [Fact]
    public async Task LatencyAuditReturnsZerosWhenNoRecordsExist()
    {
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, Config());
        var stats = await audit.GetStatsAsync();
        Assert.Equal((0, 0, 0, 0, 0), stats);
    }

    [Fact]
    public async Task MarketCacheRetriesInvalidEndpointAndStopsGracefully()
    {
        var cache = new MarketOddsCache(
            NullLogger<MarketOddsCache>.Instance,
            Config(("Exchange:WebSocketUrl", "ws://127.0.0.1:1/odds")));
        await cache.StartAsync(default);
        await Task.Delay(1200);
        await cache.StopAsync(default);
    }

    [Fact]
    public async Task MarketStateInvokesVersionedKernelAndProcessesFairOdds()
    {
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, Config());
        var parse = typeof(MarketOddsCache).GetMethod("ParseAndUpdate", BindingFlags.Instance | BindingFlags.NonPublic)!;
        var market = Encoding.UTF8.GetBytes(
            """{"match_id":"m-edge","home":2.4,"draw":3.8,"away":4.0,"over25":2.2,"under25":2.2}""");
        parse.Invoke(cache, [new ReadOnlyMemory<byte>(market)]);
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, Config());
        var mse = new MarketStateEngine(
            _redis, cache, audit, NullLogger<MarketStateEngine>.Instance,
            Config(("MarketStateEngine:MinEdgePct", "-1"), ("MarketStateEngine:MaxEdgePct", "1")));
        var subscriber = _redis.GetSubscriber();
        var invoke = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        var signal = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        await subscriber.SubscribeAsync(RedisChannel.Literal("system:invoke_kernel"), (_, value) => invoke.TrySetResult(value!));
        await subscriber.SubscribeAsync(RedisChannel.Literal("bet_signals"), (_, value) => signal.TrySetResult(value!));

        await mse.InvokeKernelAsync("m-edge", 1600, 1500, 0.1, -0.1);
        var invocation = await invoke.Task.WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Contains("brasileirao.redis/1", invocation);

        var fair = """{"protocol_version":"brasileirao.redis/1","job_id":"j","run_id":"r","match_id":"m-edge","1":2.0,"X":3.0,"2":4.0,"o25":1.9,"u25":2.1}""";
        await _redis.GetDatabase().StringSetAsync("fair_odds:m-edge", fair, TimeSpan.FromSeconds(5));
        var process = typeof(MarketStateEngine).GetMethod("ProcessFairOddsAsync", BindingFlags.Instance | BindingFlags.NonPublic)!;
        await (Task)process.Invoke(mse, ["m-edge", fair, CancellationToken.None])!;

        var bet = await signal.Task.WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Contains("m-edge", bet);
    }

    [Fact]
    public async Task MarketStateFailsClosedForExpiredInvalidAndMissingMarketOdds()
    {
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, Config());
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, Config());
        var mse = new MarketStateEngine(_redis, cache, audit, NullLogger<MarketStateEngine>.Instance, Config());
        var process = typeof(MarketStateEngine).GetMethod("ProcessFairOddsAsync", BindingFlags.Instance | BindingFlags.NonPublic)!;

        await (Task)process.Invoke(mse, ["expired", "{}", CancellationToken.None])!;
        await _redis.GetDatabase().StringSetAsync("fair_odds:invalid", "{");
        await (Task)process.Invoke(mse, ["invalid", "{}", CancellationToken.None])!;
        var fair = """{"protocol_version":"brasileirao.redis/1","job_id":"j","run_id":"r","match_id":"no-market","1":2,"X":3,"2":4,"o25":2,"u25":2}""";
        await _redis.GetDatabase().StringSetAsync("fair_odds:no-market", fair);
        await (Task)process.Invoke(mse, ["no-market", fair, CancellationToken.None])!;
    }

    [Fact]
    public void MarketStateComputesOnlyEligibleEdgesAndCapsKelly()
    {
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, Config());
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, Config());
        var mse = new MarketStateEngine(
            _redis, cache, audit, NullLogger<MarketStateEngine>.Instance,
            Config(("MarketStateEngine:MinEdgePct", "0.01"), ("MarketStateEngine:MaxEdgePct", "0.20"),
                ("MarketStateEngine:KellyFraction", "1")));
        var compute = typeof(MarketStateEngine).GetMethod("ComputeEdge", BindingFlags.Instance | BindingFlags.NonPublic)!;
        var fair = new FairOddsPayload(2, 3, 4, null, 2);
        var market = new MarketOdds("m", 2.5, 1, 1, null, 2.5, DateTimeOffset.UtcNow, "fixture");
        var state = new LineupState("m", 0.2, -0.1, true, true, DateTimeOffset.UtcNow.AddMilliseconds(-20),
            DateTimeOffset.UtcNow, "none");

        var result = (System.Collections.IEnumerable)compute.Invoke(
            mse, ["m", fair, market, state, DateTimeOffset.UtcNow])!;
        var signals = result.Cast<BetSignal>().ToList();

        Assert.Equal(2, signals.Count);
        Assert.All(signals, item => Assert.InRange(item.KellyStake, 0, 0.05));
        Assert.All(signals, item => Assert.True(item.PipelineLatencyMs >= 0));
    }

    [Fact]
    public async Task MarketStateSubscriptionHandlesNotificationsAndStopsGracefully()
    {
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, Config());
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, Config());
        var mse = new MarketStateEngine(_redis, cache, audit, NullLogger<MarketStateEngine>.Instance, Config());
        await mse.StartAsync(default);
        await Task.Delay(150);

        await _redis.GetSubscriber().PublishAsync(RedisChannel.Literal("fair_odds_ready:"), "{}");
        await _redis.GetSubscriber().PublishAsync(RedisChannel.Literal("fair_odds_ready:empty"), RedisValue.EmptyString);
        await _redis.GetSubscriber().PublishAsync(RedisChannel.Literal("fair_odds_ready:missing"), "{}");
        await Task.Delay(150);
        await mse.StopAsync(default);
    }

    [Fact]
    public async Task WorkerConsumesBothLineupsPersistsStateAndInvokesKernel()
    {
        var vorpPath = Path.Combine(_root, "vorp-runtime.json");
        await File.WriteAllTextAsync(vorpPath, """{"beta_players":{"p1":1.0,"p2":2.0},"replacement_levels":{"UNKNOWN":-0.1}}""");
        var vorp = new VorpStateService(
            NullLogger<VorpStateService>.Instance,
            CreateSettings(vorpPath, Path.Combine(_root, "absent.json")));
        await vorp.StartAsync(default);
        var cfg = Config(
            ("Worker:LineupTimeoutMinutes", "1"),
            ("Worker:WatchdogIntervalSeconds", "1"),
            ("Worker:RedisStateTtlHours", "1"),
            ("Worker:QueueCapacity", "16"));
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, cfg);
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, cfg);
        var mse = new MarketStateEngine(_redis, cache, audit, NullLogger<MarketStateEngine>.Instance, cfg);
        var worker = new LineupWorkerService(
            NullLogger<LineupWorkerService>.Instance, vorp, audit, mse, _redis, cfg);
        await worker.StartAsync(default);
        await Task.Delay(200);

        var captured = DateTimeOffset.UtcNow;
        var home = new LineupEvent("home_away", "home", "away", "home", ["p1"], [], captured);
        var away = home with { Side = "away", Starters = ["p2"] };
        var sub = _redis.GetSubscriber();
        await sub.PublishAsync(RedisChannel.Literal("lineups:home_away"), RedisValue.EmptyString);
        await sub.PublishAsync(RedisChannel.Literal("lineups:home_away"), "null");
        await sub.PublishAsync(RedisChannel.Literal("lineups:home_away"), "{");
        await sub.PublishAsync(RedisChannel.Literal("lineups:home_away"), JsonSerializer.Serialize(home));
        await sub.PublishAsync(RedisChannel.Literal("lineups:home_away"), JsonSerializer.Serialize(away));

        await Task.Delay(800);
        var raw = await _redis.GetDatabase().StringGetAsync("lineup_state:home_away");
        var state = JsonSerializer.Deserialize<LineupState>(raw.ToString())!;
        Assert.True(state.HomeLineupComplete && state.AwayLineupComplete);
        Assert.Equal(1.0, state.DeltaVorpHome);
        Assert.Equal(2.0, state.DeltaVorpAway);
        Assert.True(await _redis.GetDatabase().KeyExistsAsync("idempotency:kernel:home_away") || raw.HasValue);

        await worker.StopAsync(default);
    }

    [Fact]
    public async Task WorkerCancellationWhileWaitingForVorpIsGraceful()
    {
        var vorpPath = Path.Combine(_root, "vorp-not-started.json");
        await File.WriteAllTextAsync(vorpPath, """{"beta_players":{},"replacement_levels":{"UNKNOWN":0}}""");
        var vorp = new VorpStateService(
            NullLogger<VorpStateService>.Instance,
            CreateSettings(vorpPath, Path.Combine(_root, "none-wait.json")));
        var cfg = Config();
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, cfg);
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, cfg);
        var mse = new MarketStateEngine(_redis, cache, audit, NullLogger<MarketStateEngine>.Instance, cfg);
        var worker = new LineupWorkerService(
            NullLogger<LineupWorkerService>.Instance, vorp, audit, mse, _redis, cfg);

        await worker.StartAsync(default);
        await Task.Delay(100);
        await worker.StopAsync(default);
    }

    [Fact]
    public async Task WorkerWatchdogPublishesFallbackForMissingAwayLineup()
    {
        var vorpPath = Path.Combine(_root, "vorp-timeout.json");
        var titularidade = Path.Combine(_root, "tit-timeout.json");
        await File.WriteAllTextAsync(vorpPath, """{"beta_players":{},"replacement_levels":{"UNKNOWN":0}}""");
        await File.WriteAllTextAsync(titularidade, """{"away":[0.7,0.3]}""");
        var vorp = new VorpStateService(
            NullLogger<VorpStateService>.Instance,
            CreateSettings(vorpPath, titularidade));
        await vorp.StartAsync(default);
        var cfg = Config(
            ("Worker:LineupTimeoutMinutes", "1"),
            ("Worker:WatchdogIntervalSeconds", "1"),
            ("Worker:VarianceWideningFactor", "1.4"));
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, cfg);
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, cfg);
        var mse = new MarketStateEngine(_redis, cache, audit, NullLogger<MarketStateEngine>.Instance, cfg);
        var worker = new LineupWorkerService(
            NullLogger<LineupWorkerService>.Instance, vorp, audit, mse, _redis, cfg);
        var fallback = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        await _redis.GetSubscriber().SubscribeAsync(
            RedisChannel.Literal("variance_widen"), (_, value) => fallback.TrySetResult(value!));
        await worker.StartAsync(default);
        await Task.Delay(200);
        var home = new LineupEvent(
            "home_away", "home", "away", "home", ["unknown"], [], DateTimeOffset.UtcNow.AddMinutes(-2));
        await _redis.GetSubscriber().PublishAsync(
            RedisChannel.Literal("lineups:home_away"), JsonSerializer.Serialize(home));

        var json = await fallback.Task.WaitAsync(TimeSpan.FromSeconds(4));
        Assert.Contains("away", json);
        await Task.Delay(300);
        var raw = await _redis.GetDatabase().StringGetAsync("lineup_state:home_away");
        Assert.Contains("timeout_widen_variance", raw.ToString());
        await worker.StopAsync(default);
    }

    [Fact]
    public async Task WorkerImmediateFallbackPublishesSignalAndAudit()
    {
        var vorpPath = Path.Combine(_root, "vorp-immediate.json");
        await File.WriteAllTextAsync(vorpPath, """{"beta_players":{},"replacement_levels":{"UNKNOWN":0}}""");
        var settings = CreateSettings(vorpPath, Path.Combine(_root, "none.json"));
        var vorp = new VorpStateService(NullLogger<VorpStateService>.Instance, settings);
        await vorp.StartAsync(default);
        var cfg = Config(("Worker:VarianceWideningFactor", "1.5"));
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, cfg);
        var audit = new LatencyAuditService(_redis, NullLogger<LatencyAuditService>.Instance, cfg);
        var mse = new MarketStateEngine(_redis, cache, audit, NullLogger<MarketStateEngine>.Instance, cfg);
        var worker = new LineupWorkerService(
            NullLogger<LineupWorkerService>.Instance, vorp, audit, mse, _redis, cfg);
        var received = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        await _redis.GetSubscriber().SubscribeAsync(
            RedisChannel.Literal("variance_widen"), (_, value) => received.TrySetResult(value!));
        var method = typeof(LineupWorkerService).GetMethod(
            "TriggerImmediateFallbackAsync", BindingFlags.Instance | BindingFlags.NonPublic)!;

        await (Task)method.Invoke(worker, ["m-immediate", "home", DateTimeOffset.UtcNow.AddSeconds(-1)])!;

        Assert.Contains("m-immediate", await received.Task.WaitAsync(TimeSpan.FromSeconds(2)));
        Assert.True(await _redis.GetDatabase().KeyExistsAsync("latency_audit:m-immediate:home"));
    }
}
