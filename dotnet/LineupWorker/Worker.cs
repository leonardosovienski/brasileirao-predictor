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
    private readonly bool _allowSyntheticInputs;

    // Fila interna desacoplada: receptor (pub/sub callback) → processador
    // BoundedChannel com DropOldest garante que GC pause nunca bloqueia o receptor Redis.
    private readonly Channel<(LineupEvent Event, DateTimeOffset T1_Received)> _queue;

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
        _allowSyntheticInputs = cfg.GetValue<bool>("Worker:AllowSyntheticInputs", false);

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

    private async Task HandleLineupAsync(LineupEvent ev, DateTimeOffset t1, CancellationToken ct)
    {
        if (!LineupStreamConsumer.IsValid(ev))
            throw new ArgumentException("Lineup requires valid identity, side, players and declared capture timestamp");
        // T2: VORP calculado em O(1) — lookup em ConcurrentDictionary em memória
        double eloHome, eloAway, delta;
        string inputIdentity;
        if (ev.ModelInputs is { } inputs)
        {
            inputIdentity = inputs.Validate(ev, t1, _vorp.ArtifactSha256);
            eloHome = inputs.EloHome;
            eloAway = inputs.EloAway;
            delta = _vorp.ComputeDeclaredDelta(ev.Starters.Select(p => (p, inputs.Positions[p])));
        }
        else
        {
            if (!_allowSyntheticInputs)
                throw new ArgumentException("Declared model inputs are required; synthetic Elo and positions are disabled");
            inputIdentity = "SYNTHETIC_ONLY";
            eloHome = eloAway = 1500;
            delta = _vorp.ComputeDeltaVorp(ev.Starters.Select(p => (p, "UNKNOWN")));
        }
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
            if (raw.HasValue && current.ModelInputIdentity != inputIdentity &&
                !(_allowSyntheticInputs && inputIdentity == "SYNTHETIC_ONLY" && current.ModelInputIdentity is null))
                throw new ArgumentException("Model context changed; reconcile both lineup sides before registration");
            if ((current.HomeTeamIdentity is not null && current.HomeTeamIdentity != ev.HomeTeam) ||
                (current.AwayTeamIdentity is not null && current.AwayTeamIdentity != ev.AwayTeam))
                throw new ArgumentException("Lineup team identity changed within the same event");
            var previousCapture = ev.Side == "home" ? current.HomeCapturedAt : current.AwayCapturedAt;
            var previousIdentity = ev.Side == "home" ? current.HomeEventIdentity : current.AwayEventIdentity;
            if (previousCapture.HasValue && ev.CapturedAt <= previousCapture.Value)
            {
                var reason = ev.CapturedAt < previousCapture.Value ? "older_capture" :
                    previousIdentity == eventIdentity ? "duplicate_event" : "conflicting_equal_capture";
                if (current.WatchdogDeadlineUnixMs.HasValue)
                {
                    var currentInvocation = await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + ev.MatchId);
                    if (await SynchronizeWatchdogAsync(db, ev.MatchId, raw, currentInvocation) == 0) continue;
                }
                _log.LogInformation("[Worker] IGNORE {Match}/{Side} — {Reason}", ev.MatchId, ev.Side, reason);
                return;
            }
            var deadline = current.WatchdogDeadlineUnixMs ??
                current.LineupCapturedAt.AddMinutes(_timeoutMinutes).ToUnixTimeMilliseconds();
            updated = ev.Side == "home"
                ? current with { DeltaVorpHome = delta, HomeLineupComplete = true,
                    LineupCapturedAt = ev.CapturedAt, ComputedAt = t2,
                    HomeCapturedAt = ev.CapturedAt, HomeEventIdentity = eventIdentity,
                    WatchdogDeadlineUnixMs = deadline, ModelInputIdentity = inputIdentity,
                    HomeTeamIdentity = ev.HomeTeam, AwayTeamIdentity = ev.AwayTeam }
                : current with { DeltaVorpAway = delta, AwayLineupComplete = true,
                    LineupCapturedAt = ev.CapturedAt, ComputedAt = t2,
                    AwayCapturedAt = ev.CapturedAt, AwayEventIdentity = eventIdentity,
                    WatchdogDeadlineUnixMs = deadline, ModelInputIdentity = inputIdentity,
                    HomeTeamIdentity = ev.HomeTeam, AwayTeamIdentity = ev.AwayTeam };
            // Commit state, version, current request and wakeup in one Redis script.
            // CAS failure rereads and merges the other side; invocation is awaited.
            var registration = await _mse.InvokeKernelAsync(ev.MatchId, eloHome, eloAway,
                updated, raw.HasValue ? raw.ToString() : null, sourceEvent,
                TimeSpan.FromHours(_redisStateTtlHours), ct);
            if (registration.Status == "conflict") continue;
            if (registration.Status != "registered") return;
            break;
        }

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

    private static async Task<long> SynchronizeWatchdogAsync(IDatabase db, string matchId,
        RedisValue state, RedisValue current)
        => (long)await db.ScriptEvaluateAsync(WatchdogStateStore.Synchronize,
            [STATE_KEY_PREFIX + matchId, KernelRedisProtocolV2.CurrentPrefix + matchId, KernelRedisProtocolV2.WatchdogKey],
            [state.HasValue ? "1" : "0", state.HasValue ? state : "",
             current.HasValue ? "1" : "0", current.HasValue ? current : "", matchId]);

    private async Task TimeoutWatchdogAsync(CancellationToken ct)
    {
        var cursor = "0";
        while (!ct.IsCancellationRequested)
        {
            try
            {
                var db = _redis.GetDatabase();
                var due = (RedisResult[]?)await db.ScriptEvaluateAsync(WatchdogStateStore.ReadDue,
                    [KernelRedisProtocolV2.WatchdogKey], [cursor])
                    ?? throw new JsonException("Invalid watchdog scan reply");
                cursor = due[0].ToString();
                var now = DateTimeOffset.FromUnixTimeMilliseconds((long)due[1]);
                foreach (var item in due.Skip(2))
                {
                    ct.ThrowIfCancellationRequested();
                    var matchId = item.ToString();
                    try { await ApplyTimeoutAsync(db, matchId, now, ct); }
                    catch (Exception ex) when (ex is RedisException or JsonException)
                    {
                        _log.LogWarning("[Worker] watchdog {Match} adiado; índice preservado ({Error})", matchId, ex.GetType().Name);
                    }
                }
            }
            catch (Exception ex) when (ex is RedisException or JsonException)
            {
                _log.LogWarning("[Worker] índice watchdog indisponível; será retomado ({Error})", ex.GetType().Name);
                cursor = "0";
            }
            // First scan is immediate. Subsequent pages are bounded scans, with
            // short gaps rather than waiting a full interval for every page.
            await Task.Delay(cursor == "0" ? TimeSpan.FromSeconds(_watchdogIntervalSec)
                : TimeSpan.FromMilliseconds(100), ct);
        }
    }

    private async Task ApplyTimeoutAsync(IDatabase db, string matchId, DateTimeOffset now, CancellationToken ct)
    {
        var raw = await db.StringGetAsync(STATE_KEY_PREFIX + matchId);
        var currentRaw = await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + matchId);
        if (!raw.HasValue)
        {
            await SynchronizeWatchdogAsync(db, matchId, raw, currentRaw);
            return;
        }
        var state = JsonSerializer.Deserialize<LineupState>(raw.ToString())
            ?? throw new JsonException("Invalid watchdog state");
        if (state.MatchId != matchId) throw new JsonException("Watchdog state identity mismatch");
        bool needH = !state.HomeLineupComplete;
        bool needA = !state.AwayLineupComplete;
        if ((!needH && !needA) || !state.WatchdogDeadlineUnixMs.HasValue ||
            state.WatchdogDeadlineUnixMs > now.ToUnixTimeMilliseconds() ||
            (!currentRaw.HasValue && state.FallbackStrategy == "timeout_widen_variance"))
        {
            await SynchronizeWatchdogAsync(db, matchId, raw, currentRaw);
            return;
        }
        _log.LogWarning("[Worker] TIMEOUT {Match} — fallback widening (home={H} away={A})", matchId, needH, needA);
        var signals = new List<VarianceWideningSignal>();
        foreach (var (side, needed, team) in new[]
        {
            ("home", needH, state.HomeTeamIdentity ?? ""),
            ("away", needA, state.AwayTeamIdentity ?? ""),
        })
        {
            if (!needed) continue;
            signals.Add(new VarianceWideningSignal(matchId, side, _widenFactor,
                _vorp.GetTitularidadeMatrix(team) ?? Array.Empty<double>(), now));
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
             KernelRedisProtocolV2.ReadyKey, KernelRedisProtocolV2.WatchdogKey], arguments.ToArray());
        if (applied != 1) return; // The newer state and its durable index remain untouched.
        foreach (var signal in signals)
        {
            var record = new LatencyRecord(matchId, signal.Side, state.LineupCapturedAt, now, now, now,
                null, 0, true, "timeout_widen_variance");
            _ = _audit.RecordAsync(record).AsTask();
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

}
