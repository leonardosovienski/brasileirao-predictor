using LineupWorker.Models;
using System.Security.Cryptography;
using System.Text.Json;
using Xunit;

namespace LineupWorker.Tests;

public sealed partial class WorkerRuntimeTests
{
    [RedisRuntimeFact]
    public async Task RealModeCannotInventEqualEloAndUnknownPositions()
    {
        var worker = await Worker(allowSyntheticInputs: false);
        var ev = new LineupEvent("real-input-contract", "home", "away", "home", LineupFixtures.Starters("p1"), [], DateTimeOffset.UtcNow);
        await Assert.ThrowsAsync<ArgumentException>(() => Handle(worker, ev));
        Assert.False(await _redis.GetDatabase().KeyExistsAsync("lineup_state:" + ev.MatchId));
    }

    private LineupEvent DeclaredEvent()
    {
        var now = DateTimeOffset.UtcNow;
        var starters = LineupFixtures.Starters("p1");
        var ev = new LineupEvent("declared-input-contract", "home", "away", "home", starters, [], now);
        var hash = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(Path.Combine(_root, "fencing-vorp.json"))));
        return ev with { ModelInputs = new LineupModelInputs("synthetic-context/1", ev.MatchId, ev.HomeTeam, ev.AwayTeam,
            1630, 1480, hash, now.AddDays(-2).ToString("O"), now.AddDays(-1).ToString("O"),
            now.AddHours(-1).ToString("O"), now.AddHours(2).ToString("O"), starters.ToDictionary(p => p, _ => "GK")) };
    }

    [RedisRuntimeFact]
    public async Task WorkerRegistersDeclaredUnequalEloAndCoveredPositions()
    {
        var worker = await Worker(allowSyntheticInputs: false);
        var ev = DeclaredEvent();
        await Handle(worker, ev);
        var raw = await _redis.GetDatabase().StringGetAsync("kernel:v2:current:" + ev.MatchId);
        var request = JsonSerializer.Deserialize<KernelInvokePayload>(raw.ToString())!;
        Assert.Equal(1630, request.elo_a);
        Assert.Equal(1480, request.elo_b);
        Assert.Equal(1, request.dvorp_a);
    }

    [RedisRuntimeFact]
    public async Task ChangedModelContextCannotMixTheTwoLineupSides()
    {
        var worker = await Worker(allowSyntheticInputs: false);
        var ev = DeclaredEvent();
        await Handle(worker, ev);
        var changed = ev with { Side = "away", ModelInputs = ev.ModelInputs! with { Version = "synthetic-context/2" } };
        await Assert.ThrowsAsync<ArgumentException>(() => Handle(worker, changed));
        var raw = await _redis.GetDatabase().StringGetAsync("lineup_state:" + ev.MatchId);
        Assert.False(JsonSerializer.Deserialize<LineupState>(raw.ToString())!.AwayLineupComplete);
    }

    [RedisRuntimeFact]
    public async Task FutureOrMismatchedContextCannotWriteAState()
    {
        var worker = await Worker(allowSyntheticInputs: false);
        var ev = DeclaredEvent();
        foreach (var inputs in new[] {
            ev.ModelInputs! with { AvailableAt = DateTimeOffset.UtcNow.AddDays(1).ToString("O") },
            ev.ModelInputs! with { VorpArtifactSha256 = new string('0', 64) },
            ev.ModelInputs! with { HomeTeam = "wrong" },
            ev.ModelInputs! with { Positions = new Dictionary<string, string>() },
            ev.ModelInputs! with { FittedAt = "2024-01-01T00:00:00" },
        })
            await Assert.ThrowsAsync<ArgumentException>(() => Handle(worker, ev with { ModelInputs = inputs }));
        Assert.False(await _redis.GetDatabase().KeyExistsAsync("lineup_state:" + ev.MatchId));
    }
}
