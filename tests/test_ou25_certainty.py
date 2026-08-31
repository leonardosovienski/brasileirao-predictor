from brasileirao_predictor.research.ou25_nested_replay import _wilson_lower


def test_wilson_lower_is_conservative_and_tightens_with_sample():
    small = _wilson_lower(8, 10, 0.95)
    large = _wilson_lower(80, 100, 0.95)
    assert 0 < small < large < 0.8


def test_higher_confidence_has_lower_bound():
    assert _wilson_lower(80, 100, 0.99) < _wilson_lower(80, 100, 0.90)
