using System.Security.Cryptography;
using System.Text.Json;
using LineupWorker.Models;
using StackExchange.Redis;
using RedisProtocol = LineupWorker.Models.RedisProtocol;

namespace LineupWorker.Services;

/// <summary>
/// MarketStateEngine — Zona 2 do Hot Path.
///
/// Acorda via notificação Redis "fair_odds_ready:{match_id}" publicada pelo Kernel Python
/// após escrever a chave efêmera "fair_odds:{match_id}" (TTL 5s).
///
/// T4 está estritamente definido como o clock tick imediatamente ANTES da emissão do
/// BetSignal — engloba a leitura das Fair Odds (Redis), a leitura das Market Odds
/// (ConcurrentDictionary em memória) e a aritmética de edge. Nenhum I/O de banco.
///
/// Contrato de abortamento:
///   • Fair Odds expiradas (chave TTL esgotada → Redis retorna null) → ABORT.
///   • Market Odds ausentes ou stale (> 30s) → ABORT.
///   • Edge fora da janela [MinEdge, MaxEdge] → não gera sinal (sem ABORT).
/// </summary>
public sealed class MarketStateEngine : BackgroundService
{
    public static double FractionalKelly(double probability, double odds, double fraction, double cap = 0.05)
        => Math.Min(fraction * (probability * odds - 1.0) / (odds - 1.0), cap);

    private const string FAIR_ODDS_READY_PATTERN = "fair_odds_ready:*";
    private const string FAIR_ODDS_KEY_PREFIX    = "fair_odds:";
    private const string STATE_KEY_PREFIX        = "lineup_state:";
    private const string BET_SIGNAL_CHANNEL      = "bet_signals";

    private readonly IConnectionMultiplexer _redis;
    private readonly MarketOddsCache        _marketCache;
    private readonly LatencyAuditService    _audit;
    private readonly ILogger<MarketStateEngine> _log;
    private readonly double _minEdge;
    private readonly double _maxEdge;
    private readonly double _kellyFrac;
    private readonly double _budgetMs;
    private readonly WorkerHealth? _health;

    public MarketStateEngine(
        IConnectionMultiplexer redis,
        MarketOddsCache marketCache,
        LatencyAuditService audit,
        ILogger<MarketStateEngine> log,
        IConfiguration cfg,
        WorkerHealth? health = null)
    {
        _redis       = redis;
        _marketCache = marketCache;
        _audit       = audit;
        _log         = log;
        _health      = health;
        _minEdge  = cfg.GetValue<double>("MarketStateEngine:MinEdgePct",    0.02);
        _maxEdge  = cfg.GetValue<double>("MarketStateEngine:MaxEdgePct",    0.15);
        _kellyFrac = cfg.GetValue<double>("MarketStateEngine:KellyFraction", 0.25);
        _budgetMs = cfg.GetValue<double>("MarketStateEngine:LatencyBudgetMs", 300);
    }

    protected override Task ExecuteAsync(CancellationToken ct)
        => Task.WhenAll(ListenForReadyAsync(ct), PollReadyAsync(ct));

    private async Task ListenForReadyAsync(CancellationToken ct)
    {
        var sub = _redis.GetSubscriber();

        // Subscreve ao canal de notificação publicado pelo Kernel Python.
        // ChannelMessageQueue.OnMessage: API não-ambígua e robusta entre versões.
        ChannelMessageQueue? queue = null;
        while (queue is null)
        {
            ct.ThrowIfCancellationRequested();
            try { queue = await sub.SubscribeAsync(RedisChannel.Pattern(FAIR_ODDS_READY_PATTERN)); }
            catch (RedisException ex)
            {
                _log.LogWarning(ex, "[MSE] notificação indisponível; recuperação por índice continua ativa");
                await Task.Delay(100, ct);
            }
        }
        queue.OnMessage(async channelMessage =>
        {
            var message = channelMessage.Message;
            if (!message.HasValue) return;
            // Extrai matchId do nome do canal (fair_odds_ready:{matchId})
            var channelStr = channelMessage.Channel.ToString();
            var prefix     = FAIR_ODDS_READY_PATTERN[..^1];   // "fair_odds_ready:"
            var matchId    = channelStr.StartsWith(prefix)
                ? channelStr[prefix.Length..]
                : "";
            if (string.IsNullOrEmpty(matchId)) return;

            try { await ProcessFairOddsAsync(matchId, message.ToString(), ct); }
            catch (Exception ex)
            {
                _log.LogError(ex, "[MSE] erro ao processar fair_odds_ready:{Match}", matchId);
            }
        });

        _log.LogInformation("[MSE] aguardando fair_odds_ready:* do Kernel Python…");
        await Task.Delay(Timeout.Infinite, ct);
    }

