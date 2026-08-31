from brasileirao_scripts.backtest_walkforward import _aligned_blocks


def test_blocks_never_split_a_calendar_date() -> None:
    rows = [
        ("2025-01-01", "a", "b"),
        ("2025-01-01", "c", "d"),
        ("2025-01-02", "a", "c"),
        ("2025-01-02", "b", "d"),
        ("2025-01-03", "a", "d"),
    ]
    blocks = _aligned_blocks(rows, 3)
    assert blocks == [(0, 4), (4, 5)]
    for _start, end in blocks[:-1]:
        assert rows[end - 1][0] != rows[end][0]
