from scripts.compare_hypothesis_errors import _chronological_keys


def test_moving_block_pairing_uses_time_not_event_id() -> None:
    control = {
        "a": {"date": "2026-01-03"},
        "z": {"date": "2026-01-01"},
        "m": {"date": "2026-01-02"},
    }
    treatment = dict(control)

    assert _chronological_keys(control, treatment) == ["z", "m", "a"]
