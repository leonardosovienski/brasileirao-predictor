using Xunit;

namespace LineupWorker.Tests;

public sealed class RedisEndpointTests
{
    private static OperationalSettings Settings(string uri) => new(uri, "vorp", "tit", "sports", "market");

    [Fact]
    public void RedisAclUsernamePasswordDatabaseAndTlsArePreserved()
    {
        var cfg = Settings("rediss://worker%2Dread:SYNTHETIC%3Asecret@localhost:26380/14").RedisConfiguration();
        Assert.Equal("worker-read", cfg.User);
        Assert.Equal("SYNTHETIC:secret", cfg.Password);
        Assert.Equal(14, cfg.DefaultDatabase);
        Assert.True(cfg.Ssl);
        Assert.Equal(0, Settings("redis://localhost:26380").RedisConfiguration().DefaultDatabase);
    }

    [Theory]
    [InlineData("redis://localhost:26380/not-a-db")]
    [InlineData("redis://localhost:26380/-1")]
    [InlineData("redis://localhost:26380/2147483648")]
    [InlineData("redis://localhost:26380/1/2")]
    [InlineData("redis://localhost:26380/1?db=0")]
    [InlineData("redis://localhost:26380/1#other")]
    public void InvalidDatabaseDoesNotSilentlySelectZero(string uri)
    {
        var error = Assert.Throws<InvalidOperationException>(() => Settings(uri).RedisConfiguration());
        Assert.DoesNotContain(uri, error.Message);
    }
}
