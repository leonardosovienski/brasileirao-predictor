using System.Text.Json;
using StackExchange.Redis;

namespace LineupWorker.Services;

/// <summary>
/// Bounded liveness of both processing loops for the single Worker deployment.
/// Redis connectivity alone is insufficient. This is not a business readiness or delivery guarantee.
/// </summary>
public sealed class WorkerHealth(IConnectionMultiplexer redis, string? instanceId = null)
{
    public const string KeyPrefix = "system:lineup_worker:health:";
    public const int LifetimeMs = 5_000;
    public string SessionId { get; } = Guid.NewGuid().ToString("N");
    public string InstanceId { get; } = instanceId ?? Environment.MachineName;

    public static string KeyFor(string role, string? instanceId = null) => role is "mse" or "inbox"
        ? KeyPrefix + (instanceId ?? Environment.MachineName) + ":" + role
        : throw new ArgumentException("Unknown Worker heartbeat role", nameof(role));

    private string Payload(string role) => JsonSerializer.Serialize(new
    {
        protocol_version = Models.RedisProtocol.Version,
        instance_id = InstanceId,
        session_id = SessionId,
        role
    });

    public async Task<bool> RenewAsync(string role)
    {
        const string renew = """
            local current = redis.call('GET', KEYS[1])
            if current and current ~= ARGV[1] then return 0 end
            redis.call('SET', KEYS[1], ARGV[1], 'PX', ARGV[2])
            return 1
            """;
        return (long)await redis.GetDatabase().ScriptEvaluateAsync(renew,
            [KeyFor(role, InstanceId)], [Payload(role), LifetimeMs]) == 1;
    }

    public async Task ReleaseAsync(string role)
    {
        const string cleanup = """
            if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
            return redis.call('DEL', KEYS[1])
            """;
        await redis.GetDatabase().ScriptEvaluateAsync(cleanup, [KeyFor(role, InstanceId)], [Payload(role)]);
    }

    public static async Task<bool> CheckAsync(IConnectionMultiplexer connection, string? instanceId = null)
    {
        const string check = """
            local session = nil
            for i = 1, 2 do
                if redis.call('TYPE', KEYS[i]).ok ~= 'string' or redis.call('PTTL', KEYS[i]) <= 0 then return 0 end
                local ok, value = pcall(cjson.decode, redis.call('GET', KEYS[i]))
                if not ok or type(value) ~= 'table' or value.protocol_version ~= ARGV[1] or
                   value.instance_id ~= ARGV[2] or value.role ~= ARGV[i + 2] or
                   type(value.session_id) ~= 'string' or #value.session_id ~= 32 or
                   not string.match(value.session_id, '^[0-9a-f]+$') then return 0 end
                if session and session ~= value.session_id then return 0 end
                session = value.session_id
            end
            return 1
            """;
        return (long)await connection.GetDatabase().ScriptEvaluateAsync(check,
            [KeyFor("mse", instanceId), KeyFor("inbox", instanceId)],
            [Models.RedisProtocol.Version, instanceId ?? Environment.MachineName, "mse", "inbox"]) == 1;
    }
}
