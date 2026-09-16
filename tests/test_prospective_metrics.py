import pytest

from brasileirao_scripts.prospective_metrics import brier_ou25, holm_family


def test_brier_convention_and_boundary():
    assert brier_ou25(0.75, 2, 1) == 0.125
    assert brier_ou25(0.75, 2, 0) == 1.125
    assert brier_ou25(1, 2, 1) == 0
    assert brier_ou25(0, 2, 1) == 2


@pytest.mark.parametrize("value", [None, True, -0.1, 1.1, float("nan"), float("inf")])
def test_invalid_forecasts_are_not_filled_in(value):
    with pytest.raises(ValueError):
        brier_ou25(value, 2, 1)


def test_holm_stops_after_first_failed_hypothesis():
    result = holm_family({"H14": 0.03, "H15": 0.04}, expected_ids=("H14", "H15"))
    assert result["adjusted_p_values"] == {"H14": 0.06, "H15": 0.06}
    assert result["rejected"] == {"H14": False, "H15": False}


def test_holm_is_order_invariant_and_keeps_family():
    first = holm_family({"H14": 0.02, "H15": 0.045}, expected_ids=("H14", "H15"))
    assert first["rejected"] == {"H14": True, "H15": True}
    assert first == holm_family({"H15": 0.045, "H14": 0.02}, expected_ids=("H15", "H14"))
    with pytest.raises(ValueError):
        holm_family({"H14": 0.02}, expected_ids=("H14", "H15"))


@pytest.mark.parametrize("value", [True, None, -0.1, 1.1, float("nan"), float("inf")])
def test_holm_rejects_invalid_p_values(value):
    with pytest.raises(ValueError):
        holm_family({"H14": value, "H15": 0.5}, expected_ids=("H14", "H15"))
