using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using LineupWorker.Models;
using LineupWorker.Services;
using Microsoft.Extensions.Logging.Abstractions;
using StackExchange.Redis;
using Xunit;

namespace LineupWorker.Tests;

public sealed partial class WorkerRuntimeTests
{
    private MarketStateEngine Engine(IConnectionMultiplexer? connection = null, string? marketMatch = null)
    {
        var cfg = Config();
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, cfg);
        if (marketMatch is not null)
            typeof(MarketOddsCache).GetMethod("ParseAndUpdate", BindingFlags.Instance | BindingFlags.NonPublic)!
                .Invoke(cache, [new ReadOnlyMemory<byte>(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(
                    new { match_id = marketMatch, home = 2.4, draw = 3.0, away = 4.0 })))]);
        var redis = connection ?? _redis;
        return new MarketStateEngine(redis, cache,
            new LatencyAuditService(redis, NullLogger<LatencyAuditService>.Instance, cfg),
            NullLogger<MarketStateEngine>.Instance, cfg);
    }

    private static LineupState State(string match, double home = 0, double away = 0)
        => new(match, home, away, true, false, DateTimeOffset.UtcNow, DateTimeOffset.UtcNow, "none");

    private static async Task<KernelInvokePayload> Register(MarketStateEngine engine, LineupState state,
        string? expected = null, string source = "source")
    {
        var result = await engine.InvokeKernelAsync(state.MatchId, 1500, 1500, state, expected, source, TimeSpan.FromHours(1));
        Assert.Equal("registered", result.Status);
        return JsonSerializer.Deserialize<KernelInvokePayload>(result.PayloadJson!)!;
    }

    private async Task<string> CompleteFixture(KernelInvokePayload request, bool expiringFair = true)
    {
        var fair = JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["protocol_version"] = request.protocol_version, ["job_id"] = request.job_id,
            ["run_id"] = request.run_id, ["match_id"] = request.match_id,
            ["state_version"] = request.state_version, ["idempotency_key"] = request.idempotency_key,
            ["1"] = 2.0, ["X"] = 3.0, ["2"] = 4.0
        });
        var db = _redis.GetDatabase();
        await db.HashSetAsync(KernelRedisProtocolV2.RequestPrefix + request.run_id,
            [new HashEntry("status", "completed"), new HashEntry("result", fair)]);
        if (expiringFair) await db.StringSetAsync("fair_odds:" + request.match_id, fair, TimeSpan.FromSeconds(5));
        else await db.StringSetAsync("fair_odds:" + request.match_id, fair);
        return fair;
    }

    private static Task Process(MarketStateEngine engine, string match, string fair)
        => (Task)typeof(MarketStateEngine).GetMethod("ProcessFairOddsAsync", BindingFlags.Instance | BindingFlags.NonPublic)!
            .Invoke(engine, [match, fair, CancellationToken.None])!;

    [RedisRuntimeFact]
    public async Task RegisterDeduplicatesWithoutRenewingRequestOrRevertingCurrentRun()
    {
        var match = Guid.NewGuid().ToString("N");
        var state = State(match, 0.12345678901234567, -0.23456789012345678);
        var engine = Engine();
        var first = await Register(engine, state);
        var db = _redis.GetDatabase();
        var original = await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + match);
        Assert.Equal(state.DeltaVorpHome, first.dvorp_a); // Lua must preserve double bytes.
        Assert.Equal(state.DeltaVorpAway, first.dvorp_b);
        await db.KeyExpireAsync(KernelRedisProtocolV2.RequestPrefix + first.run_id, TimeSpan.FromSeconds(20));
        var duplicate = await engine.InvokeKernelAsync(match, 1500, 1500, state, null, "source", TimeSpan.FromHours(1));
        Assert.Equal("duplicate", duplicate.Status);
        Assert.Equal(original.ToString(), duplicate.PayloadJson);
        Assert.True(await db.KeyTimeToLiveAsync(KernelRedisProtocolV2.RequestPrefix + first.run_id) < TimeSpan.FromSeconds(21));
        Assert.Equal("1", (string?)await db.StringGetAsync(KernelRedisProtocolV2.SequencePrefix + match));
        await db.StringSetAsync("fair_odds:" + match, "old", TimeSpan.FromSeconds(5));
        await db.StringSetAsync(KernelRedisProtocolV2.LeasePrefix + first.run_id, "old-owner");
        var updated = state with { DeltaVorpAway = 1, AwayLineupComplete = true };
        var second = await Register(engine, updated, JsonSerializer.Serialize(state), "next-source");
        Assert.Equal("2", second.state_version);
        Assert.False(await db.KeyExistsAsync("fair_odds:" + match));
        Assert.False(await db.KeyExistsAsync(KernelRedisProtocolV2.LeasePrefix + first.run_id));
        Assert.Null(await db.SortedSetScoreAsync(KernelRedisProtocolV2.PendingKey, first.run_id));
        var superseded = await engine.InvokeKernelAsync(match, 1500, 1500, state, null, "source", TimeSpan.FromHours(1));
        Assert.Equal("superseded", superseded.Status);
        Assert.Equal(second.run_id, JsonSerializer.Deserialize<KernelInvokePayload>(
            (await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + match)).ToString())!.run_id);
        var conflict = await engine.InvokeKernelAsync(match, 1500, 1500, state, null, "conflict-source", TimeSpan.FromHours(1));
        Assert.Equal("conflict", conflict.Status);
    }

    [RedisRuntimeFact]
    public async Task ConsumerPublishesOneBatchAndRejectsRunChangedAfterItsReads()
    {
        var match = Guid.NewGuid().ToString("N");
        var state = State(match);
        var db = _redis.GetDatabase();
        var engine = Engine(marketMatch: match);
        var request = await Register(engine, state);
        var fair = await CompleteFixture(request);
        var seen = Channel.CreateUnbounded<string>();
        await _redis.GetSubscriber().SubscribeAsync(RedisChannel.Literal("bet_signals"), (_, value) =>
        {
            if (JsonDocument.Parse(value.ToString()).RootElement.GetProperty("MatchId").GetString() == match)
                seen.Writer.TryWrite(value.ToString());
        });
        await Process(engine, match, fair);
        var signal = JsonSerializer.Deserialize<BetSignal>(await seen.Reader.ReadAsync().AsTask().WaitAsync(TimeSpan.FromSeconds(2)))!;
        Assert.Equal(request.run_id, signal.RunId);
        Assert.Equal(request.state_version, signal.StateVersion);
        await Process(engine, match, fair);
        Assert.False(seen.Reader.TryRead(out _));

        var nextState = state with { DeltaVorpAway = 0.1 };
        var next = await Register(engine, nextState, JsonSerializer.Serialize(state), "next");
        var nextFair = await CompleteFixture(next);
        var finalFenceReached = false;
        var connection = ProxyDatabase((method, args) =>
        {
            if (method.Name != "ScriptEvaluateAsync") return method.Invoke(db, args);
            return ChangeBeforeFence();
            async Task<RedisResult> ChangeBeforeFence()
            {
                finalFenceReached = true;
                await Register(engine, nextState with { DeltaVorpAway = 0.2 }, JsonSerializer.Serialize(nextState), "newest");
                return await db.ScriptEvaluateAsync((string)args![0]!, (RedisKey[])args[1]!, (RedisValue[])args[2]!);
            }
        });
        await Process(Engine(connection, match), match, nextFair);
        Assert.True(finalFenceReached);
        Assert.False(await db.KeyExistsAsync(KernelRedisProtocolV2.SignalsPrefix + next.run_id));
        Assert.False(seen.Reader.TryRead(out _));
    }

    [RedisRuntimeFact]
    public async Task ConsumerRejectsMissingTtlPendingRequestAndChangedLineup()
    {
        var db = _redis.GetDatabase();
        foreach (var failure in new[] { "no-ttl", "pending", "changed-state", "missing-snapshot", "different-delta", "null-state", "missing-market" })
        {
            var match = Guid.NewGuid().ToString("N");
            var state = State(match);
            var engine = Engine(marketMatch: failure == "missing-market" ? null : match);
            var request = await Register(engine, state);
            var fair = await CompleteFixture(request, failure != "no-ttl");
            var requestKey = KernelRedisProtocolV2.RequestPrefix + request.run_id;
            if (failure == "pending") await db.HashSetAsync(requestKey, "status", "pending");
            if (failure == "changed-state") await db.StringSetAsync("lineup_state:" + match, "{}");
            if (failure == "missing-snapshot") await db.HashDeleteAsync(requestKey, "lineup_state");
            if (failure == "different-delta") await db.HashSetAsync(requestKey, "lineup_state", JsonSerializer.Serialize(state with { DeltaVorpHome = 1 }));
            if (failure == "null-state") await db.HashSetAsync(requestKey, "lineup_state", "null");
            await Process(engine, match, fair);
            Assert.False(await db.KeyExistsAsync(KernelRedisProtocolV2.SignalsPrefix + request.run_id));
        }
    }

    [RedisRuntimeFact]
    public async Task WatchdogCannotRestoreStaleStateAndInvalidatesOnlyItsCurrentRun()
    {
        var match = Guid.NewGuid().ToString("N");
        var state = State(match);
        var engine = Engine();
        var first = await Register(engine, state);
        var db = _redis.GetDatabase();
        var current = await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + match);
        var changed = state with { DeltaVorpHome = 1 };
        await db.StringSetAsync("lineup_state:" + match, JsonSerializer.Serialize(changed));
        var fallback = JsonSerializer.Serialize(state with { FallbackStrategy = "timeout_widen_variance" });
        RedisKey[] keys = ["lineup_state:" + match, KernelRedisProtocolV2.CurrentPrefix + match,
            "fair_odds:" + match, KernelRedisProtocolV2.PendingKey, KernelRedisProtocolV2.ReadyKey];
        RedisValue[] args = [JsonSerializer.Serialize(state), "1", current, fallback, 3600000,
            KernelRedisProtocolV2.LeasePrefix, "variance_widen"];
        Assert.Equal(0, (long)await db.ScriptEvaluateAsync(KernelRedisProtocolV2.ApplyWatchdog, keys, args));
        Assert.Equal(current, await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + match));
        Assert.Equal(JsonSerializer.Serialize(changed), (string?)await db.StringGetAsync("lineup_state:" + match));
        args[0] = JsonSerializer.Serialize(changed);
        args[2] = "old-current";
        Assert.Equal(0, (long)await db.ScriptEvaluateAsync(KernelRedisProtocolV2.ApplyWatchdog, keys, args));
        args[2] = current;
        await db.StringSetAsync(KernelRedisProtocolV2.LeasePrefix + first.run_id, "lease");
        Assert.Equal(1, (long)await db.ScriptEvaluateAsync(KernelRedisProtocolV2.ApplyWatchdog, keys, args));
        Assert.False(await db.KeyExistsAsync(KernelRedisProtocolV2.CurrentPrefix + match));
        Assert.False(await db.KeyExistsAsync(KernelRedisProtocolV2.LeasePrefix + first.run_id));
        Assert.Null(await db.SortedSetScoreAsync(KernelRedisProtocolV2.PendingKey, first.run_id));
    }

    private IConnectionMultiplexer ProxyDatabase(Func<MethodInfo, object?[]?, object?> handler)
    {
        var db = DispatchProxy.Create<IDatabase, KernelInvocationIdentityTests.RedisStub>();
        ((KernelInvocationIdentityTests.RedisStub)(object)db).Handler = handler;
        var redis = DispatchProxy.Create<IConnectionMultiplexer, KernelInvocationIdentityTests.RedisStub>();
        ((KernelInvocationIdentityTests.RedisStub)(object)redis).Handler = (method, args) =>
            method.Name == "GetDatabase" ? db : method.Invoke(_redis, args);
        return redis;
    }

    private async Task<LineupWorkerService> Worker(IConnectionMultiplexer? connection = null, int capacity = 16)
    {
        var vorpPath = Path.Combine(_root, "fencing-vorp.json");
        await File.WriteAllTextAsync(vorpPath, """{"beta_players":{"p1":1.0,"p2":2.0},"replacement_levels":{"UNKNOWN":0}}""");
        var vorp = new VorpStateService(NullLogger<VorpStateService>.Instance,
            CreateSettings(vorpPath, Path.Combine(_root, "absent.json")));
        await vorp.StartAsync(default);
        var cfg = Config(("Worker:QueueCapacity", capacity.ToString()));
        var redis = connection ?? _redis;
        return new LineupWorkerService(NullLogger<LineupWorkerService>.Instance, vorp,
            new LatencyAuditService(redis, NullLogger<LatencyAuditService>.Instance, cfg), Engine(redis), redis, cfg);
    }

    private static Task Handle(LineupWorkerService worker, LineupEvent ev)
        => (Task)typeof(LineupWorkerService).GetMethod("HandleLineupAsync", BindingFlags.Instance | BindingFlags.NonPublic)!
            .Invoke(worker, [ev, DateTimeOffset.UtcNow, CancellationToken.None])!;

    private static Channel<(LineupEvent Event, DateTimeOffset T1_Received)> Queue(LineupWorkerService worker)
        => (Channel<(LineupEvent Event, DateTimeOffset T1_Received)>)typeof(LineupWorkerService)
            .GetField("_queue", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(worker)!;

    [RedisRuntimeFact]
    public async Task ConcurrentLineupMergesAndRejectsOlderOrConflictingSameSideCaptures()
    {
        var worker = await Worker();
        var match = Guid.NewGuid().ToString("N");
        var home = new LineupEvent(match, "home", "away", "home", LineupFixtures.Starters("p1"), [], DateTimeOffset.UtcNow);
        var away = home with { Side = "away", Starters = LineupFixtures.Starters("p2") };
        await Task.WhenAll(Handle(worker, home), Handle(worker, away));
        var db = _redis.GetDatabase();
        var state = JsonSerializer.Deserialize<LineupState>((await db.StringGetAsync("lineup_state:" + match)).ToString())!;
        Assert.True(state.HomeLineupComplete && state.AwayLineupComplete);
        Assert.Equal(1, state.DeltaVorpHome);
        Assert.Equal(2, state.DeltaVorpAway);
        var later = home with { CapturedAt = home.CapturedAt.AddSeconds(1), Starters = LineupFixtures.Starters("p2") };
        await Handle(worker, later);
        var current = await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + match);
        await Handle(worker, home); // A, B, replay A must not create a newer run.
        await Handle(worker, later with { Starters = LineupFixtures.Starters("p1") }); // same declared clock, conflict.
        await Handle(worker, later); // exact replay.
        Assert.Equal(current, await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + match));
        Assert.Equal("3", (string?)await db.StringGetAsync(KernelRedisProtocolV2.SequencePrefix + match));
    }

    [RedisRuntimeFact]
    public async Task DropOldestFallbackNamesEvictedEventWhileRetainingNewest()
    {
        var worker = await Worker(capacity: 1);
        var old = new LineupEvent(Guid.NewGuid().ToString("N"), "home", "away", "home", LineupFixtures.Starters("p1"), [], DateTimeOffset.UtcNow);
        var latest = old with { MatchId = Guid.NewGuid().ToString("N"), Side = "away" };
        var fallback = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        await _redis.GetSubscriber().SubscribeAsync(RedisChannel.Literal("variance_widen"), (_, value) =>
        {
            if (value.ToString().Contains(old.MatchId)) fallback.TrySetResult(value.ToString());
        });
        Assert.True(Queue(worker).Writer.TryWrite((old, old.CapturedAt)));
        Assert.True(Queue(worker).Writer.TryWrite((latest, latest.CapturedAt)));
        var received = JsonSerializer.Deserialize<VarianceWideningSignal>(await fallback.Task.WaitAsync(TimeSpan.FromSeconds(2)))!;
        Assert.Equal(old.MatchId, received.MatchId);
        Assert.Equal(old.Side, received.Side);
        Assert.True(Queue(worker).Reader.TryRead(out var retained));
        Assert.Equal(latest, retained.Event);
    }

    [RedisRuntimeFact]
    public async Task QueueRetriesSameEventBeforeRegistrationAndAfterUncertainCommittedReply()
    {
        var db = _redis.GetDatabase();
        foreach (var failure in new[] { "before", "after", "exhausted", "permanent" })
        {
            var attempts = 0;
            var match = Guid.NewGuid().ToString("N");
            var connection = ProxyDatabase((method, args) =>
            {
                if (method.Name != "ScriptEvaluateAsync") return method.Invoke(db, args);
                attempts++;
                if (failure == "permanent") return Task.FromException<RedisResult>(new RedisServerException("invalid fixture"));
                if (failure == "exhausted" || (failure == "before" && attempts == 1))
                    return Task.FromException<RedisResult>(new RedisConnectionException(ConnectionFailureType.UnableToConnect, "synthetic transient"));
                if (failure == "after" && attempts == 1) return CommitThenLoseReply();
                return method.Invoke(db, args);
                async Task<RedisResult> CommitThenLoseReply()
                {
                    await db.ScriptEvaluateAsync((string)args![0]!, (RedisKey[])args[1]!, (RedisValue[])args[2]!);
                    throw new RedisTimeoutException("synthetic lost reply", CommandStatus.Sent);
                }
            });
            var worker = await Worker(connection);
            var ev = new LineupEvent(match, "home", "away", "home", LineupFixtures.Starters("p1"), [], DateTimeOffset.UtcNow);
            Queue(worker).Writer.TryWrite((ev, ev.CapturedAt));
            Queue(worker).Writer.Complete();
            await ((Task)typeof(LineupWorkerService).GetMethod("ProcessQueueAsync", BindingFlags.Instance | BindingFlags.NonPublic)!
                .Invoke(worker, [CancellationToken.None])!).WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(failure == "before" ? 2 : failure == "exhausted" ? 3 : 1, attempts);
            var sequence = await db.StringGetAsync(KernelRedisProtocolV2.SequencePrefix + match);
            Assert.Equal(failure is "before" or "after" ? "1" : null, (string?)sequence);
            if (failure == "after")
            {
                var pending = typeof(LineupWorkerService).GetField("_pending", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(worker)!;
                Assert.Equal(1, (int)pending.GetType().GetProperty("Count")!.GetValue(pending)!);
            }
        }
    }
}
