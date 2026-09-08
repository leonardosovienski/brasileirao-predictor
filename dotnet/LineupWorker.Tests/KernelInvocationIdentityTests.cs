using System.Reflection;
using System.Text.Json;
using LineupWorker.Models;
using LineupWorker.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using StackExchange.Redis;
using Xunit;

namespace LineupWorker.Tests;

public sealed class KernelInvocationIdentityTests
{
    [Fact]
    public async Task CompletedLineupUsesDifferentClaimFromPartialLineup()
    {
        var (engine, messages) = CreateEngine();

        await Invoke(engine, 1, 0, "home-event");
        await Invoke(engine, 1, 2, "away-event");

        Assert.Equal(2, messages.Count);
        Assert.NotEqual(messages[0].idempotency_key, messages[1].idempotency_key);
        Assert.Equal(0, messages[0].dvorp_b);
        Assert.Equal(2, messages[1].dvorp_b);
    }

    [Fact]
    public async Task ReplayingSameSourceEventAndInputsReusesClaim()
    {
        var (engine, messages) = CreateEngine();

        await Invoke(engine, 1, 2, "same-event");
        await Invoke(engine, 1, 2, "same-event");

        Assert.Equal(messages[0].idempotency_key, messages[1].idempotency_key);
        Assert.NotEqual(messages[0].run_id, messages[1].run_id);
    }

    [Fact]
    public async Task CorrectionBackToEarlierInputsGetsNewClaim()
    {
        var (engine, messages) = CreateEngine();

        await Invoke(engine, 1, 0, "original-event");
        await Invoke(engine, 1, 2, "changed-event");
        await Invoke(engine, 1, 0, "corrected-event");

        Assert.Equal(3, messages.Select(message => message.idempotency_key).Distinct().Count());
    }

    [Fact]
    public async Task EventIdentityAlsoIncludesCurrentCalculationInputs()
    {
        var (engine, messages) = CreateEngine();

        await Invoke(engine, 1, 0, "same-event");
        await Invoke(engine, 1, 2, "same-event");

        Assert.NotEqual(messages[0].idempotency_key, messages[1].idempotency_key);
    }

    [Fact]
    public async Task ReplayAfterEngineRestartKeepsDeterministicClaim()
    {
        var (firstEngine, firstMessages) = CreateEngine();
        var (secondEngine, secondMessages) = CreateEngine();

        await Invoke(firstEngine, 1, 2, "same-event");
        await Invoke(secondEngine, 1, 2, "same-event");

        Assert.Equal(firstMessages[0].idempotency_key, secondMessages[0].idempotency_key);
    }

    private static (MarketStateEngine Engine, List<KernelInvokePayload> Messages) CreateEngine()
    {
        var messages = new List<KernelInvokePayload>();
        var database = DispatchProxy.Create<IDatabase, RedisStub>();
        ((RedisStub)(object)database).Handler = (method, args) =>
        {
            Assert.Equal("ScriptEvaluateAsync", method.Name);
            Assert.Equal(KernelRedisProtocolV2.Register, args![0]);
            var arguments = (RedisValue[])args[2]!;
            Assert.Equal(KernelRedisProtocolV2.InvokeChannel, arguments[6].ToString());
            var json = arguments[3].ToString().Replace(KernelRedisProtocolV2.VersionPlaceholder, "1");
            messages.Add(JsonSerializer.Deserialize<KernelInvokePayload>(json)!);
            return Task.FromResult(RedisResult.Create(new RedisValue[] { "registered", json }));
        };
        var redis = DispatchProxy.Create<IConnectionMultiplexer, RedisStub>();
        ((RedisStub)(object)redis).Handler = (method, _) =>
        {
            Assert.Equal("GetDatabase", method.Name);
            return database;
        };
        var config = new ConfigurationBuilder().Build();
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, config);
        var audit = new LatencyAuditService(redis, NullLogger<LatencyAuditService>.Instance, config);
        return (new MarketStateEngine(redis, cache, audit,
            NullLogger<MarketStateEngine>.Instance, config), messages);
    }

    private static Task<KernelRegistrationResult> Invoke(MarketStateEngine engine, double home, double away, string source)
    {
        var now = DateTimeOffset.UtcNow;
        return engine.InvokeKernelAsync("match", 1500, 1500,
            new LineupState("match", home, away, true, away != 0, now, now, "none"),
            null, source, TimeSpan.FromHours(6));
    }

    public class RedisStub : DispatchProxy
    {
        public Func<MethodInfo, object?[]?, object?> Handler { get; set; } = null!;

        protected override object? Invoke(MethodInfo? targetMethod, object?[]? args)
            => Handler(targetMethod!, args);
    }
}
