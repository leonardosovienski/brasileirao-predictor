"""Lifecycle supervision tests with doubles; real Lua is exercised separately."""

import asyncio
import json
import signal
from types import SimpleNamespace

import numpy as np
import pytest

from brasileirao_predictor import kernel_daemon
from brasileirao_predictor import kernel_redis_v2 as protocol

PARAMS = (0.2, 1.0, 0.1, 0.0, 0.0, 6)
RAW = json.dumps(
    {
        "protocol_version": protocol.PROTOCOL_VERSION,
        "job_id": "synthetic",
        "run_id": "synthetic-run",
        "match_id": "synthetic",
        "idempotency_key": "synthetic-identity",
        "state_version": "1",
        "elo_a": 1500,
        "elo_b": 1500,
        "dvorp_a": 0,
        "dvorp_b": 0,
        "timestamp_t3": 1,
    }
).encode()


@pytest.mark.parametrize("failure", [ConnectionError, asyncio.CancelledError])
def test_uncertain_completion_releases_only_its_attempt(monkeypatch, failure):
    calls = []

    class Client:
        async def eval(self, script, count, *args):
            calls.append((script, count, args))
            if script == protocol.CLAIM_SCRIPT:
                return b"CLAIMED"
            if script == protocol.COMPLETE_SCRIPT:
                raise failure("synthetic failure")
            assert script == protocol.RELEASE_SCRIPT
            return b"LEASE_LOST"  # e.g. completion already committed / new owner.

    monkeypatch.setattr(kernel_daemon, "_compute_grid_jit", lambda *_: np.ones((2, 2)) / 4)
    if failure is asyncio.CancelledError:
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(kernel_daemon._handle_invoke(Client(), RAW, PARAMS))
    else:
        asyncio.run(kernel_daemon._handle_invoke(Client(), RAW, PARAMS))
    claim, complete, release = calls
    assert claim[0] == protocol.CLAIM_SCRIPT
    assert complete[0] == protocol.COMPLETE_SCRIPT
    assert release[0] == protocol.RELEASE_SCRIPT
    assert claim[2][7] == complete[2][8] == release[2][7]  # same lease token
    assert release[2][5:7] == (RAW, "synthetic-run")


def test_computation_failure_releases_claim_and_never_completes(monkeypatch):
    scripts = []

    class Client:
        async def eval(self, script, count, *args):
            scripts.append(script)
            return b"CLAIMED" if script == protocol.CLAIM_SCRIPT else b"RETRY"

    def fail(*_):
        raise ArithmeticError("synthetic computation failure")

    monkeypatch.setattr(kernel_daemon, "_compute_grid_jit", fail)
    asyncio.run(kernel_daemon._handle_invoke(Client(), RAW, PARAMS))
    assert scripts == [protocol.CLAIM_SCRIPT, protocol.RELEASE_SCRIPT]


def test_poller_recovers_registered_payloads_without_pubsub(monkeypatch):
    seen = []

    async def scenario():
        stop = asyncio.Event()

        class Client:
            async def eval(self, script, count, *args):
                assert script == protocol.POLL_SCRIPT
                assert count == 1 and args[0] == protocol.PENDING_KEY
                return [b"request-a", b"request-b"]

        async def handle(client, raw, params):
            assert params == PARAMS
            seen.append(raw)
            if len(seen) == 2:
                stop.set()

        monkeypatch.setattr(kernel_daemon, "_handle_invoke", handle)
        await kernel_daemon._poll_pending(Client(), PARAMS, stop)

    asyncio.run(scenario())
    assert seen == [b"request-a", b"request-b"]


def test_windows_signal_fallback_schedules_stop_and_restores_handlers(monkeypatch):
    originals = {signal.SIGTERM: object(), signal.SIGINT: object()}
    installed = dict(originals)
    scheduled = []

    def unavailable(*_):
        raise NotImplementedError

    monkeypatch.setattr(kernel_daemon.signal, "getsignal", lambda sig: originals[sig])
    monkeypatch.setattr(kernel_daemon.signal, "signal", lambda sig, fn: installed.__setitem__(sig, fn))
    loop = SimpleNamespace(
        add_signal_handler=unavailable,
        call_soon_threadsafe=lambda callback: scheduled.append(callback),
    )
    stop = asyncio.Event()
    restore = kernel_daemon._install_stop_signals(loop, stop)
    installed[signal.SIGTERM](signal.SIGTERM, None)
    assert len(scheduled) == 1 and not stop.is_set()
    scheduled[0]()
    assert stop.is_set()
    restore()
    assert installed == originals


def test_session_keeps_client_open_until_inflight_handler_cleans_up(monkeypatch):
    import redis.asyncio as redis_asyncio_module

    async def scenario():
        callbacks = {}
        started = asyncio.Event()
        released = False

        class PubSub:
            async def subscribe(self, channel):
                assert channel == protocol.INVOKE_CHANNEL

            async def listen(self):
                yield {"type": "message", "data": RAW}
                await asyncio.Event().wait()

            async def unsubscribe(self, channel):
                pass

            async def aclose(self):
                pass

        class Client:
            closed = False

            def pubsub(self):
                return PubSub()

            async def set(self, key, value):
                pass

            async def delete(self, key):
                pass

            async def eval(self, script, count, *args):
                assert script == protocol.HEARTBEAT_SCRIPT
                return 1

            async def aclose(self):
                assert released
                self.closed = True

        client = Client()

        async def handle(*_):
            nonlocal released
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                assert not client.closed
                released = True

        async def poll(client, params, stop, heartbeat_payload):
            await stop.wait()

        loop = asyncio.get_running_loop()
        wrapper = SimpleNamespace(
            run_in_executor=loop.run_in_executor,
            add_signal_handler=lambda sig, callback: callbacks.__setitem__(sig, callback),
            remove_signal_handler=lambda sig: True,
        )
        monkeypatch.setattr(kernel_daemon.asyncio, "get_event_loop", lambda: wrapper)
        monkeypatch.setattr(kernel_daemon, "_load_params", lambda _: PARAMS)
        monkeypatch.setattr(kernel_daemon, "_warmup_jit", lambda _: 0.1)
        monkeypatch.setattr(kernel_daemon, "_handle_invoke", handle)
        monkeypatch.setattr(kernel_daemon, "_poll_pending", poll)
        monkeypatch.setattr(redis_asyncio_module, "from_url", lambda *args, **kwargs: client)
        daemon = asyncio.create_task(kernel_daemon._run_daemon("synthetic.db", "redis://unused/15"))
        await asyncio.wait_for(started.wait(), 2)
        callbacks[signal.SIGTERM]()
        await asyncio.wait_for(daemon, 2)
        assert released and client.closed

    asyncio.run(scenario())
