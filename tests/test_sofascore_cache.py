import json

import pytest

from src.sofascore import Sofascore


def _client(tmp_path, monkeypatch, pages_by_call):
    """Sofascore com _fetch mockado: devolve pages_by_call.pop(0) a cada chamada,
    sem rede nem sleep."""
    c = Sofascore(rate_limit=0.0, cache_dir=str(tmp_path))
    calls = []

    def fake_fetch(path):
        calls.append(path)
        return pages_by_call.pop(0) if pages_by_call else {"events": []}

    monkeypatch.setattr(c, "_fetch", fake_fetch)
    return c, calls


def test_next_events_are_never_cached_bracket_placeholder_resolves(tmp_path, monkeypatch):
    """BUG (fixo): 'next' (fixtures futuros) não pode ser cacheado — o Sofascore
    troca placeholder de bracket ('W83') pelo nome real do time conforme as fases
    anteriores terminam. Cachear a lista congela o placeholder para sempre."""
    stale = {"events": [{"id": 1, "homeTeam": {"name": "W83"}, "awayTeam": {"name": "W84"}}]}
    fresh = {"events": [{"id": 1, "homeTeam": {"name": "Mexico"}, "awayTeam": {"name": "England"}}]}
    # ordem real de season_events(upcoming=True): kind='last' primeiro (página 0 vazia
    # encerra o loop), depois kind='next' (página 0 = payload, página 1 vazia encerra)
    empty = {"events": []}

    c, calls = _client(tmp_path, monkeypatch, [empty, stale, empty])
    first = c.season_events(16, 58210, upcoming=True)
    assert first[-1]["homeTeam"]["name"] == "W83"  # placeholder da 1ª coleta

    # 'last' já foi cacheado em disco por `c` (mesmo tmp_path) — a 2ª coleta não
    # chama fetch pra ele; só 'next' (cache=False) bate na rede de novo.
    c2, calls2 = _client(tmp_path, monkeypatch, [fresh, empty])
    second = c2.season_events(16, 58210, upcoming=True)
    assert calls2, "season_events('next') deve SEMPRE ir à rede — nunca servir do cache"
    assert second[-1]["awayTeam"]["name"] == "England"  # nome resolvido na 2ª coleta


def test_last_events_are_cached(tmp_path, monkeypatch):
    """kind='last' (jogos encerrados) é imutável — cache é seguro e esperado."""
    finished = {"events": [{"id": 2, "homeTeam": {"name": "Brazil"}, "awayTeam": {"name": "Japan"}}]}
    c, calls = _client(tmp_path, monkeypatch, [finished, {"events": []}])
    c.season_events(16, 58210, upcoming=False)

    c2, calls2 = _client(tmp_path, monkeypatch, [{"events": [{"id": 999}]}, {"events": []}])
    result = c2.season_events(16, 58210, upcoming=False)
    assert not calls2, "kind='last' deve vir do cache — sem chamada de rede na 2ª coleta"
    assert result[-1]["homeTeam"]["name"] == "Brazil"  # veio do disco, não do 'fresh' fake


def test_cache_truncado_e_refeito_sem_bloquear_coleta(tmp_path, monkeypatch):
    path = tmp_path / "unique-tournament_16_seasons.json"
    path.write_text('{"seasons": [', encoding="utf-8")
    fresh = {"seasons": [{"id": 87678, "year": "2026"}]}
    client, calls = _client(tmp_path, monkeypatch, [fresh])

    assert client.list_seasons(16) == [(87678, "2026")]
    assert calls == ["unique-tournament/16/seasons"]
    assert json.loads(path.read_text(encoding="utf-8")) == fresh
    assert not list(tmp_path.glob("*.tmp"))


def test_no_cache_dir_skips_disk_entirely(monkeypatch):
    c = Sofascore(rate_limit=0.0)
    monkeypatch.setattr(c, "_fetch", lambda path: {"seasons": []})
    assert c.cache is None
    assert c.list_seasons(16) == []


def test_sofascore_insecure_env_disables_verification(monkeypatch):
    monkeypatch.setenv("SOFASCORE_INSECURE", "1")
    c = Sofascore(rate_limit=0.0)
    assert c.verify is False


def test_event_wrappers_delegate_to_get(monkeypatch):
    c = Sofascore(rate_limit=0.0)
    calls = []
    monkeypatch.setattr(c, "_get", lambda path, cache=True: calls.append((path, cache)) or {"ok": True})

    assert c.event_odds(123, finished=True) == {"ok": True}
    assert c.event_odds(123) == {"ok": True}
    assert c.event_statistics(123) == {"ok": True}
    assert c.event_lineups(123) == {"ok": True}
    assert calls == [
        ("event/123/odds/1/all", True),
        ("event/123/odds/1/all", False),
        ("event/123/statistics", True),
        ("event/123/lineups", True),
    ]


def test_cache_write_failure_removes_temp_file_and_reraises(tmp_path, monkeypatch):
    c, _ = _client(tmp_path, monkeypatch, [{"seasons": []}])

    def failing_fdopen(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("src.sofascore.os.fdopen", failing_fdopen)
    with pytest.raises(OSError, match="disk full"):
        c.list_seasons(16)
    assert not list(tmp_path.glob("*.tmp"))
