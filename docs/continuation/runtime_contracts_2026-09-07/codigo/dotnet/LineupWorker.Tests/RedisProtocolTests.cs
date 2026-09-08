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
    [InlineData("1")]
    [InlineData("X")]
    [InlineData("2")]
    [InlineData("o25")]
    [InlineData("u25")]
    public void PreservesUnavailableSelectionAndOtherFairOdds(string unavailableKey)
    {
        var fields = JsonSerializer.Deserialize<Dictionary<string, object?>>(Valid)!;
        fields[unavailableKey] = null;
        using var document = JsonDocument.Parse(JsonSerializer.Serialize(fields));

        var payload = FairOddsPayload.FromDict(document.RootElement);

        Assert.Equal(unavailableKey == "1" ? (double?)null : 2.0, payload.Home);
        Assert.Equal(unavailableKey == "X" ? (double?)null : 3.0, payload.Draw);
        Assert.Equal(unavailableKey == "2" ? (double?)null : 4.0, payload.Away);
        Assert.Equal(unavailableKey == "o25" ? (double?)null : 1.9, payload.Over25);
        Assert.Equal(unavailableKey == "u25" ? (double?)null : 2.1, payload.Under25);
    }

    [Theory]
    [InlineData("")]
    [InlineData(",\"1\":null,\"X\":null,\"2\":null,\"o25\":null,\"u25\":null")]
    public void PreservesAllUnavailableOrMissingFairOdds(string oddsFields)
    {
        using var document = JsonDocument.Parse(
            "{\"protocol_version\":\"brasileirao.redis/1\",\"job_id\":\"j\",\"run_id\":\"r\",\"match_id\":\"m\""
            + oddsFields + "}");

        var payload = FairOddsPayload.FromDict(document.RootElement);

        Assert.Equal(new FairOddsPayload(null, null, null, null, null), payload);
    }

    [Theory]
    [InlineData("\"2.0\"")]
    [InlineData("\"null\"")]
    [InlineData("true")]
    [InlineData("{}")]
    [InlineData("[]")]
    public void DoesNotCoerceMalformedOddsIntoAvailableOrMissingPrices(string invalidOdd)
    {
        using var document = JsonDocument.Parse(Valid.Replace("\"1\":2.0", "\"1\":" + invalidOdd));

        Assert.Throws<InvalidOperationException>(() => FairOddsPayload.FromDict(document.RootElement));
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
