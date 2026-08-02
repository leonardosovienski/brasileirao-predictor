using System.Text.Json;
using LineupWorker.Models;
using Xunit;

namespace LineupWorker.Tests;

public sealed class RedisProtocolTests
{
    private const string Valid = """
        {"protocol_version":"brasileirao.redis/1","job_id":"j","run_id":"r","match_id":"m","1":2.0,"X":3.0,"2":4.0,"o25":1.9,"u25":2.1}
        """;

    [Fact]
    public void ParsesVersionedFairOdds()
    {
        using var document = JsonDocument.Parse(Valid);
        var payload = FairOddsPayload.FromDict(document.RootElement);
        Assert.Equal(2.0, payload.Home);
        Assert.Equal(2.1, payload.Under25);
    }

    [Theory]
    [InlineData("{\"protocol_version\":\"brasileirao.redis/999\",\"job_id\":\"j\",\"run_id\":\"r\",\"match_id\":\"m\"}")]
    [InlineData("{\"job_id\":\"j\",\"run_id\":\"r\",\"match_id\":\"m\"}")]
    [InlineData("{\"protocol_version\":\"brasileirao.redis/1\",\"job_id\":\"j\",\"match_id\":\"m\"}")]
    public void RejectsUnknownVersionOrMissingRequiredField(string json)
    {
        using var document = JsonDocument.Parse(json);
        Assert.Throws<JsonException>(() => FairOddsPayload.FromDict(document.RootElement));
    }

    [Fact]
    public void InvocationSerializesSharedFieldNames()
    {
        var payload = new KernelInvokePayload(
            RedisProtocol.Version, "job", "run", "idem", "match", 1600, 1500, 0, 0, 1);
        var json = JsonSerializer.Serialize(payload);
        Assert.Contains("\"protocol_version\":\"brasileirao.redis/1\"", json);
        Assert.Contains("\"idempotency_key\":\"idem\"", json);
    }
}
