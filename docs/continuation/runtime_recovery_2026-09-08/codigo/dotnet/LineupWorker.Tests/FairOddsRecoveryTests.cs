using System.Text.Json;
using LineupWorker.Services;
using StackExchange.Redis;
using Xunit;

namespace LineupWorker.Tests;

public sealed partial class WorkerRuntimeTests
{
    // Literals deliberately allow the lost-notification regression to run against
    // the archived pre-recovery producer/consumer before the new implementation.
    private const string ReadyIndex = "kernel:v2:ready";
    private const string SignalOutbox = "kernel:v2:signal_outbox";

    private async Task IndexReady(string match, string run)
    {
        var deadline = (long)await _redis.GetDatabase().ExecuteAsync("PEXPIRETIME", "fair_odds:" + match);
        await _redis.GetDatabase().SortedSetAddAsync(ReadyIndex, run, deadline);
    }

    private static async Task WaitUntil(Func<Task<bool>> ready)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(3));
        while (!await ready()) await Task.Delay(20, timeout.Token);
    }

    [RedisRuntimeFact]
    public async Task LostReadyNotificationIsRecoveredFromRetainedIndexAtStartup()
    {
        var match = Guid.NewGuid().ToString("N");
        var engine = Engine(marketMatch: match);
        var request = await Register(engine, State(match));
        var fair = await CompleteFixture(request);
        await IndexReady(match, request.run_id);
        var db = _redis.GetDatabase();
        var expiresBefore = (long)await db.ExecuteAsync("PEXPIRETIME", "fair_odds:" + match);
        // No fair_odds_ready notification and no bet_signals subscriber exist.
        await engine.StartAsync(default);
        try
        {
            await WaitUntil(async () => await db.StreamLengthAsync(SignalOutbox) == 1);
            Assert.Null(await db.SortedSetScoreAsync(ReadyIndex, request.run_id));
            var row = Assert.Single(await db.StreamRangeAsync(SignalOutbox));
            var fields = row.Values.ToDictionary(value => value.Name.ToString(), value => value.Value.ToString());
            Assert.Equal(request.run_id, fields["run_id"]);
            Assert.Equal(match, fields["match_id"]);
            Assert.Equal(request.state_version, fields["state_version"]);
            Assert.InRange(long.Parse(fields["expires_at_ms"]), expiresBefore - 2, expiresBefore + 2);
            using var batch = JsonDocument.Parse(fields["batch_json"]);
            Assert.Single(batch.RootElement.EnumerateArray());
            Assert.Equal(request.run_id, batch.RootElement[0].GetProperty("RunId").GetString());
            Assert.Equal(expiresBefore, (long)await db.ExecuteAsync("PEXPIRETIME", "fair_odds:" + match));
            // Both a redundant wakeup and a ready-index replay must hit the same dedup.
            await IndexReady(match, request.run_id);
            await _redis.GetSubscriber().PublishAsync(RedisChannel.Literal("fair_odds_ready:" + match), fair);
            await WaitUntil(async () => !(await db.SortedSetScoreAsync(ReadyIndex, request.run_id)).HasValue);
            Assert.Equal(1, await db.StreamLengthAsync(SignalOutbox));
            var prior = await db.StringGetAsync("lineup_state:" + match);
            var updated = JsonSerializer.Deserialize<LineupWorker.Models.LineupState>(prior.ToString())! with { DeltaVorpAway = 0.1 };
            var second = await Register(engine, updated, prior.ToString(), "later-completion");
            await CompleteFixture(second);
            await IndexReady(match, second.run_id); // Lost notification while MSE is already running.
            await WaitUntil(async () => await db.StreamLengthAsync(SignalOutbox) == 2);
        }
        finally { await engine.StopAsync(default); }
    }

    [RedisRuntimeFact]
    public async Task ReadyPollRecoversAfterTransientRedisFailureWithoutDuplicatingOutbox()
    {
        var match = Guid.NewGuid().ToString("N");
        var request = await Register(Engine(), State(match));
        await CompleteFixture(request);
        await IndexReady(match, request.run_id);
        var attempts = 0;
        var db = _redis.GetDatabase();
        var connection = ProxyDatabase((method, args) =>
        {
            if (method.Name == "ScriptEvaluateAsync" && args![0]!.ToString()!.Contains("ZSCAN") && ++attempts == 1)
                return Task.FromException<RedisResult>(new RedisConnectionException(ConnectionFailureType.UnableToConnect, "synthetic disconnect"));
            return method.Invoke(db, args);
        });
        var engine = Engine(connection, match);
        await engine.StartAsync(default);
        try
        {
            await WaitUntil(async () => await db.StreamLengthAsync(SignalOutbox) == 1);
            Assert.True(attempts >= 2);
        }
        finally { await engine.StopAsync(default); }
        await Process(engine, match, (await db.StringGetAsync("fair_odds:" + match)).ToString());
        Assert.Equal(1, await db.StreamLengthAsync(SignalOutbox));
    }

    [RedisRuntimeFact]
    public async Task ReadyPollRejectsExpiredAndSupersededResultsWithoutRenewal()
    {
        var db = _redis.GetDatabase();
        var match = Guid.NewGuid().ToString("N");
        var state = State(match);
        var engine = Engine(marketMatch: match);
        var request = await Register(engine, state);
        await CompleteFixture(request);
        await IndexReady(match, request.run_id);
        await Register(engine, state with { DeltaVorpAway = 1 }, JsonSerializer.Serialize(state), "newer");
        Assert.Null(await db.SortedSetScoreAsync(ReadyIndex, request.run_id));
        // Reintroducing a stale hint cannot restore authority to an obsolete run.
        await db.SortedSetAddAsync(ReadyIndex, request.run_id, DateTimeOffset.UtcNow.AddSeconds(2).ToUnixTimeMilliseconds());
        var expired = await Register(engine, State("expired-" + match));
        await CompleteFixture(expired);
        await db.KeyDeleteAsync("fair_odds:" + expired.match_id);
        await db.SortedSetAddAsync(ReadyIndex, expired.run_id, 1);
        await engine.StartAsync(default);
        try
        {
            await WaitUntil(async () => !(await db.SortedSetScoreAsync(ReadyIndex, expired.run_id)).HasValue);
            Assert.Equal(0, await db.StreamLengthAsync(SignalOutbox));
            Assert.False(await db.KeyExistsAsync("fair_odds:" + expired.match_id));
        }
        finally { await engine.StopAsync(default); }
    }

    [RedisRuntimeFact]
    public async Task InvalidOutboxTypeCannotConsumeDedupOrReadyHint()
    {
        var match = Guid.NewGuid().ToString("N");
        var engine = Engine(marketMatch: match);
        var request = await Register(engine, State(match));
        var fair = await CompleteFixture(request);
        await IndexReady(match, request.run_id);
        var db = _redis.GetDatabase();
        await db.StringSetAsync(SignalOutbox, "wrong-type");
        await Assert.ThrowsAsync<RedisServerException>(() => Process(engine, match, fair));
        Assert.False(await db.KeyExistsAsync(KernelRedisProtocolV2.SignalsPrefix + request.run_id));
        Assert.True((await db.SortedSetScoreAsync(ReadyIndex, request.run_id)).HasValue);
        await db.KeyDeleteAsync(SignalOutbox);
        await Process(engine, match, fair);
        Assert.Equal(1, await db.StreamLengthAsync(SignalOutbox));
    }

    [RedisRuntimeFact]
    public async Task LatencyAuditFailureDoesNotPreventFencedOutboxRetention()
    {
        var db = _redis.GetDatabase();
        var match = Guid.NewGuid().ToString("N");
        var engine = Engine(marketMatch: match);
        var request = await Register(engine, State(match));
        var fair = await CompleteFixture(request);
        await db.StringSetAsync("latency_audit:" + match + ":combined", "{");
        await Process(engine, match, fair);
        Assert.Equal(1, await db.StreamLengthAsync(SignalOutbox));
    }

    [RedisRuntimeFact]
    public async Task OutboxRetentionIsExactlyBoundedAndKeepsNewBatch()
    {
        var db = _redis.GetDatabase();
        await db.ScriptEvaluateAsync("for i=1,10000 do redis.call('XADD',KEYS[1],'*','fixture','retention') end return 1", [SignalOutbox]);
        var oldest = (await db.StreamRangeAsync(SignalOutbox, count: 1))[0].Id;
        var match = Guid.NewGuid().ToString("N");
        var engine = Engine(marketMatch: match);
        var request = await Register(engine, State(match));
        var fair = await CompleteFixture(request);
        await Process(engine, match, fair);
        Assert.Equal(10000, await db.StreamLengthAsync(SignalOutbox));
        Assert.NotEqual(oldest, (await db.StreamRangeAsync(SignalOutbox, count: 1))[0].Id);
        var latest = Assert.Single(await db.StreamRangeAsync(SignalOutbox, count: 1, messageOrder: Order.Descending));
        Assert.Contains(latest.Values, value => value.Name == "run_id" && value.Value == request.run_id);
        await Process(engine, match, fair);
        Assert.Equal(latest.Id, (await db.StreamRangeAsync(SignalOutbox, count: 1, messageOrder: Order.Descending))[0].Id);
    }

    [RedisRuntimeFact]
    public async Task MalformedAndMissingReadyResultsDoNotHideAnotherValidRun()
    {
        var db = _redis.GetDatabase();
        var match = Guid.NewGuid().ToString("N");
        var engine = Engine(marketMatch: match);
        var request = await Register(engine, State(match));
        var fair = await CompleteFixture(request);
        await IndexReady(match, request.run_id);
        foreach (var (run, result) in new[] { ("bad-json", "{"), ("missing", (string?)null), ("wrong-run", fair) })
        {
            var badRun = match + run;
            if (result is not null) await db.HashSetAsync(KernelRedisProtocolV2.RequestPrefix + badRun, "result", result);
            await db.SortedSetAddAsync(ReadyIndex, badRun, DateTimeOffset.UtcNow.AddSeconds(5).ToUnixTimeMilliseconds());
        }
        await engine.StartAsync(default);
        try { await WaitUntil(async () => await db.StreamLengthAsync(SignalOutbox) == 1); }
        finally { await engine.StopAsync(default); }
    }
}
