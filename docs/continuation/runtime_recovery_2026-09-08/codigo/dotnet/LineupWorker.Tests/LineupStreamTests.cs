using System.Reflection;
using System.Text.Json;
using LineupWorker.Models;
using LineupWorker.Services;
using Microsoft.Extensions.Logging.Abstractions;
using StackExchange.Redis;
using Xunit;

namespace LineupWorker.Tests;

internal static class LineupFixtures
{
    public static string[] Starters(string primary) =>
        [primary, .. Enumerable.Range(0, 10).Select(i => "SYNTHETIC_ZERO_" + i)];
}

public sealed partial class WorkerRuntimeTests
{
    private static LineupEvent InboxEvent() => new(Guid.NewGuid().ToString("N"),
        "SYNTHETIC_HOME", "SYNTHETIC_AWAY", "home", LineupFixtures.Starters("p1"), [], DateTimeOffset.UtcNow);

    private Task<RedisValue> Enqueue(LineupEvent ev) => _redis.GetDatabase().StreamAddAsync(
        LineupStreamConsumer.StreamKey, [new NameValueEntry("payload", JsonSerializer.Serialize(ev))]);

    private LineupStreamConsumer Inbox(Func<LineupEvent, DateTimeOffset, CancellationToken, Task> handle,
        IDatabase? db = null) => new(db ?? _redis.GetDatabase(), NullLogger.Instance, handle, TimeSpan.FromMinutes(55));

    [RedisRuntimeFact]
    public async Task InboxRetainsInputBeforeWorkerStartsAndRecoversAfterRepeatedFailures()
    {
        var ev = InboxEvent();
        await Enqueue(ev); // There is no subscriber, group or process yet.
        var attempts = 0;
        var inbox = Inbox((_, _, _) => { attempts++; throw new InvalidOperationException("synthetic temporary failure"); });
        for (var i = 0; i < 4; i++)
        {
            await inbox.ReadOnceAsync(default);
            if (i < 3) await Task.Delay(1050);
        }
        Assert.Equal(4, attempts); // No three-attempt loss.
        Assert.Equal(1, await _redis.GetDatabase().StreamLengthAsync(LineupStreamConsumer.StreamKey));
        await Task.Delay(1050);
        LineupEvent? received = null;
        await Inbox((entry, _, _) => { received = entry; return Task.CompletedTask; }).ReadOnceAsync(default);
        Assert.Equal(ev.MatchId, received!.MatchId);
        Assert.Equal(0, await _redis.GetDatabase().StreamLengthAsync(LineupStreamConsumer.StreamKey));
        Assert.Equal(0, (await _redis.GetDatabase().StreamPendingAsync(LineupStreamConsumer.StreamKey, LineupStreamConsumer.Group)).PendingMessageCount);
    }

