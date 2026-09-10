using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using LineupWorker.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace LineupWorker.Tests;

public sealed class MarketFeedContractTests
{
    private static MarketOddsCache Cache() => new(NullLogger<MarketOddsCache>.Instance, new ConfigurationBuilder().Build());
    private static void Apply(MarketOddsCache cache, string json) =>
        typeof(MarketOddsCache).GetMethod("ParseAndUpdate", BindingFlags.Instance | BindingFlags.NonPublic)!
            .Invoke(cache, [new ReadOnlyMemory<byte>(Encoding.UTF8.GetBytes(json))]);
    private static string Snapshot(long revision, string status = "ACTIVE", double home = 2.2, int age = 1) =>
        JsonSerializer.Serialize(new { schema_version = "normalized-market/v1", match_id = "m", source = "synthetic-provider",
            bookmaker = "synthetic-book", period = "FT", line = 2.5, revision, status, home, draw = 3.2, away = 3.5,
            observed_at = DateTimeOffset.UtcNow.AddSeconds(-age), available_at = DateTimeOffset.UtcNow.AddMilliseconds(-10),
            kickoff_at = DateTimeOffset.UtcNow.AddHours(1) });

    [Fact]
    public void LegacyPayloadCannotBecomeFreshCommercialQuote()
    {
        var cache = Cache();
        Apply(cache, """{"match_id":"m","home":2.2,"draw":3.2,"away":3.5,"source":"synthetic"}""");
        Assert.Null(cache.TryGet("m"));
    }

    [Fact]
    public void SuspensionCannotBeResurrectedByDelayedRevision()
    {
        var cache = Cache();
        Apply(cache, Snapshot(1));
        Assert.NotNull(cache.TryGet("m"));
        Apply(cache, Snapshot(2, "SUSPENDED"));
        Apply(cache, Snapshot(1));
        Assert.Null(cache.TryGet("m"));
    }

    [Fact]
    public void OldObservationCannotBecomeFreshByReceiptAlone()
    {
        var cache = Cache();
        Apply(cache, Snapshot(1, age: 120));
        Assert.Null(cache.TryGet("m"));
    }

    [Fact]
    public void ConflictingRevisionAbstainsInsteadOfPickingLastArrival()
    {
        var cache = Cache();
        Apply(cache, Snapshot(1));
        Apply(cache, Snapshot(1, home: 9));
        Assert.Null(cache.TryGet("m"));
    }

    [Fact]
    public void DuplicateJsonKeysDoNotOverrideQuotedPrice()
    {
        var cache = Cache();
        Apply(cache, Snapshot(1).Replace("\"home\":2.2", "\"home\":2.2,\"home\":9"));
        Assert.Null(cache.TryGet("m"));
    }

    [Theory]
    [InlineData("schema_version", "\"unknown/v1\"")]
    [InlineData("period", "\"HT\"")]
    [InlineData("status", "\"UNKNOWN\"")]
    [InlineData("bookmaker", "\"\"")]
    [InlineData("home", "null")]
    [InlineData("draw", "1")]
    [InlineData("away", "\"3.5\"")]
    [InlineData("revision", "-1")]
    [InlineData("revision", "0.5")]
    [InlineData("observed_at", "\"not-a-dateZ\"")]
    [InlineData("available_at", "\"2024-01-01T00:00:00\"")]
    [InlineData("available_at", "\"2999-01-01T00:00:00Z\"")]
    [InlineData("kickoff_at", "\"2024-01-01T00:00:00Z\"")]
    public void InvalidKnownMarketWithdrawsItsPreviousPrice(string field, string value)
    {
        var cache = Cache();
        Apply(cache, Snapshot(1));
        Assert.NotNull(cache.TryGet("m"));
        var invalid = JsonNode.Parse(Snapshot(2))!;
        invalid[field] = JsonNode.Parse(value);
        Apply(cache, invalid.ToJsonString());
        Assert.Null(cache.TryGet("m"));
    }

    [Fact]
    public void RetryPreservesReceiptAndNewRevisionCanResolveSuspension()
    {
        var cache = Cache();
        var initial = Snapshot(1);
        Apply(cache, initial);
        var receipt = cache.TryGet("m")!.ReceivedAt;
        Apply(cache, initial);
        Assert.Equal(receipt, cache.TryGet("m")!.ReceivedAt);
        Apply(cache, Snapshot(2, "SUSPENDED"));
        Assert.Null(cache.TryGet("m"));
        Apply(cache, Snapshot(3));
        Assert.Equal(3, cache.TryGet("m")!.Revision);
    }

    [Fact]
    public void HigherRevisionWithOlderObservationDoesNotResurrectMarket()
    {
        var cache = Cache();
        Apply(cache, Snapshot(1));
        Apply(cache, Snapshot(2, age: 20));
        Assert.Null(cache.TryGet("m"));
    }

    [Theory]
    [InlineData("source")]
    [InlineData("bookmaker")]
    public void DifferentIdentityCannotOverwriteTheSameMarket(string field)
    {
        var cache = Cache();
        Apply(cache, Snapshot(1));
        var conflicting = JsonNode.Parse(Snapshot(2))!;
        conflicting[field] = "another-identity";
        Apply(cache, conflicting.ToJsonString());
        Assert.Null(cache.TryGet("m"));
    }

    [Fact]
    public void SuspendedStateDoesNotRequireActivePrices()
    {
        var cache = Cache();
        var suspended = JsonNode.Parse(Snapshot(2, "SUSPENDED"))!.AsObject();
        foreach (var field in new[] { "home", "draw", "away" }) suspended.Remove(field);
        Apply(cache, suspended.ToJsonString());
        Apply(cache, Snapshot(1));
        Assert.Null(cache.TryGet("m"));
    }

    [Fact]
    public void TotalsRequireTheirImplementedLine()
    {
        var cache = Cache();
        var quote = JsonNode.Parse(Snapshot(1))!;
        quote["over25"] = 1.9;
        quote["under25"] = 1.9;
        Apply(cache, quote.ToJsonString());
        Assert.Equal(1.9, cache.TryGet("m")!.OddsOver25);
        quote["revision"] = 2;
        quote["line"] = 3.5;
        Apply(cache, quote.ToJsonString());
        Assert.Null(cache.TryGet("m"));
    }

    [Fact]
    public void UnidentifiedAndOversizedMessagesNeverCreateAMarket()
    {
        var cache = Cache();
        foreach (var payload in new[] { "[]", "{", "{}", new string(' ', 256 * 1024 + 1) }) Apply(cache, payload);
        Assert.Null(cache.TryGet("m"));
    }
}
