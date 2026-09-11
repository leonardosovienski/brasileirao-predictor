"""A slow cold import must precede creation of an expiring synthetic result."""

import builtins
from types import SimpleNamespace

from brasileirao_scripts import hotpath_smoke


def test_synthetic_cli_does_not_spend_result_ttl_importing_the_kernel(monkeypatch):
    clock = SimpleNamespace(now=0, expires=None, loaded=False)
    original_import = builtins.__import__

    def cold_import(name, *args, **kwargs):
        if name == "brasileirao_predictor.kernel_daemon" and not clock.loaded:
            clock.loaded = True
            clock.now += 6  # A cold NumPy/Numba import can exceed the result's 5s TTL.
        return original_import(name, *args, **kwargs)

    def register(client):
        clock.expires = clock.now + 5
        return "synthetic"

    def verify(client, match):
        from brasileirao_predictor.kernel_daemon import _parse_invoke  # noqa: F401

        if clock.now >= clock.expires:
            raise ValueError("expired synthetic result")
        return {"status": "VERIFIED_CURRENT_RESULT"}

    client = SimpleNamespace(ping=lambda: True, close=lambda: None)
    monkeypatch.setattr(builtins, "__import__", cold_import)
    monkeypatch.setattr(hotpath_smoke.redis, "from_url", lambda *a, **k: client)
    monkeypatch.setattr(hotpath_smoke, "register_synthetic_lineup", register)
    monkeypatch.setattr(hotpath_smoke, "verify_registered_request", verify)
    assert hotpath_smoke.main(["--synthetic-lineup", "--redis", "redis://127.0.0.1:26380/13"]) == 0
