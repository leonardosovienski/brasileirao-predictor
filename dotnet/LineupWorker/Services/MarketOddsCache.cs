using System.Collections.Concurrent;
using System.Globalization;
using System.Net.WebSockets;
using System.Security.Cryptography;
using System.Text.Json;
using LineupWorker.Models;

namespace LineupWorker.Services;

/// <summary>
/// Cache of declared normalized quotes. Receipt is not proof of acceptance.
/// Live transport requires an explicitly configured normalized-market/v1 bridge;
/// this service does not pretend to implement a bookmaker's private protocol.
/// </summary>
public sealed class MarketOddsCache : BackgroundService
{
    private const int MaximumMessageBytes = 256 * 1024;
    private static readonly TimeSpan MaximumAge = TimeSpan.FromSeconds(30);
    private readonly ConcurrentDictionary<string, MarketOdds> _cache = new();
    private readonly object _updateLock = new();
    private readonly ILogger<MarketOddsCache> _log;
    private readonly string? _wsUrl;
    private readonly string _apiKey;
    private readonly string? _protocol;
    private readonly string? _source;
    private readonly string? _bookmaker;
    private readonly bool _syntheticPayloads;

    public MarketOddsCache(ILogger<MarketOddsCache> log, IConfiguration cfg)
    {
        _log = log;
        _wsUrl = cfg["Exchange:WebSocketUrl"];
        _apiKey = cfg["Exchange:ApiKey"] ?? "";
        _protocol = cfg["Exchange:Protocol"];
        _source = cfg["Exchange:Source"];
        _bookmaker = cfg["Exchange:Bookmaker"];
        _syntheticPayloads = cfg.GetValue<bool>("Exchange:AllowSyntheticPayloads", false);
    }

