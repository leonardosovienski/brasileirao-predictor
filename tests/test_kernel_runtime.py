import sys
from types import SimpleNamespace

import numpy as np
import pytest

from brasileirao_predictor import kernel_daemon


def test_grid_is_normalized_non_negative_and_dixon_coles_changes_low_scores() -> None:
    baseline = kernel_daemon._compute_grid_jit(1.4, 1.1, 0.12, 0.0, 8)
    adjusted = kernel_daemon._compute_grid_jit(1.4, 1.1, 0.12, -0.08, 8)

    assert baseline.shape == (9, 9)
    assert np.isclose(adjusted.sum(), 1.0)
    assert np.all(adjusted >= 0)
    assert not np.allclose(baseline[:2, :2], adjusted[:2, :2])


def test_numba_python_implementation_is_directly_verifiable() -> None:
    python_grid = kernel_daemon._compute_grid_jit.py_func

    grid = python_grid(1.2, 0.9, 0.15, 0.05, 5)

    assert grid.shape == (6, 6)
    assert np.isclose(grid.sum(), 1.0)
    assert np.all(grid >= 0)


def test_fair_odds_cover_complete_probability_grid() -> None:
    grid = np.zeros((3, 3))
    grid[0, 0] = 0.2
    grid[1, 0] = 0.3
    grid[0, 1] = 0.1
    grid[2, 2] = 0.4

    odds = kernel_daemon._fair_odds_from_grid(grid)

    assert odds == {"1": 3.3333, "X": 1.6667, "2": 10.0, "o25": 2.5, "u25": 1.6667}


def test_fair_odds_represents_zero_probability_as_none() -> None:
    grid = np.zeros((2, 2))
    grid[0, 0] = 1.0

    odds = kernel_daemon._fair_odds_from_grid(grid)

    assert odds["1"] is None
    assert odds["2"] is None
    assert odds["o25"] is None


class _Connection:
    closed = False

    def close(self) -> None:
        self.closed = True


def test_load_params_closes_sports_db_and_applies_config(monkeypatch) -> None:
    connection = _Connection()
    monkeypatch.setattr(kernel_daemon._db, "connect", lambda path, read_only: connection)
    monkeypatch.setattr(kernel_daemon._db, "load_params", lambda conn: (0.2, 1.1, 0.3, -0.1))
    monkeypatch.setenv("KERNEL_VORP_THETA", "0.25")
    monkeypatch.setenv("KERNEL_MAX_GOALS", "9")

    assert kernel_daemon._load_params("sports.db") == (0.2, 1.1, 0.3, -0.1, 0.25, 9)
    assert connection.closed


def test_load_params_closes_sports_db_when_cache_is_empty(monkeypatch) -> None:
    connection = _Connection()
    monkeypatch.setattr(kernel_daemon._db, "connect", lambda path, read_only: connection)
    monkeypatch.setattr(kernel_daemon._db, "load_params", lambda conn: None)

    with pytest.raises(RuntimeError, match="cache vazio"):
        kernel_daemon._load_params("sports.db")
    assert connection.closed


def test_load_params_rejects_stale_versioned_cache(monkeypatch) -> None:
    connection = _Connection()
    row = (0.2, 1.1, 0.3, -0.1, 10, "old-hash", "2026-01-01T00:00:00+00:00")
    monkeypatch.setattr(kernel_daemon._db, "connect", lambda path, read_only: connection)
    monkeypatch.setattr(kernel_daemon._db, "load_params", lambda conn: row)
    monkeypatch.setattr("brasileirao_predictor.cron_update_models.cache_is_current", lambda cfg, conn, params: False)
    monkeypatch.setattr("brasileirao_predictor.ingest.load_config", lambda: {})

    with pytest.raises(RuntimeError, match="cache desatualizado"):
        kernel_daemon._load_params("sports.db")
    assert connection.closed


