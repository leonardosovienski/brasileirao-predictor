using System.Text.Json;
using System.Security.Cryptography;
using StackExchange.Redis;

namespace LineupWorker.Services;

/// <summary>
/// Serviço de warm-up: carrega VORP e Replacement Levels do artefato JSON produzido
/// pelo src/research/vorp_ridge.py e os mantém em memória para consulta O(1).
///
/// Ciclo de vida: singleton — aquece uma vez na inicialização do host.
/// </summary>
public sealed class VorpStateService : IHostedService
{
    private readonly ILogger<VorpStateService> _log;
    private readonly OperationalSettings _settings;

    // Estruturas em memória — imutáveis após warm-up
    private IReadOnlyDictionary<string, double> _vorpByPlayer  = new Dictionary<string, double>();
    private IReadOnlyDictionary<string, double> _replacementByPos = new Dictionary<string, double>();
    private IReadOnlyDictionary<string, double[]> _titularidadeByTeam = new Dictionary<string, double[]>();

    private bool _ready;
    public string ArtifactSha256 { get; private set; } = "";

    public VorpStateService(ILogger<VorpStateService> log, OperationalSettings settings)
    {
        _log = log;
        _settings = settings;
    }

    public Task StartAsync(CancellationToken ct)
    {
        var artifactPath = _settings.VorpArtifactPath;
        _log.LogInformation("[VorpState] aquecendo de {Path}", artifactPath);

        var bytes = File.ReadAllBytes(artifactPath);
        using var doc = JsonDocument.Parse(bytes);
        var root = doc.RootElement;

        _vorpByPlayer = root.GetProperty("beta_players")
            .EnumerateObject()
            .ToDictionary(p => p.Name, p => p.Value.GetDouble());

        _replacementByPos = root.GetProperty("replacement_levels")
            .EnumerateObject()
            .ToDictionary(p => p.Name, p => p.Value.GetDouble());
        if (_vorpByPlayer.Values.Concat(_replacementByPos.Values).Any(value => !double.IsFinite(value)))
            throw new JsonException("VORP and replacement values must be finite");
        ArtifactSha256 = Convert.ToHexString(SHA256.HashData(bytes));

        // Titularidade histórica por time (opcional — arquivo separado)
        var titPath = _settings.TitularidadePath;
        if (File.Exists(titPath))
        {
            using var tstream = File.OpenRead(titPath);
            using var tdoc = JsonDocument.Parse(tstream);
            _titularidadeByTeam = tdoc.RootElement
                .EnumerateObject()
                .ToDictionary(
                    p => p.Name,
                    p => p.Value.EnumerateArray().Select(v => v.GetDouble()).ToArray()
                );
            if (_titularidadeByTeam.Values.SelectMany(values => values).Any(value => !double.IsFinite(value) || value < 0 || value > 1))
                throw new JsonException("Starter probabilities must be finite in [0,1]");
        }

        _ready = true;
        _log.LogInformation("[VorpState] pronto — {N} jogadores, {P} posições",
            _vorpByPlayer.Count, _replacementByPos.Count);

        return Task.CompletedTask;
    }

    public Task StopAsync(CancellationToken ct) => Task.CompletedTask;

    public bool IsReady => _ready;

    /// <summary>Retorna VORP do jogador (O(1)). Fallback: Replacement Level da posição.</summary>
    public double GetVorp(string player, string position)
    {
        if (_vorpByPlayer.TryGetValue(player, out var v))
            return v;
        if (_replacementByPos.TryGetValue(position, out var rv))
            return rv;
        return _replacementByPos.GetValueOrDefault("UNKNOWN", 0.0);
    }

    /// <summary>Delta VORP de um lineup completo: soma dos VORPs dos 11 titulares.</summary>
    public double ComputeDeltaVorp(IEnumerable<(string Player, string Position)> starters)
        => starters.Sum(s => GetVorp(s.Player, s.Position));

    public double ComputeDeclaredDelta(IEnumerable<(string Player, string Position)> starters)
    {
        var sum = 0.0;
        foreach (var (player, position) in starters)
        {
            if (!_vorpByPlayer.TryGetValue(player, out var value) && !_replacementByPos.TryGetValue(position, out value))
                throw new ArgumentException("Player and declared position lack VORP coverage");
            sum += value;
        }
        if (!double.IsFinite(sum)) throw new ArgumentException("Nonfinite lineup VORP");
        return sum;
    }

    /// <summary>Retorna a matriz de probabilidade de titularidade histórica do time.
    /// Usada no fallback de timeout. null se não disponível.</summary>
    public double[]? GetTitularidadeMatrix(string team)
        => _titularidadeByTeam.GetValueOrDefault(team);
}