    private async Task PollReadyAsync(CancellationToken ct)
    {
        var cursor = "0";
        var unavailable = false;
        try
        {
            while (!ct.IsCancellationRequested)
            {
                try
                {
                    var db = _redis.GetDatabase();
                    var scanned = (RedisResult[]?)await db.ScriptEvaluateAsync(
                        KernelRedisProtocolV2.ReadReady, [KernelRedisProtocolV2.ReadyKey], [cursor])
                        ?? throw new InvalidOperationException("Invalid ready scan reply");
                    cursor = scanned[0].ToString();
                    foreach (var item in scanned.Skip(1))
                    {
                        ct.ThrowIfCancellationRequested();
                        var runId = item.ToString();
                        var fair = await db.HashGetAsync(KernelRedisProtocolV2.RequestPrefix + runId, "result");
                        if (!fair.HasValue) continue;
                        try
                        {
                            using var document = JsonDocument.Parse(fair.ToString());
                            var identity = FairOddsIdentity.Read(document.RootElement);
                            if (identity.RunId != runId) continue;
                            await ProcessFairOddsAsync(identity.MatchId, fair.ToString(), ct);
                        }
                        catch (Exception ex) when (ex is JsonException or InvalidOperationException)
                        {
                            _log.LogWarning(ex, "[MSE] resultado inválido no índice ready; nenhuma emissão autorizada");
                        }
                    }
                    if (_health is not null) await _health.RenewAsync("mse");
                    unavailable = false;
                }
                catch (RedisException ex)
                {
                    if (!unavailable) _log.LogWarning(ex, "[MSE] recuperação ready temporariamente indisponível");
                    unavailable = true;
                    cursor = "0"; // A reconnect starts another complete scan; final dedup is authoritative.
                }
                await Task.Delay(100, ct);
            }
        }
        finally
        {
            if (_health is not null)
            {
                try { await _health.ReleaseAsync("mse"); }
                catch (RedisException ex) { _log.LogWarning(ex, "[MSE] cleanup de heartbeat indisponível; TTL permanece limitado"); }
            }
        }
    }

    // ---------------------------------------------------------------------------
    // Hot path T3.5 → T4
    // ---------------------------------------------------------------------------

