from brasileirao_scripts.exp001_coverage_audit import _summary


def test_summary_keeps_missing_fixtures_in_denominator():
    rows = [
        {"requested_cutoff": horizon, "missing": missing, "snapshot_age_minutes": 10}
        for horizon in ("H-24h", "H-6h", "H-1h")
        for missing in (False, True)
    ]
    result = _summary(rows, 2)
    assert all(value["coverage"] == 0.5 for value in result.values())
    assert all(value["missing"] == 1 for value in result.values())
