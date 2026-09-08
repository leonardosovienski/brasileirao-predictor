using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using LineupWorker.Models;
using LineupWorker.Services;
using StackExchange.Redis;

namespace LineupWorker;

/// <summary>
/// Worker de escalações — Hot Path da Zona 1.
///
/// Fluxo de latência auditado (todos os timestamps em UTC de alta resolução):
///
///   T0 (source) → [Redis pub/sub] → T1 (received) → [VORP lookup O(1)] →
///   T2 (vorp computed) → [Redis atomic registration] → T3 (redis written) →
///   → [lineup_complete] → MarketStateEngine → T4 (market read)
///
/// Garantias de latência:
///   • VORP lookup: O(1) — ConcurrentDictionary em memória, sem lock.
///   • Nenhuma alocação de string no caminho do VORP (chaves pré-interned).
///   • Redis: CAS do snapshot e registro da invocação em um script.
///   • GC: Channel<T> pré-alocado; LineupEvent é um record (sem boxing).
///
/// Fallback de timeout (watchdog a cada 60s):
///   • Se T_deadline < agora e escalação não chegou → emite VarianceWideningSignal
///     com a matriz de titularidade histórica do time, sinalizando ao
///     MarketStateEngine que deve alargar a variância do modelo.
/// </summary>
public sealed class LineupWorkerService : BackgroundService
{
    private const string LINEUP_CHANNEL_PATTERN = "lineups:*";
    private const string STATE_KEY_PREFIX       = "lineup_state:";
    private const string WIDEN_CHANNEL          = "variance_widen";

    private readonly ILogger<LineupWorkerService> _log;
    private readonly VorpStateService             _vorp;
    private readonly LatencyAuditService          _audit;
    private readonly MarketStateEngine            _mse;
    private readonly IConnectionMultiplexer       _redis;
    private readonly WorkerHealth?                _health;
    private readonly int    _timeoutMinutes;
    private readonly double _widenFactor;
    private readonly int    _watchdogIntervalSec;
    private readonly int    _redisStateTtlHours;

    // Fila interna desacoplada: receptor (pub/sub callback) → processador
    // BoundedChannel com DropOldest garante que GC pause nunca bloqueia o receptor Redis.
    private readonly Channel<(LineupEvent Event, DateTimeOffset T1_Received)> _queue;

    // Partidas aguardando escalação: matchId → (deadline, homeOk, awayOk)
    private readonly ConcurrentDictionary<string, MatchTracking> _pending = new();

    public LineupWorkerService(
        ILogger<LineupWorkerService> log,
        VorpStateService vorp,
        LatencyAuditService audit,
        MarketStateEngine mse,
        IConnectionMultiplexer redis,
        IConfiguration cfg,
        WorkerHealth? health = null)
    {
        _log                = log;
        _vorp               = vorp;
        _audit              = audit;
        _mse                = mse;
        _redis              = redis;
        _health             = health;
        _timeoutMinutes     = cfg.GetValue<int>("Worker:LineupTimeoutMinutes",    55);
        _widenFactor        = cfg.GetValue<double>("Worker:VarianceWideningFactor", 1.35);
        _watchdogIntervalSec = cfg.GetValue<int>("Worker:WatchdogIntervalSeconds",  60);
        _redisStateTtlHours = cfg.GetValue<int>("Worker:RedisStateTtlHours",        6);

        var cap = cfg.GetValue<int>("Worker:QueueCapacity", 512);
        _queue = Channel.CreateBounded<(LineupEvent Event, DateTimeOffset T1_Received)>(
            new BoundedChannelOptions(cap)
            {
                SingleReader = false,
                FullMode     = BoundedChannelFullMode.DropOldest,
            }, OnLineupDropped);
    }

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        while (!_vorp.IsReady)
        {
            _log.LogWarning("[Worker] VorpStateService ainda não aqueceu — aguardando…");
            await Task.Delay(2_000, ct);
        }

        var sub = _redis.GetSubscriber();

        // ChannelMessageQueue.OnMessage: API não-ambígua e robusta entre versões
        // do StackExchange.Redis (as sobrecargas com Action<RedisChannel,RedisValue>
        // são obsoletas/ambíguas em 2.7+).
        var queue = await sub.SubscribeAsync(RedisChannel.Pattern(LINEUP_CHANNEL_PATTERN));
        queue.OnMessage(channelMessage =>
        {
            // T1 capturado IMEDIATAMENTE ao receber — antes de qualquer processamento
            var t1 = DateTimeOffset.UtcNow;
            var message = channelMessage.Message;
            if (!message.HasValue) return;
            try
            {
                var ev = JsonSerializer.Deserialize<LineupEvent>(message.ToString());
                if (ev is null) return;

                // DropOldest reports the actual evicted item through its callback.
                // A false result here means this incoming item was not accepted.
                if (!_queue.Writer.TryWrite((ev, t1)))
                {
                    _log.LogCritical(
                        "[CRITICAL] SLA_BREACH_CRITICAL {Match}/{Side} — Channel " +
                        "indisponível. Fallback de incerteza imediato.",
                        ev.MatchId, ev.Side);
                    _ = TriggerImmediateFallbackAsync(ev.MatchId, ev.Side, ev.CapturedAt);
                }
            }
            catch (Exception ex)
            {
                _log.LogError(ex, "[Worker] falha ao desserializar escalação");
            }
        });

