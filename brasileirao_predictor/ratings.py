from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from itertools import groupby


def _parse(d: str) -> date:
    return date.fromisoformat(d)


def k_factor(tournament: str, k_factors: dict) -> float:
    if tournament in k_factors:
        return k_factors[tournament]
    t = (tournament or "").lower()
    if "qualification" in t:
        return k_factors.get("FIFA World Cup qualification", 40)
    return k_factors["default"]


def margin_multiplier(goal_diff: int) -> float:
    d = abs(goal_diff)
    if d <= 1:
        return 1.0
    if d == 2:
        return 1.5
    return 1.75 + (d - 3) / 8.0


def expected_score(rating_diff: float) -> float:
    return 1.0 / (1.0 + 10 ** (-rating_diff / 400.0))


def temporal_keys(matches) -> list[str]:
    """Return conservative batch keys, collapsing a date if any kickoff is missing."""
    materialized = list(matches)
    dates_with_missing = {str(match[0])[:10] for match in materialized if len(match) < 8 or not match[7]}
    keys: list[str] = []
    for match in materialized:
        day = str(match[0])[:10]
        if day in dates_with_missing:
            keys.append(f"{day}T00:00:00+00:00|date")
            continue
        parsed = datetime.fromisoformat(str(match[7]).replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("kickoff_at must be timezone-aware")
        keys.append(f"{parsed.astimezone(UTC).isoformat()}|kickoff")
    return keys


def compute_ratings(matches, cfg_elo: dict, *, asof: str | date | None = None):
    """matches: iterável ordenado por data de tuplas
    (date, home, away, home_score, away_score, tournament, neutral).
    Aplica regressão à média proporcional ao tempo desde o último jogo de cada
    time (meia-vida configurável), de modo que resultados antigos perdem peso sem
    achatar a convergência. Retorna (ratings, history) — history alimenta a
    calibração do modelo de gols com o rating diff *pré-jogo* de cada partida."""
    base = float(cfg_elo["initial_rating"])
    ratings = defaultdict(lambda: base)
    home_adv = float(cfg_elo["home_advantage"])
    half_life = cfg_elo.get("form_half_life_years")
    last_seen = {}
    history = []

    def decay(team, today):
        if not half_life or team not in last_seen:
            return
        years = (today - last_seen[team]).days / 365.25
        factor = 0.5 ** (years / half_life)
        ratings[team] = base + (ratings[team] - base) * factor

    materialized = list(matches)

    keyed = list(zip(temporal_keys(materialized), materialized, strict=True))
    keyed.sort(key=lambda item: item[0])
    for _key, batch_iter in groupby(keyed, key=lambda item: item[0]):
        batch = [item[1] for item in batch_iter]
        batch_date = _parse(str(batch[0][0])[:10])
        teams = {str(team) for match in batch for team in match[1:3]}
        for team in teams:
            decay(team, batch_date)

        deltas: dict[str, float] = defaultdict(float)
        for match in batch:
            d, home, away, hs, as_, tournament, neutral = match[:7]
            adv = 0.0 if neutral else home_adv
            diff = ratings[home] + adv - ratings[away]
            history.append((diff, hs, as_))
            we_home = expected_score(diff)
            result = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
            k = k_factor(tournament, cfg_elo["k_factors"]) * margin_multiplier(hs - as_)
            delta = k * (result - we_home)
            deltas[home] += delta
            deltas[away] -= delta
        for team, delta in deltas.items():
            ratings[team] += delta
            last_seen[team] = batch_date

    if asof is not None and last_seen:
        horizon = asof if isinstance(asof, date) else _parse(str(asof)[:10])
        if horizon < max(last_seen.values()):
            raise ValueError("asof cannot be earlier than the latest match")
        for team in list(last_seen):
            decay(team, horizon)

    return dict(ratings), history


def ratings_asof(matches, cfg_elo: dict, dates) -> dict:
    """Snapshot forward-only dos ratings imediatamente ANTES de cada data.

    Fix da auditoria (P3): os scripts de pesquisa usavam `current_elo` — o
    rating de HOJE — como rating pre-jogo de partidas passadas (lookahead).
    Este helper devolve {data_iso: {team: rating}} onde cada snapshot enxerga
    apenas partidas com date < data, aplicando a mesma janela `window_years`
    do cron RELATIVA a cada data (paridade train/serve).

    matches: iteravel ordenado por data no formato de compute_ratings.
    dates: iteravel de datas ISO (strings). Custo O(D*N) — aceitavel para
    pesquisa (D ~ dezenas de datas de evento).
    """
    ms = list(matches)
    window = cfg_elo.get("window_years")
    out = {}
    for d in sorted(set(dates)):
        prefix = [m for m in ms if m[0] < d]
        if window:
            cut = (_parse(d) - timedelta(days=int(window * 365.25))).isoformat()
            prefix = [m for m in prefix if m[0] >= cut]
        out[d], _ = compute_ratings(prefix, cfg_elo, asof=d)
    return out
