using System.Reflection;
using System.Text.Json;
using LineupWorker.Models;
using LineupWorker.Services;
using StackExchange.Redis;
using Xunit;

namespace LineupWorker.Tests;

public sealed partial class WorkerRuntimeTests
{
    private const string WatchdogIndex = "lineup:v2:watchdogs";

    private static Task RunWatchdog(LineupWorkerService worker, CancellationToken ct)
        => (Task)typeof(LineupWorkerService).GetMethod("TimeoutWatchdogAsync", BindingFlags.Instance | BindingFlags.NonPublic)!
            .Invoke(worker, [ct])!;

    [RedisRuntimeFact]
    public async Task AcknowledgedFirstLineupStillTimesOutAfterWorkerRestart()
    {
        var first = await Worker(timeoutMinutes: 1, watchdogIntervalSeconds: 1);
        var ev = InboxEvent() with { CapturedAt = DateTimeOffset.UtcNow.AddSeconds(-59.5) };
        await Enqueue(ev);
        await Inbox((entry, _, _) => Handle(first, entry)).ReadOnceAsync(default);
        var db = _redis.GetDatabase();
        Assert.Equal(0, await db.StreamLengthAsync(LineupStreamConsumer.StreamKey));
        Assert.Equal(0, (await db.StreamPendingAsync(LineupStreamConsumer.StreamKey, LineupStreamConsumer.Group)).PendingMessageCount);
        Assert.True(await db.KeyExistsAsync(KernelRedisProtocolV2.CurrentPrefix + ev.MatchId));
        await Task.Delay(700);

        // This instance has never handled any lineup and has no in-memory tracking.
        var restarted = await Worker(timeoutMinutes: 1, watchdogIntervalSeconds: 1);
        var fallback = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        await _redis.GetSubscriber().SubscribeAsync(RedisChannel.Literal("variance_widen"), (_, value) =>
        {
            if (value.ToString().Contains(ev.MatchId)) fallback.TrySetResult(value.ToString());
        });
        using var cancel = new CancellationTokenSource();
        var watchdog = RunWatchdog(restarted, cancel.Token);
        try
        {
            var signal = JsonSerializer.Deserialize<VarianceWideningSignal>(await fallback.Task.WaitAsync(TimeSpan.FromSeconds(3)))!;
            Assert.Equal("away", signal.Side);
            Assert.False(await db.KeyExistsAsync(KernelRedisProtocolV2.CurrentPrefix + ev.MatchId));
            Assert.Null(await db.SortedSetScoreAsync(WatchdogIndex, ev.MatchId));
            var state = JsonSerializer.Deserialize<LineupState>((await db.StringGetAsync("lineup_state:" + ev.MatchId)).ToString())!;
            Assert.Equal("timeout_widen_variance", state.FallbackStrategy);
        }
        finally
        {
            cancel.Cancel();
            try { await watchdog; } catch (OperationCanceledException) { }
        }
    }

    [RedisRuntimeFact]
    public async Task CorrectionPreservesDeadlineAndDuplicateRepairsMissingIndexBeforeAck()
    {
        var worker = await Worker(timeoutMinutes: 1);
        var ev = InboxEvent();
        await Handle(worker, ev);
        var db = _redis.GetDatabase();
        var original = await db.SortedSetScoreAsync(WatchdogIndex, ev.MatchId);
        Assert.NotNull(original);
        var correction = ev with { CapturedAt = ev.CapturedAt.AddSeconds(20), Starters = LineupFixtures.Starters("p2") };
        await Handle(worker, correction);
        Assert.Equal(original, await db.SortedSetScoreAsync(WatchdogIndex, ev.MatchId));
        await db.SortedSetRemoveAsync(WatchdogIndex, ev.MatchId);
        await Enqueue(correction);
        await Inbox((entry, _, _) => Handle(worker, entry)).ReadOnceAsync(default);
        Assert.Equal(original, await db.SortedSetScoreAsync(WatchdogIndex, ev.MatchId));
        Assert.Equal(0, await db.StreamLengthAsync(LineupStreamConsumer.StreamKey));
        Assert.Equal("2", (string?)await db.StringGetAsync(KernelRedisProtocolV2.SequencePrefix + ev.MatchId));
        await Handle(worker, correction with { Side = "away" });
        Assert.Null(await db.SortedSetScoreAsync(WatchdogIndex, ev.MatchId));
    }

    [RedisRuntimeFact]
    public async Task InvalidWatchdogIndexCannotAllowRegistrationOrAcknowledgement()
    {
        var worker = await Worker();
        var ev = InboxEvent();
        var db = _redis.GetDatabase();
        await db.StringSetAsync(WatchdogIndex, "invalid-index-type");
        await Enqueue(ev);
        await Inbox((entry, _, _) => Handle(worker, entry)).ReadOnceAsync(default);
        Assert.False(await db.KeyExistsAsync("lineup_state:" + ev.MatchId));
        Assert.False(await db.KeyExistsAsync(KernelRedisProtocolV2.CurrentPrefix + ev.MatchId));
        Assert.False(await db.KeyExistsAsync(KernelRedisProtocolV2.SequencePrefix + ev.MatchId));
        Assert.Equal(1, (await db.StreamPendingAsync(LineupStreamConsumer.StreamKey, LineupStreamConsumer.Group)).PendingMessageCount);
        await db.KeyDeleteAsync(WatchdogIndex);
        await Task.Delay(1050);
        await Inbox((entry, _, _) => Handle(worker, entry)).ReadOnceAsync(default);
        Assert.True((await db.SortedSetScoreAsync(WatchdogIndex, ev.MatchId)).HasValue);
        Assert.Equal(0, await db.StreamLengthAsync(LineupStreamConsumer.StreamKey));
    }

    [RedisRuntimeFact]
    public async Task StaleWatchdogCleanupCannotRemoveIndexFromNewSnapshot()
    {
        var worker = await Worker();
        var ev = InboxEvent();
        await Handle(worker, ev);
        var db = _redis.GetDatabase();
        var priorState = await db.StringGetAsync("lineup_state:" + ev.MatchId);
        var priorRun = await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + ev.MatchId);
        await Handle(worker, ev with { CapturedAt = ev.CapturedAt.AddSeconds(1), Starters = LineupFixtures.Starters("p2") });
        var index = await db.SortedSetScoreAsync(WatchdogIndex, ev.MatchId);
        Assert.Equal(0, (long)await db.ScriptEvaluateAsync(WatchdogStateStore.Synchronize,
            ["lineup_state:" + ev.MatchId, KernelRedisProtocolV2.CurrentPrefix + ev.MatchId, WatchdogIndex],
            ["1", priorState, "1", priorRun, ev.MatchId]));
        Assert.Equal(index, await db.SortedSetScoreAsync(WatchdogIndex, ev.MatchId));
        Assert.NotEqual(priorRun, await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + ev.MatchId));
    }
}
