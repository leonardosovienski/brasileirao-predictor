using System.Text.Json;
using LineupWorker.Models;
using LineupWorker.Services;
using Xunit;

namespace LineupWorker.Tests;

public sealed class CompletionContractTests
{
    [Fact]
    public void NegativeEdgeCannotBecomeANegativeStake()
        => Assert.Equal(0, MarketStateEngine.FractionalKelly(.2, 2, .25));

    [Theory]
    [InlineData(double.NaN, 2, .25)]
    [InlineData(.5, double.PositiveInfinity, .25)]
    [InlineData(.5, 1, .25)]
    [InlineData(1.1, 2, .25)]
    [InlineData(.5, 2, -.25)]
    public void KellyRejectsInvalidInputs(double p, double odd, double fraction)
        => Assert.Throws<ArgumentOutOfRangeException>(() => MarketStateEngine.FractionalKelly(p, odd, fraction));

    [Fact]
    public void FutureReceiptIsNotFresh()
    {
        var odds = new MarketOdds("x", 2, 3, 4, null, null, DateTimeOffset.UtcNow.AddHours(1), "synthetic");
        Assert.False(odds.IsFresh(TimeSpan.FromSeconds(30)));
    }

    [Theory]
    [InlineData("-2")]
    [InlineData("1e400")]
    public void FairOddsMustRepresentValidProbabilities(string odd)
    {
        using var json = JsonDocument.Parse("{\"protocol_version\":\"brasileirao.redis/2\",\"job_id\":\"j\",\"run_id\":\"r\",\"match_id\":\"m\",\"state_version\":\"1\",\"idempotency_key\":\"k\",\"1\":" + odd + "}");
        Assert.Throws<JsonException>(() => FairOddsPayload.FromDict(json.RootElement));
    }
}
