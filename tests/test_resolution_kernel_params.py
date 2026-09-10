import pytest

from brasileirao_predictor import kernel_daemon as kernel


@pytest.mark.parametrize(
    "index,value", [(0, float("inf")), (1, float("nan")), (2, -0.1), (4, True), (5, 0), (5, -1), (5, 1.5), (5, 101)]
)
def test_invalid_kernel_parameters_never_reach_numba(monkeypatch, index, value):
    params = [0.2, 1.0, 0.1, 0.0, 0.0, 12]
    params[index] = value

    def unsafe_jit(*args):
        raise AssertionError("invalid parameters reached the numerical kernel")

    monkeypatch.setattr(kernel, "_compute_grid_jit", unsafe_jit)
    with pytest.raises(ValueError):
        kernel._warmup_jit(tuple(params))


def test_supported_kernel_parameters_keep_two_warmup_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(kernel, "_compute_grid_jit", lambda *args: calls.append(args))
    assert kernel._warmup_jit((0.2, 1.0, 0.1, -0.05, 0.0, 12)) >= 0
    assert len(calls) == 2
    assert calls[0] == calls[1]