    private async Task ProcessFairOddsAsync(string matchId, string fairOddsJson,
                                            CancellationToken ct)
    {
        // The final Redis script repeats every fence after all awaited reads.
        // A matching notification at this first read alone does not authorize a signal.
        var db      = _redis.GetDatabase();
        var rawKey  = await db.StringGetAsync(FAIR_ODDS_KEY_PREFIX + matchId);
        var currentRaw = await db.StringGetAsync(KernelRedisProtocolV2.CurrentPrefix + matchId);
        if (!rawKey.HasValue || !currentRaw.HasValue || rawKey.ToString() != fairOddsJson)
        {
            _log.LogWarning("[MSE] ABORT {Match} — fair odds ausentes ou notificação sem correspondência exata", matchId);
            return;
        }

        FairOddsPayload fair;
        FairOddsIdentity identity;
        KernelInvokePayload invocation;
        try
        {
            using var doc = JsonDocument.Parse(rawKey.ToString());
            fair = FairOddsPayload.FromDict(doc.RootElement);
            identity = FairOddsIdentity.Read(doc.RootElement);
            invocation = JsonSerializer.Deserialize<KernelInvokePayload>(currentRaw.ToString())
                ?? throw new JsonException("Current invocation is missing");
            if (identity.MatchId != matchId || invocation.match_id != matchId ||
                invocation.protocol_version != RedisProtocol.Version ||
                identity.JobId != invocation.job_id || identity.RunId != invocation.run_id ||
                identity.StateVersion != invocation.state_version || identity.IdempotencyKey != invocation.idempotency_key)
            {
                _log.LogWarning("[MSE] ABORT {Match} — notificação não corresponde à invocação na chave", matchId);
                return;
            }
        }
        catch (Exception ex) when (ex is JsonException or InvalidOperationException)
        {
            _log.LogError(ex, "[MSE] JSON inválido em fair_odds:{Match}", matchId);
            return;
        }

        // Market Odds: O(1) lookup em ConcurrentDictionary — zero I/O
        var market = _marketCache.TryGet(matchId);
        if (market is null)
        {
            _log.LogWarning("[MSE] ABORT {Match} — market odds ausentes ou stale", matchId);
            return;
        }

        // Use the exact lineup snapshot registered with these model inputs.
        var requestKey = KernelRedisProtocolV2.RequestPrefix + identity.RunId;
        var stateRaw = await db.HashGetAsync(requestKey, "lineup_state");
        if (!stateRaw.HasValue) return;
        var state = JsonSerializer.Deserialize<LineupState>(stateRaw.ToString());
        if (state is null || state.MatchId != matchId ||
            state.DeltaVorpHome != invocation.dvorp_a || state.DeltaVorpAway != invocation.dvorp_b)
            return;

        // T4: clock tick estrito ANTES da aritmética de edge (não depois)
        var t4 = DateTimeOffset.UtcNow;

        var signals = ComputeEdge(matchId, fair, market, state, t4)
            .Select(signal => signal with
            {
                JobId = identity.JobId, RunId = identity.RunId, StateVersion = identity.StateVersion
            }).ToList();

        try { await _audit.MarkMarketReadAsync(matchId, "combined", t4); }
        catch (Exception ex) when (ex is RedisException or JsonException)
        {
            _log.LogWarning(ex, "[MSE] auditoria de latência indisponível; fences econômicos continuam obrigatórios");
        }

        if (!signals.Any())
        {
            _log.LogDebug("[MSE] {Match} — sem edge na janela [{Min:P0},{Max:P0}]",
                matchId, _minEdge, _maxEdge);
            return;
        }

        ct.ThrowIfCancellationRequested();
        var arguments = new List<RedisValue> { currentRaw, rawKey, stateRaw, BET_SIGNAL_CHANNEL };
        arguments.AddRange(signals.Select(signal => (RedisValue)JsonSerializer.Serialize(signal)));
        var emitted = (long)await db.ScriptEvaluateAsync(KernelRedisProtocolV2.PublishSignals,
            [KernelRedisProtocolV2.CurrentPrefix + matchId, FAIR_ODDS_KEY_PREFIX + matchId,
             requestKey, STATE_KEY_PREFIX + matchId, KernelRedisProtocolV2.SignalsPrefix + identity.RunId,
             KernelRedisProtocolV2.ReadyKey, KernelRedisProtocolV2.SignalOutboxKey],
            arguments.ToArray());
        if (emitted <= 0)
        {
            _log.LogInformation("[MSE] ABORT {Match} — execução obsoleta, expirada ou batch já emitido ({Fence})", matchId, emitted);
            return;
        }
        foreach (var sig in signals)
        {
            _log.LogInformation(
                "[MSE] BetSignal retido na outbox {Match} {Mkt}/{Sel}: edge={E:+0.00%} kelly={K:P2} " +
                "fair={F:F3} market={M:F3} E2E={L:F1}ms {SLA}",
                sig.MatchId, sig.Market, sig.Selection,
                sig.EdgeVsPrice, sig.KellyStake,
                sig.PModel > 0 ? 1.0 / sig.PModel : 0, sig.OddsOffered,
                sig.PipelineLatencyMs,
                sig.PipelineLatencyMs <= _budgetMs ? "✓" : "⚠ LATE");
        }
    }

    // ---------------------------------------------------------------------------
    // Aritmética de edge (puramente em RAM, sem I/O)
    // ---------------------------------------------------------------------------

    private IEnumerable<BetSignal> ComputeEdge(
        string matchId, FairOddsPayload fair, MarketOdds market,
        LineupState? state, DateTimeOffset t4)
    {
        var dvh = state?.DeltaVorpHome ?? 0;
        var dva = state?.DeltaVorpAway ?? 0;
        var e2e = state != null
            ? (t4 - state.LineupCapturedAt).TotalMilliseconds
            : 0;

        // Iteração sobre os mercados disponíveis
        var candidates = new[]
        {
            (Market: "1x2", Sel: "home",  FairOdd: fair.Home,    MarketOdd: market.OddsHome),
            (Market: "1x2", Sel: "draw",  FairOdd: fair.Draw,    MarketOdd: market.OddsDraw),
            (Market: "1x2", Sel: "away",  FairOdd: fair.Away,    MarketOdd: market.OddsAway),
            (Market: "ou25", Sel: "over",  FairOdd: fair.Over25,  MarketOdd: market.OddsOver25 ?? 0),
            (Market: "ou25", Sel: "under", FairOdd: fair.Under25, MarketOdd: market.OddsUnder25 ?? 0),
        };

        foreach (var (mkt, sel, fairOdd, marketOdd) in candidates)
        {
            if (fairOdd is null || fairOdd <= 1.0 || marketOdd <= 1.0) continue;

            // p_model = 1 / fair_odd (justa, sem overround)
            var pModel  = 1.0 / fairOdd.Value;
            // edge vs preço de mercado (com vig)
            var edge    = pModel - 1.0 / marketOdd;

            if (edge < _minEdge || edge > _maxEdge) continue;

            var kelly   = FractionalKelly(pModel, marketOdd, _kellyFrac);

            yield return new BetSignal(
                MatchId:            matchId,
                Market:             mkt,
                Selection:          sel,
                PModel:             pModel,
                OddsOffered:        marketOdd,
                EdgeVsPrice:        edge,
                KellyStake:         kelly,
                DeltaVorpHome:      dvh,
                DeltaVorpAway:      dva,
                IssuedAt:           t4,
                PipelineLatencyMs:  e2e
            );
        }
    }

