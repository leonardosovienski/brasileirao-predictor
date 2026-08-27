using LineupWorker.Services;
using Xunit;

namespace LineupWorker.Tests;

public sealed class KellyMathTests
{
    [Fact]
    public void FractionalKellyUsesProbabilityTimesOddsNumerator()
    {
        // p=.5, O=2.5 => full Kelly=(1.25-1)/1.5=1/6; at 10% => 1/60.
        Assert.Equal(1.0 / 60.0, MarketStateEngine.FractionalKelly(0.5, 2.5, 0.1), 10);
    }
}
