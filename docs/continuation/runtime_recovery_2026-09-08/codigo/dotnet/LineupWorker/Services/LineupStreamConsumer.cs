using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using LineupWorker.Models;
using StackExchange.Redis;

namespace LineupWorker.Services;

/// <summary>Recoverable ingestion. ACK follows registration; process loss leaves entries pending.</summary>
public sealed class LineupStreamConsumer
{
    public const string StreamKey = "lineup:v2:inbox";
    public const string Group = "lineup-worker-v2";
    public const string RejectedKey = "lineup:v2:rejected";
    private readonly IDatabase _db;
    private readonly ILogger _log;
    private readonly Func<LineupEvent, DateTimeOffset, CancellationToken, Task> _handle;
    private readonly TimeSpan _maxAge;
    private readonly Func<Task>? _onHealthy;
    private readonly string _consumer = Guid.NewGuid().ToString("N");
    private bool _initialized;
    private RedisValue _claimCursor = "0-0";

    public LineupStreamConsumer(IDatabase db, ILogger log,
        Func<LineupEvent, DateTimeOffset, CancellationToken, Task> handle, TimeSpan maxAge,
        Func<Task>? onHealthy = null)
    {
        if (maxAge <= TimeSpan.Zero) throw new ArgumentOutOfRangeException(nameof(maxAge));
        _db = db;
        _log = log;
        _handle = handle;
        _maxAge = maxAge;
        _onHealthy = onHealthy;
    }

    public async Task RunAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                await ReadOnceAsync(ct);
                if (_onHealthy is not null) await _onHealthy();
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested) { return; }
            catch (RedisException ex)
            {
                // Recreate only a missing consumer group; never reset its delivery position.
                if (ex is RedisServerException && ex.Message.StartsWith("NOGROUP", StringComparison.Ordinal))
                    _initialized = false;
                _log.LogWarning("[Inbox] Redis indisponível; entradas não confirmadas serão retomadas ({Error})", ex.GetType().Name);
            }
            await Task.Delay(100, ct);
        }
    }

    public async Task ReadOnceAsync(CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        if (!_initialized)
        {
            try { await _db.StreamCreateConsumerGroupAsync(StreamKey, Group, "0-0", createStream: true); }
            catch (RedisServerException ex) when (ex.Message.StartsWith("BUSYGROUP", StringComparison.Ordinal)) { }
            _initialized = true;
        }
        // The cursor advances even when a poisoned entry fails, so later work is not starved.
        var recovered = await _db.StreamAutoClaimAsync(StreamKey, Group, _consumer, 1000, _claimCursor, count: 16);
        _claimCursor = recovered.NextStartId;
        foreach (var entry in recovered.ClaimedEntries) await ProcessAsync(entry, ct);
        var fresh = await _db.StreamReadGroupAsync(StreamKey, Group, _consumer, ">", count: 16);
        foreach (var entry in fresh) await ProcessAsync(entry, ct);
    }

    private async Task ProcessAsync(StreamEntry entry, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        var values = entry.Values.Where(value => value.Name == "payload").ToArray();
        var raw = values.Length == 1 ? values[0].Value.ToString() : "";
        LineupEvent? ev = null;
        string? reason = null;
        try
        {
            if (raw.Length == 0 || Encoding.UTF8.GetByteCount(raw) > 65536)
                reason = "invalid_envelope";
            else
            {
                ev = JsonSerializer.Deserialize<LineupEvent>(raw);
                if (ev is null || !IsValid(ev)) reason = "invalid_lineup";
                else if (ev.CapturedAt < DateTimeOffset.UtcNow - _maxAge) reason = "expired_lineup";
                else if (ev.CapturedAt > DateTimeOffset.UtcNow.AddMinutes(5)) reason = "future_capture";
            }
        }
        catch (JsonException) { reason = "invalid_json"; }

        if (reason is not null)
        {
            // Preserve diagnosis without echoing arbitrary provider payloads or secrets.
            var digest = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(raw)));
            await _db.ScriptEvaluateAsync(Reject, [StreamKey, RejectedKey], [Group, entry.Id, reason, digest]);
            _log.LogWarning("[Inbox] evento recusado {Id}: {Reason}", entry.Id, reason);
            return;
        }
        try
        {
            await _handle(ev!, DateTimeOffset.UtcNow, ct);
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested) { throw; }
        catch (Exception ex)
        {
            _log.LogWarning("[Inbox] evento {Id} mantido pendente ({Error})", entry.Id, ex.GetType().Name);
            return;
        }
        ct.ThrowIfCancellationRequested();
        // Single atomic command avoids ACK succeeding with a lost cleanup operation.
        // ACKED preserves entries referenced by any additional consumer group.
        await _db.ExecuteAsync("XACKDEL", StreamKey, Group, "ACKED", "IDS", 1, entry.Id);
    }

    public static bool IsValid(LineupEvent ev) =>
        !string.IsNullOrWhiteSpace(ev.MatchId) && ev.MatchId.Length <= 200 &&
        !string.IsNullOrWhiteSpace(ev.HomeTeam) && !string.IsNullOrWhiteSpace(ev.AwayTeam) &&
        ev.Side is "home" or "away" && ev.CapturedAt != default &&
        ev.Starters is { Length: 11 } && ev.Subs is { Length: <= 30 } &&
        ev.Starters.Concat(ev.Subs).All(p => !string.IsNullOrWhiteSpace(p) && p.Length <= 200) &&
        ev.Starters.Distinct(StringComparer.Ordinal).Count() == ev.Starters.Length &&
        ev.Subs.Distinct(StringComparer.Ordinal).Count() == ev.Subs.Length &&
        !ev.Starters.Intersect(ev.Subs, StringComparer.Ordinal).Any();

    private const string Reject = """
        local kind = redis.call('TYPE', KEYS[2]).ok
        if kind ~= 'none' and kind ~= 'stream' then return redis.error_reply('invalid rejection stream') end
        if not redis.acl_check_cmd('XADD', KEYS[2], 'MAXLEN', '=', '1000', '*', 'source_id', ARGV[2], 'reason', ARGV[3], 'sha256', ARGV[4])
          or not redis.acl_check_cmd('XACKDEL', KEYS[1], ARGV[1], 'ACKED', 'IDS', '1', ARGV[2]) then
            return redis.error_reply('rejection permissions unavailable')
        end
        local pending = redis.call('XPENDING', KEYS[1], ARGV[1], ARGV[2], ARGV[2], 1)
        if #pending == 0 then return 0 end
        redis.call('XADD', KEYS[2], 'MAXLEN', '=', '1000', '*', 'source_id', ARGV[2], 'reason', ARGV[3], 'sha256', ARGV[4])
        redis.call('XACKDEL', KEYS[1], ARGV[1], 'ACKED', 'IDS', '1', ARGV[2])
        return 1
        """;
}