def test_warmup_invokes_grid_twice(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(kernel_daemon, "_compute_grid_jit", lambda *args: calls.append(args))

    elapsed = kernel_daemon._warmup_jit((0.2, 1.0, 0.1, -0.2, 0.0, 6))

    assert elapsed >= 0
    assert len(calls) == 2
    assert calls[0] == calls[1]
    assert calls[0][-2:] == (0.2, 6)


def test_main_rejects_missing_runtime_configuration(monkeypatch) -> None:
    monkeypatch.delenv("SPORTS_DB_PATH", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(sys, "argv", ["brasileirao-kernel"])

    with pytest.raises(SystemExit) as exc:
        kernel_daemon.main()
    assert exc.value.code == 2


def test_main_healthcheck_reports_redis_state(monkeypatch, tmp_path) -> None:
    sports_db = tmp_path / "sports.db"
    client = SimpleNamespace(get=lambda key: b"ready")
    fake_redis = SimpleNamespace(from_url=lambda url: client)
    monkeypatch.setitem(sys.modules, "redis", fake_redis)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "brasileirao-kernel",
            "--db",
            str(sports_db),
            "--redis",
            "redis://redis:6379/0",
            "--healthcheck",
        ],
    )

    assert kernel_daemon.main() == 0


def test_main_healthcheck_fails_when_kernel_is_not_ready(monkeypatch, tmp_path) -> None:
    sports_db = tmp_path / "sports.db"
    client = SimpleNamespace(get=lambda key: None)
    monkeypatch.setitem(sys.modules, "redis", SimpleNamespace(from_url=lambda url: client))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "brasileirao-kernel",
            "--db",
            str(sports_db),
            "--redis",
            "redis://redis:6379/0",
            "--healthcheck",
        ],
    )

    assert kernel_daemon.main() == 1


def test_main_starts_daemon_with_explicit_absolute_configuration(monkeypatch, tmp_path) -> None:
    sports_db = tmp_path / "sports.db"
    seen = []

    def run(coroutine) -> None:
        seen.append(coroutine)
        coroutine.close()

    monkeypatch.setattr(kernel_daemon.asyncio, "run", run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "brasileirao-kernel",
            "--db",
            str(sports_db),
            "--redis",
            "redis://redis:6379/0",
        ],
    )

    assert kernel_daemon.main() is None
    assert len(seen) == 1


class _PubSub:
    def __init__(self) -> None:
        self.subscribed = []
        self.unsubscribed = []

    async def subscribe(self, channel) -> None:
        self.subscribed.append(channel)

    async def listen(self):
        yield {"type": "subscribe", "data": b""}

    async def unsubscribe(self, channel) -> None:
        self.unsubscribed.append(channel)

    async def aclose(self) -> None:
        return None


class _DaemonRedis:
    def __init__(self) -> None:
        self.pubsub_instance = _PubSub()
        self.set_calls = []
        self.deleted = []
        self.closed = False

    def pubsub(self):
        return self.pubsub_instance

    async def set(self, key, value) -> None:
        self.set_calls.append((key, value))

    async def delete(self, key) -> None:
        self.deleted.append(key)

    async def aclose(self) -> None:
        self.closed = True


def test_daemon_sets_health_and_cleans_up_on_shutdown(monkeypatch) -> None:
    import redis.asyncio as redis_asyncio_module

    client = _DaemonRedis()
    monkeypatch.setattr(redis_asyncio_module, "from_url", lambda url, decode_responses: client)
    monkeypatch.setattr(kernel_daemon, "_load_params", lambda path: (0.2, 1, 0.1, 0, 0, 6))
    monkeypatch.setattr(kernel_daemon, "_warmup_jit", lambda params: 0.1)

    async def exercise() -> None:
        running_loop = __import__("asyncio").get_running_loop()
        loop = SimpleNamespace(
            run_in_executor=running_loop.run_in_executor,
            add_signal_handler=lambda signal, callback: callback(),
        )
        monkeypatch.setattr(kernel_daemon.asyncio, "get_event_loop", lambda: loop)
        await kernel_daemon._run_daemon("sports.db", "redis://redis:6379/0")

    __import__("asyncio").run(exercise())

    assert client.pubsub_instance.subscribed == ["system:invoke_kernel"]
    assert client.set_calls == [("health:kernel", "ready")]
    assert client.pubsub_instance.unsubscribed == ["system:invoke_kernel"]
    assert client.deleted == ["health:kernel"]
    assert client.closed
