import asyncio
import builtins
import importlib
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

from brasileirao_predictor import kernel_daemon as kernel
from brasileirao_predictor import kernel_redis_v2 as protocol


def test_installed_health_entrypoint_needs_no_numeric_or_database_import(monkeypatch, tmp_path):
    config = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    module_name, function = config["project"]["scripts"]["brasileirao-kernel"].split(":")
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    original = builtins.__import__

    def lightweight_import(name, *args, **kwargs):
        if name.split(".")[0] in {"numpy", "numba", "scipy"} or name == "brasileirao_predictor.db":
            raise AssertionError("healthcheck attempted an expensive model dependency import")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", lightweight_import)
    client = SimpleNamespace(eval=lambda *args: 1, close=lambda: None)
    monkeypatch.setitem(sys.modules, "redis", SimpleNamespace(from_url=lambda *args, **kwargs: client))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "brasileirao-kernel",
            "--healthcheck",
            "--db",
            str(tmp_path / "sports.db"),
            "--redis",
            "redis://127.0.0.1:1/15",
        ],
    )
    entrypoint = getattr(importlib.import_module(module_name), function)
    assert entrypoint() == 0


def test_pubsub_burst_has_bounded_handlers_and_cancels_them_on_shutdown(monkeypatch):
    import redis.asyncio as redis_asyncio

    async def exercise():
        stop = asyncio.Event()
        active = 0
        maximum = 0

        class PubSub:
            async def subscribe(self, *args):
                pass

            async def unsubscribe(self, *args):
                pass

            async def aclose(self):
                pass

            async def listen(self):
                for _ in range(protocol.POLL_LIMIT * 4):
                    yield {"type": "message", "data": b"durably registered synthetic request"}
                await asyncio.sleep(0)
                stop.set()
                await asyncio.Event().wait()

        class Client:
            def pubsub(self):
                return PubSub()

            async def eval(self, *args):
                return 1

            async def aclose(self):
                pass

        async def handle(*args):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            try:
                await asyncio.Event().wait()
            finally:
                active -= 1

        async def recover(*args):
            await stop.wait()

        monkeypatch.setattr(redis_asyncio, "from_url", lambda *args, **kwargs: Client())
        monkeypatch.setattr(kernel, "_handle_invoke", handle)
        monkeypatch.setattr(kernel, "_poll_pending", recover)
        await asyncio.wait_for(kernel._serve_sessions((0.2, 1.0, 0.1, 0.0, 0.0, 12), "redis://127.0.0.1:1/15", stop), 5)
        assert 0 < maximum <= protocol.POLL_LIMIT
        assert active == 0

    asyncio.run(exercise())


def test_healthcheck_connection_failure_closes_client_and_does_not_log_credentials(monkeypatch, tmp_path, caplog):
    import redis

    from brasileirao_predictor import kernel_cli

    options = {}
    closed = []

    def unavailable(*args):
        raise redis.ConnectionError("redis://user:synthetic-secret@unavailable.invalid/15")

    def client_factory(url, **kwargs):
        options.update(kwargs)
        return SimpleNamespace(eval=unavailable, close=lambda: closed.append(True))

    monkeypatch.setattr(redis, "from_url", client_factory)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "brasileirao-kernel",
            "--healthcheck",
            "--db",
            str(tmp_path / "absent.db"),
            "--redis",
            "redis://127.0.0.1:1/15",
        ],
    )
    assert kernel_cli.main() == 1
    assert options["socket_connect_timeout"] == options["socket_timeout"] == 1
    assert options["retry_on_timeout"] is False
    assert closed == [True]
    assert "synthetic-secret" not in caplog.text