    [RedisRuntimeFact]
    public async Task InboxRegistrationSurvivesCrashBeforeAckWithoutCreatingAnotherVersion()
    {
        var worker = await Worker();
        var ev = InboxEvent();
        await Enqueue(ev);
        await Inbox(async (entry, _, _) =>
        {
            await Handle(worker, entry);
            throw new InvalidOperationException("synthetic process loss after successful registration");
        }).ReadOnceAsync(default);
        var db = _redis.GetDatabase();
        var current = await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + ev.MatchId);
        Assert.True(current.HasValue);
        await Task.Delay(1050);
        await Inbox((entry, _, _) => Handle(worker, entry)).ReadOnceAsync(default);
        Assert.Equal(current, await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + ev.MatchId));
        Assert.Equal("1", (string?)await db.StringGetAsync(KernelRedisProtocolV2.SequencePrefix + ev.MatchId));
        Assert.Equal(0, await db.StreamLengthAsync(LineupStreamConsumer.StreamKey));
    }

    [RedisRuntimeFact]
    public async Task InboxPoisonEntryDoesNotStarveLaterWorkAndCancellationDoesNotAck()
    {
        var first = InboxEvent();
        var second = InboxEvent();
        await Enqueue(first);
        await Enqueue(second);
        var accepted = new List<string>();
        await Inbox((ev, _, _) =>
        {
            if (ev.MatchId == first.MatchId) throw new InvalidOperationException();
            accepted.Add(ev.MatchId);
            return Task.CompletedTask;
        }).ReadOnceAsync(default);
        Assert.Equal([second.MatchId], accepted);
        Assert.Equal(1, await _redis.GetDatabase().StreamLengthAsync(LineupStreamConsumer.StreamKey));
        await Task.Delay(1050);
        using var cancel = new CancellationTokenSource();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => Inbox((_, _, _) =>
        {
            cancel.Cancel();
            return Task.CompletedTask;
        }).ReadOnceAsync(cancel.Token));
        Assert.Equal(1, (await _redis.GetDatabase().StreamPendingAsync(LineupStreamConsumer.StreamKey, LineupStreamConsumer.Group)).PendingMessageCount);
    }

    [RedisRuntimeFact]
    public async Task InboxRejectsMalformedExpiredAndFuturePayloadsWithoutLeakingTheirContents()
    {
        var db = _redis.GetDatabase();
        var valid = InboxEvent();
        var variants = new[]
        {
            "SYNTHETIC_SECRET_MARKER", "null", "{}", "", new string('x', 65537),
            JsonSerializer.Serialize(valid with { CapturedAt = DateTimeOffset.UtcNow.AddHours(-1) }),
            JsonSerializer.Serialize(valid with { CapturedAt = DateTimeOffset.UtcNow.AddHours(1) }),
            JsonSerializer.Serialize(valid with { Starters = LineupFixtures.Starters("SYNTHETIC_ZERO_0") }),
            JsonSerializer.Serialize(valid with { Subs = ["p1"] }),
        };
        foreach (var raw in variants)
            await db.StreamAddAsync(LineupStreamConsumer.StreamKey, [new NameValueEntry("payload", raw)]);
        await db.StreamAddAsync(LineupStreamConsumer.StreamKey, [new NameValueEntry("other", "SYNTHETIC_SECRET_MARKER")]);
        await Inbox((_, _, _) => throw new Xunit.Sdk.XunitException("Malformed event must not reach registration")).ReadOnceAsync(default);
        Assert.Equal(0, await db.StreamLengthAsync(LineupStreamConsumer.StreamKey));
        var rejected = await db.StreamRangeAsync(LineupStreamConsumer.RejectedKey);
        Assert.Equal(10, rejected.Length);
        Assert.All(rejected, entry =>
        {
            Assert.Equal(3, entry.Values.Length);
            Assert.DoesNotContain("SYNTHETIC_SECRET_MARKER", JsonSerializer.Serialize(entry.Values));
            Assert.Equal(64, entry.Values.Single(v => v.Name == "sha256").Value.ToString().Length);
        });
    }

    [RedisRuntimeFact]
    public async Task InboxReadLoopRecoversRedisFailureAndStopsOnCancellation()
    {
        await Enqueue(InboxEvent());
        var real = _redis.GetDatabase();
        var calls = 0;
        var proxy = DispatchProxy.Create<IDatabase, KernelInvocationIdentityTests.RedisStub>();
        ((KernelInvocationIdentityTests.RedisStub)(object)proxy).Handler = (method, args) =>
        {
            if (method.Name == "StreamCreateConsumerGroupAsync" && calls++ == 0)
                return Task.FromException<bool>(new RedisConnectionException(ConnectionFailureType.UnableToConnect, "synthetic"));
            return method.Invoke(real, args);
        };
        var handled = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        using var cancel = new CancellationTokenSource();
        var loop = Inbox((_, _, _) => { handled.TrySetResult(); return Task.CompletedTask; }, proxy).RunAsync(cancel.Token);
        await handled.Task.WaitAsync(TimeSpan.FromSeconds(3));
        cancel.Cancel();
        try { await loop.WaitAsync(TimeSpan.FromSeconds(2)); }
        catch (OperationCanceledException) { }
        Assert.True(calls >= 2);
    }
}

public sealed class LineupValidationTests
{
    [Fact]
    public void InvalidLineupsAreRejectedBeforeComputingVorp()
    {
        var good = new LineupEvent("match", "home", "away", "home", LineupFixtures.Starters("p"), [], DateTimeOffset.UtcNow);
        Assert.True(LineupStreamConsumer.IsValid(good));
        foreach (var invalid in new[]
        {
            good with { MatchId = "" }, good with { MatchId = new string('m', 201) },
            good with { HomeTeam = "" }, good with { AwayTeam = "" }, good with { Side = "other" },
            good with { CapturedAt = default }, good with { Starters = null! }, good with { Subs = null! },
            good with { Starters = [] }, good with { Starters = ["p"] },
            good with { Starters = Enumerable.Range(0, 12).Select(i => i.ToString()).ToArray() },
            good with { Subs = new string[31] }, good with { Starters = LineupFixtures.Starters("") },
            good with { Starters = LineupFixtures.Starters(new string('p', 201)) }, good with { Subs = ["s", "s"] },
        }) Assert.False(LineupStreamConsumer.IsValid(invalid));
        Assert.Throws<ArgumentOutOfRangeException>(() => new LineupStreamConsumer(null!, NullLogger.Instance,
            (_, _, _) => Task.CompletedTask, TimeSpan.Zero));
    }
}