    public MarketOdds? TryGet(string matchId) =>
        _cache.TryGetValue(matchId, out var odds) && odds.IsFresh(MaximumAge) ? odds : null;

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(_wsUrl))
        {
            _log.LogInformation("[MarketOdds] disabled: no normalized market feed configured");
            return;
        }
        if (_protocol != "normalized-market/v1" || string.IsNullOrWhiteSpace(_source) ||
            string.IsNullOrWhiteSpace(_bookmaker) || !Uri.TryCreate(_wsUrl, UriKind.Absolute, out var uri) ||
            uri.Scheme != "wss" || uri.UserInfo != "" || uri.Query != "" || uri.Fragment != "" ||
            uri.Host.EndsWith(".invalid", StringComparison.OrdinalIgnoreCase) ||
            uri.Host.EndsWith("example.com", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Explicit WSS bridge, protocol, source and bookmaker required");
        int attempt = 0;
        while (!ct.IsCancellationRequested)
        {
            try
            {
                await ConnectAndListenAsync(ct);
                attempt = 0;
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested) { break; }
            catch (Exception ex) when (ex is WebSocketException or JsonException or IOException)
            {
                _log.LogWarning("[MarketOdds] feed unavailable ({Error})", ex.GetType().Name);
            }
            finally
            {
                // Retain revision fences across reconnection; a duplicate old
                // active quote cannot erase the knowledge of disconnection.
                lock (_updateLock)
                    foreach (var pair in _cache)
                        _cache[pair.Key] = pair.Value with { Status = "UNAVAILABLE" };
            }
            try { await Task.Delay(TimeSpan.FromSeconds(Math.Min(30, Math.Pow(2, Math.Min(attempt++, 5)))), ct); }
            catch (OperationCanceledException) when (ct.IsCancellationRequested) { break; }
        }
    }

    private async Task ConnectAndListenAsync(CancellationToken ct)
    {
        using var ws = new ClientWebSocket();
        if (_apiKey.Length > 0) ws.Options.SetRequestHeader("X-Api-Key", _apiKey);
        await ws.ConnectAsync(new Uri(_wsUrl!), ct);
        var subscription = JsonSerializer.SerializeToUtf8Bytes(new { action = "subscribe", protocol = "normalized-market/v1", source = _source, bookmaker = _bookmaker });
        await ws.SendAsync(subscription, WebSocketMessageType.Text, true, ct);
        var buffer = new byte[8 * 1024];
        using var message = new MemoryStream();
        while (!ct.IsCancellationRequested && ws.State == WebSocketState.Open)
        {
            message.SetLength(0);
            WebSocketReceiveResult result;
            do
            {
                result = await ws.ReceiveAsync(buffer, ct);
                if (result.MessageType == WebSocketMessageType.Close) return;
                if (result.MessageType != WebSocketMessageType.Text || message.Length + result.Count > MaximumMessageBytes)
                    throw new JsonException("Unsupported or oversized market message");
                message.Write(buffer, 0, result.Count);
            } while (!result.EndOfMessage);
            ParseAndUpdate(message.ToArray());
        }
    }

    private static string Text(JsonElement root, string name)
    {
        var value = root.GetProperty(name);
        if (value.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(value.GetString()))
            throw new JsonException("Missing market identity");
        return value.GetString()!;
    }

    private static DateTimeOffset Clock(JsonElement root, string name)
    {
        var value = Text(root, name);
        if (!System.Text.RegularExpressions.Regex.IsMatch(value, @"(?:Z|[+-]\d{2}:\d{2})$") ||
            !DateTimeOffset.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.None, out var parsed))
            throw new JsonException("Aware market clock required");
        return parsed.ToUniversalTime();
    }

    private static double? Price(JsonElement root, string name, bool required)
    {
        if (!root.TryGetProperty(name, out var element) || element.ValueKind == JsonValueKind.Null)
        {
            if (required) throw new JsonException("Missing active price");
            return null;
        }
        if (element.ValueKind != JsonValueKind.Number || !element.TryGetDouble(out var value) || !double.IsFinite(value) || value <= 1)
            throw new JsonException("Invalid decimal price");
        return value;
    }

    private void ParseAndUpdate(ReadOnlyMemory<byte> data)
    {
        string? identifiedMatch = null;
        try
        {
            if (data.Length > MaximumMessageBytes) throw new JsonException("Oversized market message");
            using var doc = JsonDocument.Parse(data, new JsonDocumentOptions { MaxDepth = 16 });
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object || root.EnumerateObject().GroupBy(p => p.Name).Any(g => g.Count() > 1))
                throw new JsonException("Invalid or duplicate market fields");
            var match = Text(root, "match_id");
            identifiedMatch = match;
            var source = Text(root, "source");
            var received = DateTimeOffset.UtcNow;
            if (!root.TryGetProperty("schema_version", out _))
            {
                if (!_syntheticPayloads) return;
                var synthetic = new MarketOdds(match, Price(root, "home", true)!.Value, Price(root, "draw", true)!.Value,
                    Price(root, "away", true)!.Value, Price(root, "over25", false), Price(root, "under25", false), received, source)
                    { Synthetic = true, Bookmaker = "SYNTHETIC", ReceivedAt = received };
                lock (_updateLock) _cache[match] = synthetic;
                return;
            }
            if (Text(root, "schema_version") != "normalized-market/v1" || Text(root, "period") != "FT")
                throw new JsonException("Unsupported market contract");
            var bookmaker = Text(root, "bookmaker");
            if ((_source is not null && source != _source) || (_bookmaker is not null && bookmaker != _bookmaker))
                throw new JsonException("Market source mismatch");
            var status = Text(root, "status");
            if (status is not ("ACTIVE" or "SUSPENDED" or "CLOSED")) throw new JsonException("Unsupported market status");
            var observed = Clock(root, "observed_at");
            var available = Clock(root, "available_at");
            var kickoff = Clock(root, "kickoff_at");
            if (observed > available || available > received || kickoff <= received)
                throw new JsonException("Invalid market chronology");
            if (!root.GetProperty("revision").TryGetInt64(out var revision) || revision < 0)
                throw new JsonException("Nonnegative source revision required");
            var over = Price(root, "over25", false);
            var under = Price(root, "under25", false);
            if ((over.HasValue || under.HasValue) && (!root.TryGetProperty("line", out var line) || !line.TryGetDouble(out var total) || total != 2.5))
                throw new JsonException("Only total line 2.5 is implemented");
            var odds = new MarketOdds(match, Price(root, "home", status == "ACTIVE") ?? 0,
                Price(root, "draw", status == "ACTIVE") ?? 0, Price(root, "away", status == "ACTIVE") ?? 0,
                over, under, observed, source)
                { Bookmaker = bookmaker, Status = status, Revision = revision, ReceivedAt = received, AvailableAt = available,
                  KickoffAt = kickoff, SnapshotIdentity = Convert.ToHexString(SHA256.HashData(data.Span)) };
            lock (_updateLock)
            {
                if (_cache.TryGetValue(match, out var previous))
                {
                    if (previous.Source != source || previous.Bookmaker != bookmaker)
                    { _cache[match] = previous with { Status = "CONFLICT" }; return; }
                    if (revision < previous.Revision) return;
                    if (revision == previous.Revision)
                    {
                        if (odds.SnapshotIdentity != previous.SnapshotIdentity)
                            _cache[match] = previous with { Status = "CONFLICT" };
                        return;
                    }
                    if (observed < previous.LastUpdated)
                    { _cache[match] = odds with { Status = "CONFLICT" }; return; }
                }
                else if (_cache.Count >= 10_000) throw new JsonException("Market cache capacity reached");
                _cache[match] = odds;
            }
        }
        catch (Exception ex) when (ex is JsonException or InvalidOperationException or KeyNotFoundException or FormatException)
        {
            if (identifiedMatch is not null)
                lock (_updateLock)
                    if (_cache.TryGetValue(identifiedMatch, out var previous))
                        _cache[identifiedMatch] = previous with { Status = "INVALID" };
            _log.LogWarning("[MarketOdds] rejected market message ({Error})", ex.GetType().Name);
        }
    }
}
