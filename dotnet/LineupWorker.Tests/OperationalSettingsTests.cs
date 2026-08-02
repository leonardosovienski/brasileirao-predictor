using LineupWorker;
using Xunit;

[assembly: CollectionBehavior(DisableTestParallelization = true)]

namespace LineupWorker.Tests;

public sealed class OperationalSettingsTests
{
    private static readonly string[] Names =
    [
        "REDIS_URL", "SPORTS_DB_PATH", "MARKET_DB_PATH",
        "VORP_ARTIFACT_PATH", "TITULARIDADE_PATH"
    ];

    private sealed class EnvironmentScope : IDisposable
    {
        private readonly Dictionary<string, string?> _original =
            Names.ToDictionary(name => name, Environment.GetEnvironmentVariable);

        public EnvironmentScope()
        {
            var root = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "brasileirao-tests"));
            Environment.SetEnvironmentVariable("REDIS_URL", "redis://redis.example:6380/2");
            Environment.SetEnvironmentVariable("SPORTS_DB_PATH", Path.Combine(root, "sports.db"));
            Environment.SetEnvironmentVariable("MARKET_DB_PATH", Path.Combine(root, "market.db"));
            Environment.SetEnvironmentVariable("VORP_ARTIFACT_PATH", Path.Combine(root, "vorp.json"));
            Environment.SetEnvironmentVariable("TITULARIDADE_PATH", Path.Combine(root, "titularidade.json"));
        }

        public void Dispose()
        {
            foreach (var pair in _original)
                Environment.SetEnvironmentVariable(pair.Key, pair.Value);
        }
    }

    [Fact]
    public void LoadsAbsoluteIsolatedPathsAndRedisUri()
    {
        using var scope = new EnvironmentScope();
        var settings = OperationalSettings.FromEnvironment();
        var redis = settings.RedisConfiguration();

        Assert.True(Path.IsPathFullyQualified(settings.SportsDatabasePath));
        Assert.NotEqual(settings.SportsDatabasePath, settings.MarketDatabasePath);
        Assert.Equal(2, redis.DefaultDatabase);
        Assert.Contains(redis.EndPoints, endpoint => endpoint.ToString()!.Contains("redis.example:6380"));
    }

    [Fact]
    public void RejectsMissingRedisUrl()
    {
        using var scope = new EnvironmentScope();
        Environment.SetEnvironmentVariable("REDIS_URL", null);
        Assert.Throws<InvalidOperationException>(OperationalSettings.FromEnvironment);
    }

    [Fact]
    public void RejectsRelativePath()
    {
        using var scope = new EnvironmentScope();
        Environment.SetEnvironmentVariable("SPORTS_DB_PATH", "relative.db");
        Assert.Throws<InvalidOperationException>(OperationalSettings.FromEnvironment);
    }

    [Fact]
    public void RejectsSharedSportsAndMarketDatabase()
    {
        using var scope = new EnvironmentScope();
        var sports = Environment.GetEnvironmentVariable("SPORTS_DB_PATH");
        Environment.SetEnvironmentVariable("MARKET_DB_PATH", sports);
        Assert.Throws<InvalidOperationException>(OperationalSettings.FromEnvironment);
    }

    [Fact]
    public void RejectsInvalidRedisScheme()
    {
        using var scope = new EnvironmentScope();
        var settings = OperationalSettings.FromEnvironment();
        var invalid = settings with { RedisUrl = "http://redis.example" };
        Assert.Throws<InvalidOperationException>(invalid.RedisConfiguration);
    }
}
