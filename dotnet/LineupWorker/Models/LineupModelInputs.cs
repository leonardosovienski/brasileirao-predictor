using System.Globalization;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace LineupWorker.Models;

/// <summary>Declared model context; clock checks and hashes do not authenticate its producer.</summary>
public sealed record LineupModelInputs(
    string Version, string MatchId, string HomeTeam, string AwayTeam,
    double EloHome, double EloAway, string VorpArtifactSha256,
    string LearnedThrough, string FittedAt, string AvailableAt, string KickoffAt,
    IReadOnlyDictionary<string, string> Positions)
{
    private static DateTimeOffset Clock(string text)
    {
        if (text is null || !Regex.IsMatch(text, @"(?:Z|[+-]\d{2}:\d{2})$") ||
            !DateTimeOffset.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.None, out var stamp))
            throw new ArgumentException("Model context requires explicit aware clocks");
        return stamp.ToUniversalTime();
    }

    public string Validate(LineupEvent ev, DateTimeOffset decision, string loadedVorpHash)
    {
        if (string.IsNullOrWhiteSpace(Version) || MatchId != ev.MatchId || HomeTeam != ev.HomeTeam || AwayTeam != ev.AwayTeam ||
            !double.IsFinite(EloHome) || !double.IsFinite(EloAway) || EloHome <= 0 || EloAway <= 0 ||
            string.IsNullOrWhiteSpace(loadedVorpHash) || VorpArtifactSha256 != loadedVorpHash)
            throw new ArgumentException("Model context identity, Elo or VORP artifact mismatch");
        var learned = Clock(LearnedThrough);
        var fitted = Clock(FittedAt);
        var available = Clock(AvailableAt);
        var kickoff = Clock(KickoffAt);
        if (learned > fitted || fitted > available || available > decision || decision >= kickoff || ev.CapturedAt >= kickoff)
            throw new ArgumentException("Model context was not available before decision and kickoff");
        if (Positions is null || ev.Starters.Any(player => !Positions.TryGetValue(player, out var position) ||
            position is not ("GK" or "DF" or "MF" or "FW")))
            throw new ArgumentException("Every starter requires a declared GK/DF/MF/FW position");
        var normalized = this with { Positions = new SortedDictionary<string, string>(Positions.ToDictionary(p => p.Key, p => p.Value), StringComparer.Ordinal) };
        return Convert.ToHexString(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(normalized)));
    }
}
