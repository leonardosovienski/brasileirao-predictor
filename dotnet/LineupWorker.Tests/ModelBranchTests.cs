using System.Text.Json;
using LineupWorker.Models;
using Xunit;

namespace LineupWorker.Tests;

public sealed class ModelBranchTests
{
    [Fact]
    public void FairOddsAllowsMissingOptionalPrices()
    {
        using var document = JsonDocument.Parse(
            """{"protocol_version":"brasileirao.redis/1","job_id":"j","run_id":"r","match_id":"m"}""");
        var fair = FairOddsPayload.FromDict(document.RootElement);
        Assert.Null(fair.Home);
        Assert.Null(fair.Draw);
        Assert.Null(fair.Away);
        Assert.Null(fair.Over25);
        Assert.Null(fair.Under25);
    }

    [Theory]
    [InlineData("job_id")]
    [InlineData("run_id")]
    [InlineData("match_id")]
    public void FairOddsRejectsBlankRequiredIdentifiers(string field)
    {
        var values = new Dictionary<string, object?>
        {
            ["protocol_version"] = RedisProtocol.Version,
            ["job_id"] = "j",
            ["run_id"] = "r",
            ["match_id"] = "m",
        };
        values[field] = " ";
        using var document = JsonDocument.Parse(JsonSerializer.Serialize(values));
        Assert.Throws<JsonException>(() => FairOddsPayload.FromDict(document.RootElement));
    }

    [Fact]
    public void MarketOddsComputesOverroundAndFreshnessAcrossZeroPrices()
    {
        var fresh = new MarketOdds("m", 2, 0, 4, null, null, DateTimeOffset.UtcNow, "fixture");
        var complementary = fresh with { OddsHome = 0, OddsDraw = 2, OddsAway = 0 };
        var stale = fresh with { LastUpdated = DateTimeOffset.UtcNow.AddMinutes(-2) };
        Assert.Equal(0.75, fresh.Overround);
        Assert.Equal(0.5, complementary.Overround);
        Assert.True(fresh.IsFresh(TimeSpan.FromSeconds(30)));
        Assert.False(stale.IsFresh(TimeSpan.FromSeconds(30)));
    }

    [Fact]
    public void LatencyRecordExposesAllDeltasWithAndWithoutMarketRead()
    {
        var t0 = DateTimeOffset.UtcNow;
        var record = new LatencyRecord("m", "home", t0, t0.AddMilliseconds(2), t0.AddMilliseconds(5),
            t0.AddMilliseconds(9), t0.AddMilliseconds(12), 0, false, null);
        Assert.Equal(2, record.NetworkLagMs);
        Assert.Equal(3, record.ProcessingMs);
        Assert.Equal(4, record.WriteMs);
        Assert.Equal(9, record.E2EMs);
        Assert.Equal(3, record.MarketReactionMs);
        Assert.True(record.IsWithinBudget(9));
        Assert.False(record.IsWithinBudget(8));
        Assert.Null((record with { T4_MarketEngineRead = null }).MarketReactionMs);
    }

    [Fact]
    public void RedisConfigurationSupportsPasswordDefaultPortAndDefaultDatabase()
    {
        var root = Path.GetFullPath(Path.GetTempPath());
        var settings = new LineupWorker.OperationalSettings(
            "rediss://user:p%40ss@redis.example/",
            Path.Combine(root, "vorp.json"),
            Path.Combine(root, "tit.json"),
            Path.Combine(root, "sports.db"),
            Path.Combine(root, "market.db"));
        var options = settings.RedisConfiguration();
        Assert.True(options.Ssl);
        Assert.Equal(0, options.DefaultDatabase);
        Assert.Equal("p@ss", options.Password);
        Assert.Contains(options.EndPoints, endpoint => endpoint.ToString()!.Contains("6379"));
    }
}
