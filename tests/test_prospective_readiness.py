from scripts import prospective_readiness


def test_readiness_fails_closed_without_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.setattr(prospective_readiness, "ROOT", tmp_path)
    monkeypatch.setattr(
        prospective_readiness,
        "Settings",
        lambda: type("EmptySettings", (), {"API_FOOTBALL_KEY": None, "THE_ODDS_API_KEY": None})(),
    )
    result = prospective_readiness.report()
    assert result["h9_can_emit"] is False
    assert result["capital_enabled"] is False
    assert result["bookmaker_persistence_gate"] == "PENDING"
    assert result["collection_runs"] == 0
