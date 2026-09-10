"""Verification must not import or initialize the numeric daemon."""

import builtins

import pytest
from test_hotpath_smoke import RegisteredRedis

from brasileirao_scripts import hotpath_smoke


def test_verification_has_no_cold_numeric_import_inside_the_result_lifetime(monkeypatch):
    original = builtins.__import__

    def no_numeric_startup(name, *args, **kwargs):
        if name == "brasileirao_predictor.kernel_daemon" or name.split(".")[0] in {"numpy", "numba", "scipy"}:
            raise AssertionError("verification must use a pure protocol parser")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_numeric_startup)
    assert (
        hotpath_smoke.verify_registered_request(RegisteredRedis(), "synthetic")["status"] == "VERIFIED_CURRENT_RESULT"
    )


def test_ambiguous_duplicate_protocol_field_cannot_be_a_valid_request():
    from brasileirao_predictor.kernel_daemon import _parse_invoke

    raw = RegisteredRedis().request.replace('"elo_a": 1600', '"elo_a": 900, "elo_a": 1600')
    with pytest.raises(ValueError):
        _parse_invoke(raw.encode())
