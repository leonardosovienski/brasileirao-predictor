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

        await engine.InvokeKernelAsync("match", 1500, 1500, 1, 0, "home-event");
        await engine.InvokeKernelAsync("match", 1500, 1500, 1, 2, "away-event");

        Assert.Equal(2, messages.Count);
        Assert.NotEqual(messages[0].idempotency_key, messages[1].idempotency_key);
        Assert.Equal(0, messages[0].dvorp_b);
        Assert.Equal(2, messages[1].dvorp_b);
    }

    [Fact]
    public async Task ReplayingSameSourceEventAndInputsReusesClaim()
    {
        var (engine, messages) = CreateEngine();

        await engine.InvokeKernelAsync("match", 1500, 1500, 1, 2, "same-event");
        await engine.InvokeKernelAsync("match", 1500, 1500, 1, 2, "same-event");

        Assert.Equal(messages[0].idempotency_key, messages[1].idempotency_key);
        Assert.NotEqual(messages[0].run_id, messages[1].run_id);
    }

    [Fact]
    public async Task CorrectionBackToEarlierInputsGetsNewClaim()
    {
        var (engine, messages) = CreateEngine();

        await engine.InvokeKernelAsync("match", 1500, 1500, 1, 0, "original-event");
        await engine.InvokeKernelAsync("match", 1500, 1500, 1, 2, "changed-event");
        await engine.InvokeKernelAsync("match", 1500, 1500, 1, 0, "corrected-event");

        Assert.Equal(3, messages.Select(message => message.idempotency_key).Distinct().Count());
    }

    [Fact]
    public async Task EventIdentityAlsoIncludesCurrentCalculationInputs()
    {
        var (engine, messages) = CreateEngine();

        await engine.InvokeKernelAsync("match", 1500, 1500, 1, 0, "same-event");
        await engine.InvokeKernelAsync("match", 1500, 1500, 1, 2, "same-event");

        Assert.NotEqual(messages[0].idempotency_key, messages[1].idempotency_key);
    }

    [Fact]
    public async Task ReplayAfterEngineRestartKeepsDeterministicClaim()
    {
        var (firstEngine, firstMessages) = CreateEngine();
        var (secondEngine, secondMessages) = CreateEngine();

        await firstEngine.InvokeKernelAsync("match", 1500, 1500, 1, 2, "same-event");
        await secondEngine.InvokeKernelAsync("match", 1500, 1500, 1, 2, "same-event");

        Assert.Equal(firstMessages[0].idempotency_key, secondMessages[0].idempotency_key);
    }

    private static (MarketStateEngine Engine, List<KernelInvokePayload> Messages) CreateEngine()
    {
        var messages = new List<KernelInvokePayload>();
        var subscriber = DispatchProxy.Create<ISubscriber, RedisStub>();
        ((RedisStub)(object)subscriber).Handler = (method, args) =>
        {
            Assert.Equal("PublishAsync", method.Name);
            Assert.Equal("system:invoke_kernel", args![0]!.ToString());
            messages.Add(JsonSerializer.Deserialize<KernelInvokePayload>(args[1]!.ToString()!)!);
            return Task.FromResult(1L);
        };
        var redis = DispatchProxy.Create<IConnectionMultiplexer, RedisStub>();
        ((RedisStub)(object)redis).Handler = (method, _) =>
        {
            Assert.Equal("GetSubscriber", method.Name);
            return subscriber;
        };
        var config = new ConfigurationBuilder().Build();
        var cache = new MarketOddsCache(NullLogger<MarketOddsCache>.Instance, config);
        var audit = new LatencyAuditService(redis, NullLogger<LatencyAuditService>.Instance, config);
        return (new MarketStateEngine(redis, cache, audit,
            NullLogger<MarketStateEngine>.Instance, config), messages);
    }

    public class RedisStub : DispatchProxy
    {
        public Func<MethodInfo, object?[]?, object?> Handler { get; set; } = null!;

        protected override object? Invoke(MethodInfo? targetMethod, object?[]? args)
            => Handler(targetMethod!, args);
    }
}
