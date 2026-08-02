using StackExchange.Redis;

namespace LineupWorker;

public sealed record OperationalSettings(
    string RedisUrl,
    string VorpArtifactPath,
    string TitularidadePath,
    string SportsDatabasePath,
    string MarketDatabasePath)
{
    public static OperationalSettings FromEnvironment()
    {
        string Required(string name) => Environment.GetEnvironmentVariable(name)
            ?? throw new InvalidOperationException($"Required environment variable {name} is missing");

        string Absolute(string name)
        {
            var value = Required(name);
            if (!Path.IsPathFullyQualified(value))
                throw new InvalidOperationException($"{name} must be an absolute path");
            return Path.GetFullPath(value);
        }

        var sports = Absolute("SPORTS_DB_PATH");
        var market = Absolute("MARKET_DB_PATH");
        if (StringComparer.OrdinalIgnoreCase.Equals(sports, market))
            throw new InvalidOperationException("SPORTS_DB_PATH and MARKET_DB_PATH must be isolated");

        return new(Required("REDIS_URL"), Absolute("VORP_ARTIFACT_PATH"),
            Absolute("TITULARIDADE_PATH"), sports, market);
    }

    public ConfigurationOptions RedisConfiguration()
    {
        if (!Uri.TryCreate(RedisUrl, UriKind.Absolute, out var uri) ||
            (uri.Scheme != "redis" && uri.Scheme != "rediss"))
            throw new InvalidOperationException("REDIS_URL must use redis:// or rediss://");

        var options = new ConfigurationOptions
        {
            AbortOnConnectFail = false,
            ConnectTimeout = 3000,
            SyncTimeout = 1000,
            Ssl = uri.Scheme == "rediss",
            DefaultDatabase = uri.AbsolutePath is { Length: > 1 } && int.TryParse(uri.AbsolutePath[1..], out var db) ? db : 0,
            ReconnectRetryPolicy = new ExponentialRetry(5000),
        };
        options.EndPoints.Add(uri.Host, uri.IsDefaultPort ? 6379 : uri.Port);
        if (!string.IsNullOrEmpty(uri.UserInfo))
        {
            var parts = uri.UserInfo.Split(':', 2);
            if (parts.Length == 2) options.Password = Uri.UnescapeDataString(parts[1]);
        }
        return options;
    }
}