    // ---------------------------------------------------------------------------
    // Invocação do Kernel (C# → Redis → Python) — chamada pelo Worker após T2
    // ---------------------------------------------------------------------------

    public async Task<KernelRegistrationResult> InvokeKernelAsync(
        string matchId, double eloA, double eloB, LineupState updatedState,
        string? expectedStateJson, string sourceEventId, TimeSpan stateTtl,
        CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(matchId);
        ArgumentException.ThrowIfNullOrWhiteSpace(sourceEventId);
        if (updatedState.MatchId != matchId || !double.IsFinite(eloA) || !double.IsFinite(eloB) ||
            !double.IsFinite(updatedState.DeltaVorpHome) || !double.IsFinite(updatedState.DeltaVorpAway))
            throw new ArgumentException("Kernel registration requires matching finite inputs");
        var stateTtlMs = checked((long)stateTtl.TotalMilliseconds);
        if (stateTtlMs <= 0) throw new ArgumentOutOfRangeException(nameof(stateTtl));
        if (updatedState.WatchdogDeadlineUnixMs is <= 0 or > 9_007_199_254_740_991)
            throw new ArgumentException("Invalid watchdog deadline");
        ct.ThrowIfCancellationRequested();
        // Replays of the same event and inputs share a claim. A new lineup or
        // correction has its own identity, even when inputs return to an earlier value.
        var invocationIdentity = JsonSerializer.SerializeToUtf8Bytes(
            new { sourceEventId, matchId, eloA, eloB, dvorpA = updatedState.DeltaVorpHome, dvorpB = updatedState.DeltaVorpAway });
        var identityHash = Convert.ToHexString(SHA256.HashData(invocationIdentity));
        var payload = new KernelInvokePayload(
            protocol_version: LineupWorker.Models.RedisProtocol.Version,
            job_id:       matchId,
            run_id:       Guid.NewGuid().ToString("N"),
            idempotency_key: $"kernel:{matchId}:{identityHash}",
            match_id:    matchId,
            elo_a:       eloA,
            elo_b:       eloB,
            dvorp_a:     updatedState.DeltaVorpHome,
            dvorp_b:     updatedState.DeltaVorpAway,
            timestamp_t3: DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            state_version: KernelRedisProtocolV2.VersionPlaceholder
        );
        var complete = updatedState.HomeLineupComplete && updatedState.AwayLineupComplete
            ? JsonSerializer.Serialize(new { MatchId = matchId, CompleteAt = updatedState.ComputedAt }) : "";
        var result = await _redis.GetDatabase().ScriptEvaluateAsync(KernelRedisProtocolV2.Register,
            [STATE_KEY_PREFIX + matchId, KernelRedisProtocolV2.CurrentPrefix + matchId,
             KernelRedisProtocolV2.SequencePrefix + matchId, KernelRedisProtocolV2.RequestPrefix + payload.run_id,
             KernelRedisProtocolV2.IdentityPrefix + payload.idempotency_key, FAIR_ODDS_KEY_PREFIX + matchId,
             KernelRedisProtocolV2.PendingKey, KernelRedisProtocolV2.ReadyKey, KernelRedisProtocolV2.WatchdogKey],
            [expectedStateJson is null ? "0" : "1", expectedStateJson ?? "", JsonSerializer.Serialize(updatedState),
             JsonSerializer.Serialize(payload), stateTtlMs, KernelRedisProtocolV2.RequestLifetimeMs,
             KernelRedisProtocolV2.InvokeChannel, KernelRedisProtocolV2.RequestPrefix, KernelRedisProtocolV2.LeasePrefix,
             complete, "lineup_complete"]);
        var values = (RedisResult[]?)result ?? throw new InvalidOperationException("Invalid Redis registration reply");
        return new(values[0].ToString(), values[1].ToString());
    }
}
