using System.Reflection;
using System.Text;
using System.Text.Json;
using LineupWorker.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using StackExchange.Redis;
using Xunit;

namespace LineupWorker.Tests;

public sealed class FairOddsCorrelationTests
{
    [Theory]
    [InlineData("match", "job", "new-run")]
    [InlineData("another-match", "job", "run")]
    [InlineData("match", "another-job", "run")]
    public async Task RejectsNotificationWhoseKeyBelongsToAnotherInvocation(
        string keyMatch, string keyJob, string keyRun)
    {
        var signals = await ProcessAsync(FairOdds(keyMatch, keyJob, keyRun), FairOdds());

        Assert.Empty(signals);
    }

    [Fact]
    public async Task RejectsUncorrelatedNotificationEvenWhenKeyIsValid()
    {
        var signals = await ProcessAsync(FairOdds(), "{}");

        Assert.Empty(signals);
    }

    [Fact]
    public async Task RejectsMatchingPayloadsForAnotherChannelMatch()
    {
        var signals = await ProcessAsync(FairOdds("another-match"), FairOdds("another-match"));

        Assert.Empty(signals);
    }

    [Theory]
    [InlineData("[]")]
    [InlineData("null")]
    [InlineData("{")]
    [InlineData("{\"protocol_version\":1}")]
    public async Task MalformedNotificationFailsClosed(string notified)
    {
        var signals = await ProcessAsync(FairOdds(), notified);

        Assert.Empty(signals);
    }

    [Fact]
    public async Task MatchingNotificationAndLiveKeyCanProduceSignal()
    {
        var signals = await ProcessAsync(FairOdds(), FairOdds());

        Assert.Single(signals);
    }

    [Fact]
    public async Task ExpiredKeyCannotProduceSignal()
    {
        var signals = await ProcessAsync(null, FairOdds());

        Assert.Empty(signals);
    }

    private static string FairOdds(string match = "match", string job = "job", string run = "run")
        => JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["protocol_version"] = "brasileirao.redis/1",
            ["job_id"] = job, ["run_id"] = run, ["match_id"] = match,
            ["1"] = 2.0, ["X"] = 3.0, ["2"] = 4.0,
        });

    private static async Task<List<string>> ProcessAsync(string? stored, string notified)
    {
        var signals = new List<string>();
        var database = DispatchProxy.Create<IDatabase, KernelInvocationIdentityTests.RedisStub>();
        ((KernelInvocationIdentityTests.RedisStub)(object)database).Handler = (method, args) =>
        {
            Assert.Equal("StringGetAsync", method.Name);
            RedisValue value = args![0]!.ToString() == "fair_odds:match" ? stored : null;
            return Task.FromResult(value);
        };
        var subscriber = DispatchProxy.Create<ISubscriber, KernelInvocationIdentityTests.RedisStub>();
        ((KernelInvocationIdentityTests.RedisStub)(object)subscriber).Handler = (method, args) =>
        {
            Assert.Equal("PublishAsync", method.Name);
            Assert.Equal("bet_signals", args![0]!.ToString());
            signals.Add(args[1]!.ToString()!);
            return Task.FromResult(1L);
        };
        var redis = DispatchProxy.Create<IConnectionMultiplexer, KernelInvocationIdentityTests.RedisStub>();
        ((KernelInvocationIdentityTests.RedisStub)(object)redis).Handler = (method, _) => method.Name switch
        {
            "GetDatabase" => database,
            "GetSubscriber" => subscriber,
            _ => throw new InvalidOperationException(method.Name),
        };
        var config = new ConfigurationBuilder().Build();
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, config);
        var parse = typeof(MarketOddsCache).GetMethod("ParseAndUpdate", BindingFlags.Instance | BindingFlags.NonPublic)!;
        parse.Invoke(cache, [new ReadOnlyMemory<byte>(Encoding.UTF8.GetBytes(
            """{"match_id":"match","home":2.4,"draw":3.0,"away":4.0}"""))]);
        var audit = new LatencyAuditService(redis, NullLogger<LatencyAuditService>.Instance, config);
        var engine = new MarketStateEngine(redis, cache, audit, NullLogger<MarketStateEngine>.Instance, config);
        var process = typeof(MarketStateEngine).GetMethod("ProcessFairOddsAsync", BindingFlags.Instance | BindingFlags.NonPublic)!;

        await (Task)process.Invoke(engine, ["match", notified, CancellationToken.None])!;

        return signals;
    }
}