        _log.LogInformation("[Worker] escutando {Pattern}", LINEUP_CHANNEL_PATTERN);

        try
        {
            await Task.WhenAll(
                ProcessQueueAsync(ct),
                TimeoutWatchdogAsync(ct),
                new LineupStreamConsumer(_redis.GetDatabase(), _log, HandleLineupAsync,
                    TimeSpan.FromMinutes(_timeoutMinutes),
                    _health is null ? null : () => _health.RenewAsync("inbox")).RunAsync(ct)
            );
        }
        finally
        {
            if (_health is not null)
            {
                try { await _health.ReleaseAsync("inbox"); }
                catch (RedisException) { _log.LogWarning("[Worker] saúde expirará por TTL após parada"); }
            }
            try { await queue.UnsubscribeAsync(); }
            catch (RedisException) { _log.LogWarning("[Worker] Redis indisponível ao remover assinatura legada"); }
        }
    }

    // ---------------------------------------------------------------------------
    // Hot path: processamento de escalações
    // ---------------------------------------------------------------------------

    private async Task ProcessQueueAsync(CancellationToken ct)
    {
        // This is bounded recovery for an already captured event, not durable ingestion.
        // After three transient failures, the event is logged and processing continues.
        await foreach (var (ev, t1) in _queue.Reader.ReadAllAsync(ct))
        {
            for (var attempt = 1; attempt <= 3; attempt++)
            {
                try
                {
                    await HandleLineupAsync(ev, t1, ct);
                    break;
                }
                catch (OperationCanceledException) when (ct.IsCancellationRequested) { return; }
                catch (Exception ex) when (attempt < 3 && (ex is RedisConnectionException or RedisTimeoutException))
                {
                    _log.LogWarning("[Worker] retry Redis {Match}, tentativa {Attempt}/3", ev.MatchId, attempt);
                    await Task.Delay(TimeSpan.FromMilliseconds(100 * attempt), ct);
                }
                catch (Exception ex)
                {
                    _log.LogError(ex, "[Worker] evento não concluído {Match}, tentativa {Attempt}/3", ev.MatchId, attempt);
                    break; // Malformed/permanent errors are not retried indefinitely.
                }
            }
        }
    }

    private void OnLineupDropped((LineupEvent Event, DateTimeOffset T1_Received) dropped)
    {
        _log.LogCritical("[CRITICAL] SLA_BREACH_CRITICAL {Match}/{Side} — escalação descartada por DropOldest",
            dropped.Event.MatchId, dropped.Event.Side);
        _ = TriggerImmediateFallbackAsync(dropped.Event.MatchId, dropped.Event.Side, dropped.Event.CapturedAt)
            .ContinueWith(task => _log.LogError(task.Exception, "[Worker] falha no fallback do item descartado"),
                TaskContinuationOptions.OnlyOnFaulted);
    }

    private void TrackPending(LineupEvent ev, LineupState state) =>
        _pending.AddOrUpdate(ev.MatchId,
            new MatchTracking(ev.CapturedAt.AddMinutes(_timeoutMinutes), state.HomeLineupComplete, state.AwayLineupComplete),
            (_, tracking) => tracking with { HomeOk = state.HomeLineupComplete, AwayOk = state.AwayLineupComplete });

    private async Task HandleLineupAsync(LineupEvent ev, DateTimeOffset t1, CancellationToken ct)
    {
        if (!LineupStreamConsumer.IsValid(ev))
            throw new ArgumentException("Lineup requires valid identity, side, players and declared capture timestamp");
        // T2: VORP calculado em O(1) — lookup em ConcurrentDictionary em memória
        var starters = ev.Starters.Select(p => (Player: p, Position: "UNKNOWN"));
        var delta    = _vorp.ComputeDeltaVorp(starters);
        var t2       = DateTimeOffset.UtcNow;

        var sourceEvent = JsonSerializer.Serialize(ev);
        var eventIdentity = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(sourceEvent)));
        var db   = _redis.GetDatabase();
        var key  = STATE_KEY_PREFIX + ev.MatchId;
        LineupState updated;
        while (true)
        {
            ct.ThrowIfCancellationRequested();
            var raw = await db.StringGetAsync(key);
            var current = raw.HasValue
                ? JsonSerializer.Deserialize<LineupState>(raw.ToString())
                    ?? throw new JsonException("Invalid lineup state")
                : new LineupState(ev.MatchId, 0, 0, false, false, ev.CapturedAt, t2, "none");
            if (current.MatchId != ev.MatchId) throw new JsonException("Lineup state identity mismatch");
            var previousCapture = ev.Side == "home" ? current.HomeCapturedAt : current.AwayCapturedAt;
            var previousIdentity = ev.Side == "home" ? current.HomeEventIdentity : current.AwayEventIdentity;
            if (previousCapture.HasValue && ev.CapturedAt <= previousCapture.Value)
            {
                var reason = ev.CapturedAt < previousCapture.Value ? "older_capture" :
                    previousIdentity == eventIdentity ? "duplicate_event" : "conflicting_equal_capture";
                if (reason == "duplicate_event") TrackPending(ev, current);
                _log.LogInformation("[Worker] IGNORE {Match}/{Side} — {Reason}", ev.MatchId, ev.Side, reason);
                return;
            }
            updated = ev.Side == "home"
                ? current with { DeltaVorpHome = delta, HomeLineupComplete = true,
                    LineupCapturedAt = ev.CapturedAt, ComputedAt = t2,
                    HomeCapturedAt = ev.CapturedAt, HomeEventIdentity = eventIdentity }
                : current with { DeltaVorpAway = delta, AwayLineupComplete = true,
                    LineupCapturedAt = ev.CapturedAt, ComputedAt = t2,
                    AwayCapturedAt = ev.CapturedAt, AwayEventIdentity = eventIdentity };
            // Commit state, version, current request and wakeup in one Redis script.
            // CAS failure rereads and merges the other side; invocation is awaited.
            var registration = await _mse.InvokeKernelAsync(ev.MatchId, 1500.0, 1500.0,
                updated, raw.HasValue ? raw.ToString() : null, sourceEvent,
                TimeSpan.FromHours(_redisStateTtlHours), ct);
            if (registration.Status == "conflict") continue;
            if (registration.Status != "registered") return;
            break;
        }

        TrackPending(ev, updated);

        var t3 = DateTimeOffset.UtcNow;

        // Grava registro de latência para auditoria (fora do caminho crítico)
        var latRec = new LatencyRecord(
            MatchId:            ev.MatchId,
            Side:               ev.Side,
            T0_SourcePublished: ev.CapturedAt,
            T1_Received:        t1,
            T2_VorpComputed:    t2,
            T3_RedisWritten:    t3,
            T4_MarketEngineRead: null,
            DeltaVorp:          delta,
            IsFallback:         false,
            FallbackReason:     null
        );
        // Fire-and-forget na auditoria — não bloqueia o hot path
        _ = _audit.RecordAsync(latRec).AsTask()
            .ContinueWith(t => _log.LogError(t.Exception, "[Worker] falha na auditoria"),
                          TaskContinuationOptions.OnlyOnFaulted);

        _log.LogInformation(
            "[Worker] {Match} {Side} ΔVORP={D:+0.000} E2E={E2E:F1}ms (net={Net:F1} proc={Proc:F2} write={Write:F1})",
            ev.MatchId, ev.Side, delta, (t3 - ev.CapturedAt).TotalMilliseconds,
            (t1 - ev.CapturedAt).TotalMilliseconds,
            (t2 - t1).TotalMilliseconds,
            (t3 - t2).TotalMilliseconds);
    }

    // ---------------------------------------------------------------------------
    // Watchdog de timeout — fallback quando escalação não chega
    // ---------------------------------------------------------------------------

    private async Task TimeoutWatchdogAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            await Task.Delay(TimeSpan.FromSeconds(_watchdogIntervalSec), ct);

            var now     = DateTimeOffset.UtcNow;
            var expired = _pending
                .Where(kv => kv.Value.Deadline < now)
                .Select(kv => kv.Key)
                .ToList();

            foreach (var matchId in expired)
            {
                try
                {
                if (!_pending.TryGetValue(matchId, out var tracking)) continue;

                var db  = _redis.GetDatabase();
                var raw = await db.StringGetAsync(STATE_KEY_PREFIX + matchId);
                if (!raw.HasValue)
                {
                    _pending.TryRemove(new KeyValuePair<string, MatchTracking>(matchId, tracking));
                    continue;
                }
                var currentRaw = await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + matchId);

                var state = JsonSerializer.Deserialize<LineupState>(raw.ToString())
                    ?? throw new JsonException("Invalid watchdog state");
                bool needH  = !state.HomeLineupComplete;
                bool needA  = !state.AwayLineupComplete;
                if ((!needH && !needA) || (!currentRaw.HasValue && state.FallbackStrategy == "timeout_widen_variance"))
                {
                    _pending.TryRemove(new KeyValuePair<string, MatchTracking>(matchId, tracking));
                    continue;
                }

                _log.LogWarning("[Worker] TIMEOUT {Match} — fallback widening (home={H} away={A})",
                    matchId, needH, needA);

                var signals = new List<VarianceWideningSignal>();
                foreach (var (side, needed, team) in new[]
                {
                    ("home", needH, matchId.Split('_').ElementAtOrDefault(0) ?? ""),
                    ("away", needA, matchId.Split('_').ElementAtOrDefault(1) ?? ""),
                })
                {
                    if (!needed) continue;

                    var mat    = _vorp.GetTitularidadeMatrix(team);
                    var signal = new VarianceWideningSignal(
                        MatchId:            matchId,
                        Side:               side,
                        VarianceMultiplier: _widenFactor,
                        TitularidadeMatrix: mat ?? Array.Empty<double>(),
                        IssuedAt:           now
                    );
                    signals.Add(signal);
                }
                var fallback = state with { FallbackStrategy = "timeout_widen_variance", ComputedAt = now };
                var arguments = new List<RedisValue>
                {
                    raw, currentRaw.HasValue ? "1" : "0", currentRaw.HasValue ? currentRaw : "",
                    JsonSerializer.Serialize(fallback), checked((long)TimeSpan.FromHours(_redisStateTtlHours).TotalMilliseconds),
                    KernelRedisProtocolV2.LeasePrefix, WIDEN_CHANNEL
                };
                arguments.AddRange(signals.Select(signal => (RedisValue)JsonSerializer.Serialize(signal)));
                ct.ThrowIfCancellationRequested();
                var applied = (long)await db.ScriptEvaluateAsync(KernelRedisProtocolV2.ApplyWatchdog,
                    [STATE_KEY_PREFIX + matchId, KernelRedisProtocolV2.CurrentPrefix + matchId,
                     "fair_odds:" + matchId, KernelRedisProtocolV2.PendingKey,
                     KernelRedisProtocolV2.ReadyKey], arguments.ToArray());
                if (applied != 1) continue; // New state won the race; retain tracking for a fresh read.
                _pending.TryRemove(new KeyValuePair<string, MatchTracking>(matchId, tracking));
                foreach (var signal in signals)
                {
                    var latRec = new LatencyRecord(
                        MatchId:            matchId,
                        Side:               signal.Side,
                        T0_SourcePublished: now.AddMinutes(-_timeoutMinutes),
                        T1_Received:        now,
                        T2_VorpComputed:    now,
                        T3_RedisWritten:    now,
                        T4_MarketEngineRead: null,
                        DeltaVorp:          0,
                        IsFallback:         true,
                        FallbackReason:     "timeout_widen_variance"
                    );
                    _ = _audit.RecordAsync(latRec).AsTask();
                }

                }
                catch (Exception ex) when (ex is RedisException or JsonException)
                {
                    _log.LogWarning("[Worker] watchdog {Match} adiado; estado preservado ({Error})", matchId, ex.GetType().Name);
                }
            }
        }
    }

    /// <summary>
    /// Fallback imediato para quando o Channel descarta uma escalação (SLA_BREACH_CRITICAL).
    /// Emite VarianceWideningSignal e registra o breach na auditoria.
    /// Iniciado pelo callback; a conclusão assíncrona não bloqueia o receptor.
    /// </summary>
    private async Task TriggerImmediateFallbackAsync(
        string matchId, string side, DateTimeOffset sourceTs)
    {
        var now = DateTimeOffset.UtcNow;
        var sub = _redis.GetSubscriber();

        var signal = new VarianceWideningSignal(
            MatchId:            matchId,
            Side:               side,
            VarianceMultiplier: _widenFactor,
            TitularidadeMatrix: Array.Empty<double>(),   // sem lineup → sem matriz
            IssuedAt:           now
        );
        await sub.PublishAsync(
            RedisChannel.Literal(WIDEN_CHANNEL),
            JsonSerializer.Serialize(signal));

        var latRec = new LatencyRecord(
            MatchId:            matchId,
            Side:               side,
            T0_SourcePublished: sourceTs,
            T1_Received:        now,
            T2_VorpComputed:    now,
            T3_RedisWritten:    now,
            T4_MarketEngineRead: null,
            DeltaVorp:          0,
            IsFallback:         true,
            FallbackReason:     "sla_breach_critical_channel_full"
        );
        await _audit.RecordAsync(latRec);
    }

    private record MatchTracking(DateTimeOffset Deadline, bool HomeOk, bool AwayOk);
}
